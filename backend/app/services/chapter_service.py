"""章节业务服务"""

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.polish_agent import PolishAgent
from app.agents.writer_agent import WriterAgent
from app.models.chapter import Chapter
from app.models.paper import Paper
from app.rag.retriever import retriever
from app.schemas.chapter import ChapterCreate, ChapterUpdate
from app.utils.helpers import assemble_paper, count_words, truncate


class ChapterService:
    """章节服务：CRUD + 单章节 AI 撰写/润色"""

    def __init__(self):
        self.writer_agent = WriterAgent()
        self.polish_agent = PolishAgent()

    async def list_by_paper(self, db: AsyncSession, paper_id: int) -> List[Chapter]:
        """获取论文下的所有章节"""
        result = await db.execute(
            select(Chapter)
            .where(Chapter.paper_id == paper_id)
            .order_by(Chapter.order_index, Chapter.id)
        )
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, chapter_id: int) -> Optional[Chapter]:
        """获取章节详情"""
        result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: ChapterCreate) -> Chapter:
        """创建章节"""
        chapter = Chapter(**data.model_dump(), word_count=count_words(data.content or ""))
        db.add(chapter)
        await db.commit()
        await db.refresh(chapter)
        await self._refresh_paper_content(db, chapter.paper_id)
        return chapter

    async def update(
        self,
        db: AsyncSession,
        chapter_id: int,
        data: ChapterUpdate,
    ) -> Optional[Chapter]:
        """更新章节"""
        chapter = await self.get(db, chapter_id)
        if chapter is None:
            return None

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(chapter, key, value)

        if data.content is not None:
            chapter.word_count = count_words(data.content)
            chapter.summary = truncate(data.content, 200)

        await db.commit()
        await db.refresh(chapter)
        await self._refresh_paper_content(db, chapter.paper_id)
        return chapter

    async def delete(self, db: AsyncSession, chapter_id: int) -> bool:
        """删除章节"""
        chapter = await self.get(db, chapter_id)
        if chapter is None:
            return False

        paper_id = chapter.paper_id
        await db.delete(chapter)
        await db.commit()
        await self._refresh_paper_content(db, paper_id)
        return True

    # ------------------------------------------------------------------
    # AI 能力
    # ------------------------------------------------------------------
    async def generate_content(
        self,
        db: AsyncSession,
        chapter_id: int,
        options: Optional[Dict[str, Any]] = None,
    ) -> Optional[Chapter]:
        """使用写作 Agent 生成章节内容"""
        options = options or {}
        chapter = await self.get(db, chapter_id)
        if chapter is None:
            return None

        paper = (await db.execute(select(Paper).where(Paper.id == chapter.paper_id))).scalar_one_or_none()
        paper_title = paper.title if paper else ""
        paper_topic = (paper.topic if paper else "") or ""

        # RAG 检索相关文献，供写作参考
        reference_titles: List[str] = []
        if options.get("use_references", True):
            try:
                docs = await retriever.search(f"{paper_title} {chapter.title}", top_k=5)
                reference_titles = [
                    doc.get("metadata", {}).get("title", "")
                    for doc in docs
                    if doc.get("metadata", {}).get("title")
                ]
            except Exception:
                reference_titles = []

        result = await self.writer_agent.execute({
            "section_title": chapter.title,
            "outline_points": options.get("outline_points") or [],
            "references": reference_titles,
            "style": options.get("style", "formal"),
            "word_count": options.get("word_count") or chapter.word_count or 1000,
            "context": f"论文标题：{paper_title}\n选题方向：{paper_topic}",
        })

        content = result.get("content", "")
        chapter.content = content
        chapter.word_count = count_words(content)
        chapter.summary = truncate(content, 200)

        await db.commit()
        await db.refresh(chapter)
        await self._refresh_paper_content(db, chapter.paper_id)
        return chapter

    async def polish_content(
        self,
        db: AsyncSession,
        chapter_id: int,
        focus: str = "all",
    ) -> Optional[Chapter]:
        """使用润色 Agent 优化章节内容"""
        chapter = await self.get(db, chapter_id)
        if chapter is None:
            return None

        result = await self.polish_agent.execute({
            "content": chapter.content or "",
            "focus": focus,
        })

        polished = result.get("polished", "")
        if polished.strip():
            chapter.content = polished
            chapter.word_count = count_words(polished)
            chapter.summary = truncate(polished, 200)

        await db.commit()
        await db.refresh(chapter)
        await self._refresh_paper_content(db, chapter.paper_id)
        return chapter

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    async def _refresh_paper_content(self, db: AsyncSession, paper_id: int) -> None:
        """章节变化后刷新论文全文"""
        paper = (await db.execute(select(Paper).where(Paper.id == paper_id))).scalar_one_or_none()
        if paper is None:
            return

        chapters = await self.list_by_paper(db, paper_id)
        sections = {c.title: (c.content or "") for c in chapters if c.content}
        if sections:
            paper.content = assemble_paper(paper.title, sections)
            await db.commit()


# 全局服务实例
chapter_service = ChapterService()