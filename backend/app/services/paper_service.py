"""论文业务服务"""

from typing import Any, AsyncIterator, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.paper import Paper, PaperStatus
from app.schemas.paper import PaperCreate, PaperUpdate
from app.workflows.paper_workflow import paper_workflow


class PaperService:
    """论文服务：CRUD + 生成工作流调度"""

    async def create(
        self,
        db: AsyncSession,
        data: PaperCreate,
        author_id: Optional[int] = None,
    ) -> Paper:
        """创建论文"""
        paper = Paper(**data.model_dump(), author_id=author_id)
        db.add(paper)
        await db.commit()
        await db.refresh(paper)
        return paper

    async def list(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        status: Optional[PaperStatus] = None,
        author_id: Optional[int] = None,
    ) -> List[Paper]:
        """获取论文列表"""
        query = select(Paper)

        if status:
            query = query.where(Paper.status == status)
        if author_id is not None:
            query = query.where(Paper.author_id == author_id)

        query = query.offset(skip).limit(limit).order_by(Paper.updated_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, paper_id: int) -> Optional[Paper]:
        """获取论文详情（含章节与文献）"""
        result = await db.execute(
            select(Paper)
            .options(selectinload(Paper.chapters), selectinload(Paper.references))
            .where(Paper.id == paper_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        db: AsyncSession,
        paper_id: int,
        data: PaperUpdate,
    ) -> Optional[Paper]:
        """更新论文"""
        paper = await self.get(db, paper_id)
        if paper is None:
            return None

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(paper, key, value)

        await db.commit()
        await db.refresh(paper)
        return paper

    async def delete(self, db: AsyncSession, paper_id: int) -> bool:
        """删除论文"""
        paper = await self.get(db, paper_id)
        if paper is None:
            return False

        await db.delete(paper)
        await db.commit()
        return True

    # ------------------------------------------------------------------
    # 生成工作流
    # ------------------------------------------------------------------
    async def generate(
        self,
        paper_id: int,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """运行完整生成工作流"""
        return await paper_workflow.run(paper_id, options)

    async def stream(
        self,
        paper_id: int,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式生成论文"""
        async for event in paper_workflow.stream(paper_id, options):
            yield event

    async def generate_outline(
        self,
        paper_id: int,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """仅生成大纲"""
        return await paper_workflow.generate_outline(paper_id, options)

    async def recommend_topics(
        self,
        field: str,
        keywords: str = "",
        requirements: str = "",
    ) -> str:
        """推荐论文选题"""
        return await paper_workflow.recommend_topics(field, keywords, requirements)


# 全局服务实例
paper_service = PaperService()