"""FastAPI 应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chapters, papers, references, versions
from app.config import settings
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表（导入模型以注册元数据）
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 初始化向量数据库
    from app.rag.vector_store import VectorStore
    VectorStore.initialize()

    yield

    # 关闭时清理资源
    await engine.dispose()


# 创建 FastAPI 应用实例
app = FastAPI(
    title="AI 论文写作系统",
    description="基于多 Agent 协作的智能论文写作平台",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置 - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(papers.router, prefix="/api/papers", tags=["论文"])
app.include_router(chapters.router, prefix="/api/chapters", tags=["章节"])
app.include_router(references.router, prefix="/api/references", tags=["文献"])
app.include_router(versions.router, prefix="/api/papers/{paper_id}/versions", tags=["版本管理"])


@app.get("/")
async def root():
    """健康检查接口"""
    return {
        "message": "AI 论文写作系统 API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """详细健康检查"""
    from app.services.reference_service import reference_service
    from app.utils.llm import is_embedding_configured, is_llm_configured

    return {
        "database": "connected",
        "vector_store": "ready",
        "llm": "available" if is_llm_configured() else "not_configured",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": getattr(settings, f"{settings.LLM_PROVIDER.upper()}_MODEL", ""),
        "embedding": "available" if is_embedding_configured() else "not_configured",
        "vector_count": reference_service.status()["vector_count"],
    }