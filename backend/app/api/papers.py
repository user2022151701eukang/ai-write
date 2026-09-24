"""论文接口"""

import io
import json
import re
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.auth import get_optional_user, require_llm_config
from app.database import get_db
from app.models.paper import PaperStatus
from app.models.user import User
from app.schemas.paper import (
    PaperCreate,
    PaperDetail,
    PaperGenerateRequest,
    PaperResponse,
    PaperUpdate,
)
from app.services.paper_service import paper_service
from app.services.version_service import version_service
from app.utils.exporters import markdown_to_docx, markdown_to_pdf

router = APIRouter()


class TopicRecommendRequest(BaseModel):
    """选题推荐请求"""

    field: str = Field(..., min_length=1, description="研究领域")
    keywords: str = Field("", description="关键词，逗号分隔")
    requirements: str = Field("", description="特殊要求")


@router.post("/", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    paper_data: PaperCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """创建新论文"""
    return await paper_service.create(
        db,
        paper_data,
        author_id=current_user.id if current_user else None,
    )


@router.get("/", response_model=List[PaperResponse])
async def list_papers(
    skip: int = 0,
    limit: int = 20,
    status: Optional[PaperStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取论文列表"""
    return await paper_service.list(
        db,
        skip=skip,
        limit=limit,
        status=status,
        author_id=current_user.id if current_user else None,
    )


@router.get("/{paper_id}", response_model=PaperDetail)
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取论文详情"""
    paper = await paper_service.get(db, paper_id)
    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"论文 ID {paper_id} 不存在",
        )
    return paper


@router.put("/{paper_id}", response_model=PaperResponse)
async def update_paper(
    paper_id: int,
    paper_data: PaperUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新论文"""
    old_paper = await paper_service.get(db, paper_id)
    if old_paper is None:
        raise HTTPException(status_code=404, detail="论文不存在")
    old_topic = old_paper.topic or ""

    paper = await paper_service.update(db, paper_id, paper_data)
    if paper is None:
        raise HTTPException(status_code=404, detail="论文不存在")

    # 关键节点：选题确认后自动版本（用户明确填写/修改了选题方向）
    if paper_data.topic and paper.topic and paper.topic != old_topic:
        await version_service.auto_version(
            paper_id,
            f"选题确认：{paper.topic}",
            trigger_node="topic",
            workflow_state={"last_node": "analyze_topic", "topic": paper.topic},
        )

    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除论文"""
    deleted = await paper_service.delete(db, paper_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="论文不存在")


@router.post("/{paper_id}/generate", dependencies=[Depends(require_llm_config)])
async def generate_paper(
    paper_id: int,
    options: Optional[PaperGenerateRequest] = Body(None),
):
    """触发论文生成工作流（非流式，等待全部完成后返回）"""
    try:
        result = await paper_service.generate(
            paper_id,
            options.model_dump(exclude_none=True) if options else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"论文生成失败：{exc}")

    return {"message": "论文生成完成", "paper_id": paper_id, **result}


@router.post("/{paper_id}/outline", dependencies=[Depends(require_llm_config)])
async def generate_outline(
    paper_id: int,
    options: Optional[PaperGenerateRequest] = Body(None),
):
    """仅生成论文大纲"""
    try:
        outline = await paper_service.generate_outline(
            paper_id,
            options.model_dump(exclude_none=True) if options else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"大纲生成失败：{exc}")

    return {"paper_id": paper_id, "outline": outline}


@router.post("/{paper_id}/topics", dependencies=[Depends(require_llm_config)])
async def recommend_topics(
    paper_id: int,
    payload: TopicRecommendRequest,
):
    """智能选题推荐"""
    try:
        topics = await paper_service.recommend_topics(
            field=payload.field,
            keywords=payload.keywords,
            requirements=payload.requirements,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"选题推荐失败：{exc}")

    return {"paper_id": paper_id, "topics": topics}


@router.get("/{paper_id}/stream-generate")
async def stream_generate_paper(
    paper_id: int,
    polish: bool = True,
    is_topic_clear: bool = True,
):
    """流式生成论文（SSE）"""

    async def event_generator():
        from app.utils.llm import is_llm_configured

        if not is_llm_configured():
            message = "尚未配置大模型 API Key，请在 backend/.env 中填写 QWEN_API_KEY 后重启后端服务"
            yield f"data: {json.dumps({'event': 'error', 'message': message}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        options = {"polish": polish, "is_topic_clear": is_topic_clear}
        try:
            async for event in paper_service.stream(paper_id, options):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'event': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# 导出格式配置：格式 → (媒体类型, 文件后缀)
_EXPORT_FORMATS = {
    "md": ("text/markdown; charset=utf-8", "md"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    "pdf": ("application/pdf", "pdf"),
}


def _safe_filename(title: str) -> str:
    """清理文件名中的非法字符"""
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", title or "论文").strip()
    return (name or "论文")[:80]


@router.get("/{paper_id}/export")
async def export_paper(
    paper_id: int,
    fmt: str = Query("docx", alias="format", pattern="^(md|docx|pdf)$", description="导出格式"),
    db: AsyncSession = Depends(get_db),
):
    """导出论文为 Markdown / Word(.docx) / PDF"""
    paper = await paper_service.get(db, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="论文不存在")

    content = paper.content or ""
    if not content.strip():
        raise HTTPException(status_code=400, detail="论文暂无内容，请先生成或撰写正文")

    title = paper.title or "论文"
    if fmt == "docx":
        # 文档生成是 CPU 密集操作，放到线程池避免阻塞事件循环
        data = await run_in_threadpool(markdown_to_docx, title, content)
    elif fmt == "pdf":
        data = await run_in_threadpool(markdown_to_pdf, title, content)
    else:
        data = content.encode("utf-8")

    media_type, suffix = _EXPORT_FORMATS[fmt]
    filename = f"{_safe_filename(title)}.{suffix}"

    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={
            # 中文文件名使用 RFC 5987 编码
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            "Content-Length": str(len(data)),
        },
    )