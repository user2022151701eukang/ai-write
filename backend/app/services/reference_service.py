"""文献业务服务 - 文献 CRUD 与向量库同步"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.reference_agent import ReferenceAgent
from app.models.reference import Reference
from app.rag.vector_store import vector_store
from app.schemas.paper import ReferenceCreate, ReferenceUpdate
from app.utils.helpers import build_reference_text, format_reference

logger = logging.getLogger(__name__)


class ReferenceService:
    """文献服务：数据库与向量库双写"""

    def __init__(self):
        self.agent = ReferenceAgent()

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    async def list(
        self,
        db: AsyncSession,
        paper_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        keyword: Optional[str] = None,
    ) -> List[Reference]:
        """获取文献列表"""
        query = select(Reference)

        if paper_id is not None:
            query = query.where(Reference.paper_id == paper_id)
        if keyword:
            query = query.where(Reference.title.contains(keyword))

        query = query.offset(skip).limit(limit).order_by(Reference.year.desc().nullslast(), Reference.id.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, reference_id: int) -> Optional[Reference]:
        """获取文献详情"""
        result = await db.execute(select(Reference).where(Reference.id == reference_id))
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------
    async def create(self, db: AsyncSession, data: ReferenceCreate) -> Reference:
        """新增文献（同时写入向量库）"""
        reference = Reference(**data.model_dump())
        db.add(reference)
        await db.commit()
        await db.refresh(reference)

        await self.sync_to_vector_store(reference)
        await db.refresh(reference)
        return reference

    async def bulk_create(self, db: AsyncSession, items: List[ReferenceCreate]) -> List[Reference]:
        """批量新增文献"""
        references = [Reference(**item.model_dump()) for item in items]
        db.add_all(references)
        await db.commit()

        for reference in references:
            await db.refresh(reference)
            await self.sync_to_vector_store(reference)

        return references

    async def update(
        self,
        db: AsyncSession,
        reference_id: int,
        data: ReferenceUpdate,
    ) -> Optional[Reference]:
        """更新文献（同步刷新向量）"""
        reference = await self.get(db, reference_id)
        if reference is None:
            return None

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(reference, key, value)

        await db.commit()
        await db.refresh(reference)

        await self.sync_to_vector_store(reference)
        await db.refresh(reference)
        return reference

    async def delete(self, db: AsyncSession, reference_id: int) -> bool:
        """删除文献（同时移除向量）"""
        reference = await self.get(db, reference_id)
        if reference is None:
            return False

        if reference.vector_id:
            try:
                vector_store.delete_document(reference.vector_id)
            except Exception as exc:
                logger.warning("删除向量失败：%s", exc)

        await db.delete(reference)
        await db.commit()
        return True

    # ------------------------------------------------------------------
    # 向量库同步
    # ------------------------------------------------------------------
    async def sync_to_vector_store(self, reference: Reference) -> None:
        """将文献写入/更新到向量库"""
        try:
            vector_id = reference.vector_id or str(reference.id)
            vector_store.delete_document(vector_id)
            vector_store.add_documents([{
                "id": vector_id,
                "text": build_reference_text({
                    "title": reference.title,
                    "authors": reference.authors,
                    "journal": reference.journal,
                    "year": reference.year,
                    "abstract": reference.abstract,
                }),
                "metadata": {
                    "reference_id": reference.id,
                    "title": reference.title,
                    "authors": reference.authors or "",
                    "journal": reference.journal or "",
                    "year": reference.year or 0,
                    "paper_id": reference.paper_id or 0,
                },
            }])
            reference.vector_id = vector_id
        except Exception as exc:
            logger.warning("文献「%s」向量化失败：%s", reference.title, exc)
            reference.vector_id = None

    async def rebuild_vector_store(self, db: AsyncSession) -> int:
        """重建向量库（全量重新向量化）"""
        vector_store.clear()
        references = await self.list(db, limit=1000)
        for reference in references:
            await self.sync_to_vector_store(reference)
        await db.commit()
        return len(references)

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------
    async def search(
        self,
        query: str,
        top_k: int = 5,
        format_style: str = "gbt",
    ) -> Dict[str, Any]:
        """RAG 检索并生成标准引用"""
        result = await self.agent.execute({
            "query": query,
            "top_k": top_k,
            "format": format_style,
        })

        references = [
            {
                "id": doc.get("metadata", {}).get("reference_id"),
                "title": doc.get("metadata", {}).get("title", doc.get("text", "")),
                "authors": doc.get("metadata", {}).get("authors", ""),
                "journal": doc.get("metadata", {}).get("journal", ""),
                "year": doc.get("metadata", {}).get("year"),
                "score": round(float(doc.get("score", 0)), 4),
                "citation": format_reference(doc.get("metadata", {}), format_style),
            }
            for doc in result.get("references", [])
        ]

        return {
            "query": query,
            "references": references,
            "formatted": result.get("formatted", ""),
            "error": result.get("error"),
        }

    def status(self) -> Dict[str, Any]:
        """向量库状态"""
        from app.utils.llm import is_embedding_configured, is_llm_configured

        return {
            "vector_count": vector_store.get_document_count(),
            "llm_configured": is_llm_configured(),
            "embedding_configured": is_embedding_configured(),
        }


# 全局服务实例
reference_service = ReferenceService()