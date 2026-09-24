"""论文生成工作流 - 业务编排、结果落库与 SSE 事件流"""

import json
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from sqlalchemy import delete, select, update

from app.database import AsyncSessionLocal
from app.models.chapter import Chapter
from app.models.paper import Paper, PaperStatus
from app.models.reference import Reference
from app.services.version_service import version_service
from app.utils.helpers import assemble_paper, count_words, strip_ai_meta, truncate
from app.workflows.graph_builder import PaperWorkflowGraph, paper_workflow_graph

logger = logging.getLogger(__name__)


class PaperWorkflow:
    """论文生成工作流（业务层）：串联各 Agent、产出 SSE 事件并落库"""

    def __init__(self, graph: Optional[PaperWorkflowGraph] = None):
        self.graph_builder = graph or paper_workflow_graph

    # ------------------------------------------------------------------
    # 事件工具
    # ------------------------------------------------------------------
    @staticmethod
    def _event(event: str, **payload: Any) -> Dict[str, Any]:
        """构造 SSE 事件"""
        return {"event": event, **payload}

    # ------------------------------------------------------------------
    # 数据读取
    # ------------------------------------------------------------------
    async def _load_paper(self, paper_id: int) -> Optional[Dict[str, Any]]:
        """读取论文基础信息（使用独立会话，避免长事务占用连接）"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Paper).where(Paper.id == paper_id))
            paper = result.scalar_one_or_none()
            if paper is None:
                return None
            return {
                "id": paper.id,
                "title": paper.title,
                "topic": paper.topic or "",
                "keywords": [k.strip() for k in (paper.keywords or "").split(",") if k.strip()],
                "paper_type": paper.paper_type or "research",
                "word_limit": paper.word_limit or 10000,
            }

    # ------------------------------------------------------------------
    # 选题推荐
    # ------------------------------------------------------------------
    async def recommend_topics(self, field: str, keywords: str = "", requirements: str = "") -> str:
        """推荐选题（用于「智能选题推荐」功能）"""
        result = await self.graph_builder.topic_agent.execute({
            "field": field,
            "keywords": keywords,
            "requirements": requirements,
        })
        return result.get("topics", "")

    # ------------------------------------------------------------------
    # 大纲生成（仅大纲，不撰写正文）
    # ------------------------------------------------------------------
    async def generate_outline(self, paper_id: int, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """为指定论文生成大纲并保存"""
        options = options or {}
        paper = await self._load_paper(paper_id)
        if paper is None:
            raise LookupError(f"论文 ID {paper_id} 不存在")

        result = await self.graph_builder.outline_agent.execute({
            "title": paper["title"],
            "topic": options.get("topic") or paper["topic"],
            "paper_type": options.get("paper_type") or paper["paper_type"],
            "word_limit": options.get("word_limit") or paper["word_limit"],
        })
        outline = result.get("outline_dict") or {"title": paper["title"], "sections": []}

        async with AsyncSessionLocal() as session:
            db_paper = (await session.execute(select(Paper).where(Paper.id == paper_id))).scalar_one_or_none()
            if db_paper is not None:
                db_paper.outline = json.dumps(outline, ensure_ascii=False)
                if db_paper.status == PaperStatus.DRAFT:
                    db_paper.status = PaperStatus.OUTLINE
                await session.commit()

        # 关键节点：大纲生成后自动版本
        await version_service.auto_version(
            paper_id,
            "大纲生成完成",
            trigger_node="outline",
            workflow_state={"last_node": "outline", "note": "仅生成大纲"},
        )

        return outline

    # ------------------------------------------------------------------
    # 完整生成（非流式，基于 LangGraph 图）
    # ------------------------------------------------------------------
    async def run(self, paper_id: int, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """运行完整论文生成工作流并落库"""
        options = options or {}
        paper = await self._load_paper(paper_id)
        if paper is None:
            raise LookupError(f"论文 ID {paper_id} 不存在")

        initial_state = {
            "paper_id": paper["id"],
            "title": paper["title"],
            "topic": options.get("topic") or paper["topic"] or paper["title"],
            "keywords": paper["keywords"],
            "paper_type": options.get("paper_type") or paper["paper_type"],
            "word_limit": options.get("word_limit") or paper["word_limit"],
            "current_step": "init",
            "is_topic_clear": options.get("is_topic_clear", True),
            "requires_revision": False,
            "sections_content": {},
            "references": [],
            "revision_count": 0,
            "max_revisions": options.get("max_revisions", 3),
            "messages": [],
        }

        final_state = await self.graph_builder.run(initial_state)

        saved = await self._save_result(
            paper,
            final_state.get("outline") or {},
            final_state.get("sections_content") or {},
            final_state.get("references") or [],
            final_state.get("final_paper") or "",
        )

        # 关键节点自动版本：选题推荐（选题不明确时）或质量检查通过
        if final_state.get("current_step") == "topic_recommend":
            await version_service.auto_version(
                paper_id,
                "选题推荐完成",
                trigger_node="topic_recommend",
                workflow_state={"last_node": "recommend_topic"},
            )
        else:
            quality_score = final_state.get("quality_score", 0)
            await version_service.auto_version(
                paper_id,
                f"论文生成完成（质量检查 {quality_score}）· 含大纲/撰写/文献/润色",
                trigger_node="quality_check",
                workflow_state={
                    "last_node": "quality_check",
                    "quality_score": quality_score,
                    "note": "非流式完整工作流（大纲→撰写→文献→润色→质检）",
                },
            )

        return {
            "paper_id": paper_id,
            "current_step": final_state.get("current_step", ""),
            "quality_score": final_state.get("quality_score", 0),
            "analysis_result": final_state.get("analysis_result"),
            "outline": final_state.get("outline") or {},
            "chapters": saved["chapters"],
            "reference_count": len(final_state.get("references") or []),
        }

    # ------------------------------------------------------------------
    # 完整生成（流式，SSE 事件）
    # ------------------------------------------------------------------
    async def stream(
        self,
        paper_id: int,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式生成论文，逐阶段产出事件"""
        options = options or {}
        paper = await self._load_paper(paper_id)
        if paper is None:
            yield self._event("error", message=f"论文 ID {paper_id} 不存在")
            return

        is_topic_clear = options.get("is_topic_clear", True)
        enable_polish = options.get("polish", True)
        topic = options.get("topic") or paper["topic"] or paper["title"]
        paper_type = options.get("paper_type") or paper["paper_type"]
        word_limit = options.get("word_limit") or paper["word_limit"]

        # ---------- 1. 选题分析 ----------
        yield self._event("status", step="analyze_topic", message="正在分析选题...", progress=5)

        if not is_topic_clear:
            buffer = ""
            async for chunk in self.graph_builder.topic_agent.stream_execute({
                "field": topic,
                "keywords": ", ".join(paper["keywords"]),
            }):
                buffer += chunk
                yield self._event("token", scope="topic", content=chunk)
            yield self._event("topics", content=buffer)
            return

        # ---------- 2. 大纲生成 ----------
        yield self._event("status", step="outline", message="正在生成论文大纲...", progress=15)
        try:
            outline_result = await self.graph_builder.outline_agent.execute({
                "title": paper["title"],
                "topic": topic,
                "paper_type": paper_type,
                "word_limit": word_limit,
            })
        except Exception as exc:
            yield self._event("error", message=f"大纲生成失败：{exc}")
            return

        outline = outline_result.get("outline_dict") or {}
        sections: List[dict] = outline.get("sections") or []
        if not sections:
            yield self._event("error", message="大纲生成失败，请检查模型配置或稍后重试")
            return
        yield self._event("outline", outline=outline, progress=25)

        # 关键节点：大纲生成后（先落库，保证快照有内容，再自动建版本）
        await self._save_outline_progress(paper_id, outline)
        await version_service.auto_version(
            paper_id,
            "大纲生成完成",
            trigger_node="outline",
            workflow_state={"last_node": "outline"},
        )

        # ---------- 3. 文献检索 ----------
        yield self._event("status", step="references", message="正在检索相关文献...", progress=28)
        references: List[dict] = []
        try:
            ref_result = await self.graph_builder.reference_agent.execute({
                "query": f"{paper['title']} {topic}".strip(),
                "top_k": 8,
            })
            references = ref_result.get("references") or []
        except Exception as exc:
            yield self._event("warning", message=f"文献检索不可用：{exc}")
        yield self._event("references", references=[
            {
                "id": ref.get("id"),
                "title": ref.get("metadata", {}).get("title", ""),
                "authors": ref.get("metadata", {}).get("authors", ""),
                "year": ref.get("metadata", {}).get("year"),
                "score": ref.get("score", 0),
            }
            for ref in references
        ])

        # 关键节点：文献引用完成
        linked = await self._save_reference_links(paper_id, references)
        if linked:
            await version_service.auto_version(
                paper_id,
                f"文献引用完成（{linked} 篇）",
                trigger_node="references",
                workflow_state={"last_node": "add_references", "reference_count": linked},
            )

        # ---------- 4. 分章节撰写 ----------
        reference_titles = [ref.get("metadata", {}).get("title", "") for ref in references if ref.get("metadata")]
        sections_content: Dict[str, str] = {}
        total = len(sections)

        for index, section in enumerate(sections, start=1):
            section_title = section.get("title") or f"第 {index} 节"
            progress = 30 + int(50 * (index - 1) / max(total, 1))
            yield self._event(
                "section_start",
                title=section_title,
                index=index,
                total=total,
                progress=progress,
            )

            buffer = ""
            try:
                async for chunk in self.graph_builder.writer_agent.stream_execute({
                    "section_title": section_title,
                    "outline_points": section.get("points", []),
                    "references": reference_titles,
                    "word_count": section.get("word_count", 1000),
                    "context": self.graph_builder._build_context(sections_content),
                }):
                    buffer += chunk
                    yield self._event("token", scope="section", title=section_title, content=chunk)
            except Exception as exc:
                yield self._event("error", message=f"章节「{section_title}」撰写失败：{exc}")
                return

            # 清理模型在正文后追加的「说明 / 如需扩展…」等非正文内容
            buffer = strip_ai_meta(buffer)
            sections_content[section_title] = buffer
            yield self._event(
                "section_done",
                title=section_title,
                index=index,
                total=total,
                content=buffer,
                word_count=count_words(buffer),
            )

            # 关键节点：每章撰写完成（增量落库后自动建版本，中途中断也不丢进度）
            await self._save_sections_progress(paper_id, sections_content)
            await version_service.auto_version(
                paper_id,
                f"第 {index}/{total} 章撰写完成：{section_title}",
                trigger_node="section",
                workflow_state={
                    "last_node": "write_sections",
                    "section_index": index,
                    "section_total": total,
                },
            )

        full_content = assemble_paper(paper["title"], sections_content)

        # ---------- 5. 润色优化 ----------
        if enable_polish:
            yield self._event("status", step="polish", message="正在进行润色优化...", progress=85)
            polished = ""
            try:
                async for chunk in self.graph_builder.polish_agent.stream_execute({
                    "content": full_content,
                    "focus": "all",
                }):
                    polished += chunk
                    yield self._event("token", scope="polish", content=chunk)
            except Exception as exc:
                yield self._event("warning", message=f"润色优化失败，已保留初稿：{exc}")
                polished = ""

            if polished.strip():
                full_content = polished
            full_content = strip_ai_meta(full_content)
            yield self._event("polish_done", content=full_content)

            # 关键节点：润色完成
            await self._save_content_progress(paper_id, full_content)
            await version_service.auto_version(
                paper_id,
                "全文润色完成",
                trigger_node="polish",
                workflow_state={"last_node": "polish_paper"},
            )

        # ---------- 6. 结果落库 ----------
        yield self._event("status", step="save", message="正在保存论文...", progress=95)
        saved = await self._save_result(
            paper, outline, sections_content, references, full_content,
        )

        # 关键节点：质量检查通过（复用工作流内的规则化质检，不额外消耗模型调用）
        quality = await self.graph_builder._quality_check({
            "final_paper": full_content,
            "references": references,
            "word_limit": word_limit,
            "revision_count": 0,
        })
        quality_score = quality.get("quality_score", 0)
        await version_service.auto_version(
            paper_id,
            f"论文生成完成（质量检查 {quality_score}）",
            trigger_node="quality_check",
            workflow_state={"last_node": "quality_check", "quality_score": quality_score},
        )

        yield self._event(
            "done",
            paper_id=paper_id,
            outline=outline,
            chapters=saved["chapters"],
            reference_count=saved["reference_count"],
            word_count=count_words(full_content),
            content=full_content,
            progress=100,
        )

    # ------------------------------------------------------------------
    # 关键节点增量落库（让自动版本快照反映真实进度）
    # ------------------------------------------------------------------
    async def _save_outline_progress(self, paper_id: int, outline: dict) -> None:
        """大纲生成后落库"""
        async with AsyncSessionLocal() as session:
            paper = (await session.execute(select(Paper).where(Paper.id == paper_id))).scalar_one_or_none()
            if paper is None:
                return
            paper.outline = json.dumps(outline, ensure_ascii=False)
            if paper.status == PaperStatus.DRAFT:
                paper.status = PaperStatus.OUTLINE
            await session.commit()

    async def _save_reference_links(self, paper_id: int, references: List[dict]) -> int:
        """把检索到的文献关联到论文，返回关联数量"""
        linked = 0
        async with AsyncSessionLocal() as session:
            for ref in references:
                metadata = ref.get("metadata") or {}
                reference_id = metadata.get("reference_id")
                if reference_id:
                    await session.execute(
                        update(Reference)
                        .where(Reference.id == int(reference_id))
                        .values(paper_id=paper_id)
                    )
                    linked += 1
                elif metadata.get("title"):
                    session.add(Reference(
                        paper_id=paper_id,
                        title=metadata.get("title"),
                        authors=metadata.get("authors"),
                        journal=metadata.get("journal"),
                        year=metadata.get("year"),
                        vector_id=str(ref.get("id")) if ref.get("id") else None,
                    ))
                    linked += 1
            await session.commit()
        return linked

    async def _save_sections_progress(self, paper_id: int, sections_content: Dict[str, str]) -> None:
        """每章完成后增量落库（重建章节 + 刷新论文全文）"""
        async with AsyncSessionLocal() as session:
            paper = (await session.execute(select(Paper).where(Paper.id == paper_id))).scalar_one_or_none()
            if paper is None:
                return

            await session.execute(delete(Chapter).where(Chapter.paper_id == paper_id))
            for index, (title, content) in enumerate(sections_content.items()):
                session.add(Chapter(
                    paper_id=paper_id,
                    title=title,
                    content=content,
                    summary=truncate(content, 200),
                    order_index=index,
                    word_count=count_words(content),
                ))

            if paper.status in (PaperStatus.DRAFT, PaperStatus.OUTLINE):
                paper.status = PaperStatus.WRITING
            paper.content = assemble_paper(paper.title, sections_content)
            await session.commit()

    async def _save_content_progress(self, paper_id: int, content: str) -> None:
        """润色完成后更新论文全文"""
        async with AsyncSessionLocal() as session:
            paper = (await session.execute(select(Paper).where(Paper.id == paper_id))).scalar_one_or_none()
            if paper is None:
                return
            paper.content = content
            await session.commit()

    # ------------------------------------------------------------------
    # 结果落库
    # ------------------------------------------------------------------
    async def _save_result(
        self,
        paper: Dict[str, Any],
        outline: dict,
        sections_content: Dict[str, str],
        references: List[dict],
        final_content: str,
    ) -> Dict[str, Any]:
        """保存大纲、章节、文献关联与论文全文"""
        chapters_data: List[Dict[str, Any]] = []

        # 统一清理非正文内容（防止模型附加说明进入导出文件）
        sections_content = {title: strip_ai_meta(content) for title, content in sections_content.items()}
        final_content = strip_ai_meta(final_content)

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Paper).where(Paper.id == paper["id"]))
            paper_obj = result.scalar_one_or_none()
            if paper_obj is None:
                return {"chapters": [], "reference_count": 0}

            paper_obj.outline = json.dumps(outline, ensure_ascii=False)
            paper_obj.content = final_content
            paper_obj.status = PaperStatus.COMPLETED
            paper_obj.updated_at = datetime.utcnow()

            abstract = sections_content.get("摘要")
            if abstract:
                paper_obj.abstract = truncate(abstract, 1000)

            # 重建章节
            await session.execute(delete(Chapter).where(Chapter.paper_id == paper_obj.id))
            for index, (title, content) in enumerate(sections_content.items()):
                chapter = Chapter(
                    paper_id=paper_obj.id,
                    title=title,
                    content=content,
                    summary=truncate(content, 200),
                    order_index=index,
                    word_count=count_words(content),
                )
                session.add(chapter)

            # 关联检索到的文献
            reference_count = 0
            for ref in references:
                metadata = ref.get("metadata") or {}
                reference_id = metadata.get("reference_id")
                if reference_id:
                    await session.execute(
                        update(Reference)
                        .where(Reference.id == int(reference_id))
                        .values(paper_id=paper_obj.id)
                    )
                elif metadata.get("title"):
                    session.add(Reference(
                        paper_id=paper_obj.id,
                        title=metadata.get("title"),
                        authors=metadata.get("authors"),
                        journal=metadata.get("journal"),
                        year=metadata.get("year"),
                        vector_id=str(ref.get("id")) if ref.get("id") else None,
                    ))
                reference_count += 1

            await session.commit()

            # commit 后读取生成的主键
            for index, (title, content) in enumerate(sections_content.items()):
                chapters_data.append({"title": title, "order_index": index})

            result = await session.execute(
                select(Chapter).where(Chapter.paper_id == paper_obj.id).order_by(Chapter.order_index)
            )
            chapters_data = [
                {"id": c.id, "title": c.title, "order_index": c.order_index, "word_count": c.word_count}
                for c in result.scalars().all()
            ]

        return {"chapters": chapters_data, "reference_count": reference_count}


# 创建全局工作流实例
paper_workflow = PaperWorkflow()