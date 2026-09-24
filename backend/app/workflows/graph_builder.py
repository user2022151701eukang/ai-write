"""LangGraph 图构建器 - 多 Agent 协作工作流"""

import json
from typing import Any, AsyncIterator, Dict

from langgraph.graph import StateGraph, END

from app.agents.topic_agent import TopicAgent
from app.agents.outline_agent import OutlineAgent
from app.agents.writer_agent import WriterAgent
from app.agents.reference_agent import ReferenceAgent
from app.agents.polish_agent import PolishAgent
from app.utils.helpers import assemble_paper, count_words, truncate
from app.workflows.state import PaperState


class PaperWorkflowGraph:
    """论文生成工作流图构建器"""

    def __init__(self):
        # 初始化所有 Agent
        self.topic_agent = TopicAgent()
        self.outline_agent = OutlineAgent()
        self.writer_agent = WriterAgent()
        self.reference_agent = ReferenceAgent()
        self.polish_agent = PolishAgent()

        # 创建工作流图
        self.graph = self._build_graph()

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------
    def _build_graph(self):
        """构建工作流图"""
        workflow = StateGraph(PaperState)

        # 添加节点
        workflow.add_node("analyze_topic", self._analyze_topic)
        workflow.add_node("recommend_topic", self._recommend_topic)
        workflow.add_node("generate_outline", self._generate_outline)
        workflow.add_node("write_sections", self._write_sections)
        workflow.add_node("add_references", self._add_references)
        workflow.add_node("polish_paper", self._polish_paper)
        workflow.add_node("quality_check", self._quality_check)

        # 设置入口点
        workflow.set_entry_point("analyze_topic")

        # 添加边（状态转换）
        workflow.add_conditional_edges(
            "analyze_topic",
            self._should_recommend_topic,
            {
                "recommend": "recommend_topic",
                "outline": "generate_outline",
            },
        )

        # 选题不明确时：输出选题推荐后结束，等待用户确认
        workflow.add_edge("recommend_topic", END)

        workflow.add_edge("generate_outline", "write_sections")
        workflow.add_edge("write_sections", "add_references")
        workflow.add_edge("add_references", "polish_paper")
        workflow.add_edge("polish_paper", "quality_check")

        workflow.add_conditional_edges(
            "quality_check",
            self._check_quality,
            {
                "pass": END,
                "revise": "write_sections",
            },
        )

        return workflow.compile()

    # ------------------------------------------------------------------
    # 节点实现
    # ------------------------------------------------------------------
    async def _analyze_topic(self, state: PaperState) -> Dict[str, Any]:
        """分析选题"""
        return {
            "current_step": "analyze_topic",
            "is_topic_clear": state.get("is_topic_clear", True),
        }

    async def _recommend_topic(self, state: PaperState) -> Dict[str, Any]:
        """推荐选题（选题不明确时）"""
        result = await self.topic_agent.execute({
            "field": state.get("topic") or state.get("title", ""),
            "keywords": ", ".join(state.get("keywords") or []),
        })
        return {
            "current_step": "topic_recommend",
            "analysis_result": result.get("topics", ""),
        }

    async def _generate_outline(self, state: PaperState) -> Dict[str, Any]:
        """生成大纲"""
        result = await self.outline_agent.execute({
            "title": state.get("title", ""),
            "topic": state.get("topic", ""),
            "paper_type": state.get("paper_type", "research"),
            "word_limit": state.get("word_limit", 10000),
        })
        return {
            "current_step": "outline",
            "outline": result.get("outline_dict", {}),
        }

    async def _write_sections(self, state: PaperState) -> Dict[str, Any]:
        """撰写章节（多 Agent 并行/串行协作）"""
        outline = state.get("outline") or {}
        sections = outline.get("sections", [])
        sections_content: Dict[str, str] = dict(state.get("sections_content") or {})
        references = state.get("references") or []

        for section in sections:
            title = section.get("title", "")
            result = await self.writer_agent.execute({
                "section_title": title,
                "outline_points": section.get("points", []),
                "references": [ref.get("title", "") for ref in references],
                "word_count": section.get("word_count", 1000),
                "context": self._build_context(sections_content),
            })
            sections_content[title] = result.get("content", "")

        return {
            "current_step": "writing",
            "sections_content": sections_content,
        }

    async def _add_references(self, state: PaperState) -> Dict[str, Any]:
        """添加参考文献"""
        result = await self.reference_agent.execute({
            "query": state.get("title", "") + " " + (state.get("topic") or ""),
            "top_k": 10,
        })
        return {
            "current_step": "references",
            "references": result.get("references", []),
            "formatted_references": result.get("formatted", ""),
        }

    async def _polish_paper(self, state: PaperState) -> Dict[str, Any]:
        """润色论文"""
        sections_content = state.get("sections_content") or {}
        full_content = assemble_paper(state.get("title", ""), sections_content)

        result = await self.polish_agent.execute({
            "content": full_content,
            "focus": "all",
        })

        return {
            "current_step": "polish",
            "final_paper": result.get("polished", ""),
        }

    async def _quality_check(self, state: PaperState) -> Dict[str, Any]:
        """质量检查"""
        revision_count = state.get("revision_count", 0)

        has_content = bool(state.get("final_paper"))
        has_references = bool(state.get("references"))
        word_count = count_words(state.get("final_paper") or "")
        target = state.get("word_limit", 10000)

        quality_score = 0.5
        if has_content and has_references:
            quality_score = 0.8
        if word_count >= target * 0.6:
            quality_score = min(1.0, quality_score + 0.1)

        return {
            "current_step": "quality_check",
            "quality_score": quality_score,
            "revision_count": revision_count + 1,
        }

    # ------------------------------------------------------------------
    # 条件边
    # ------------------------------------------------------------------
    def _should_recommend_topic(self, state: PaperState) -> str:
        """判断是否需要推荐选题"""
        if state.get("is_topic_clear", True):
            return "outline"
        return "recommend"

    def _check_quality(self, state: PaperState) -> str:
        """检查质量是否达标"""
        quality_score = state.get("quality_score", 0)
        revision_count = state.get("revision_count", 0)
        max_revisions = state.get("max_revisions", 3)

        if quality_score >= 0.7 or revision_count >= max_revisions:
            return "pass"
        return "revise"

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    @staticmethod
    def _build_context(sections_content: Dict[str, str]) -> str:
        """构造已撰写章节的上下文摘要"""
        if not sections_content:
            return ""
        parts = [
            f"{title}：{truncate(content, 150)}"
            for title, content in sections_content.items()
        ]
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # 运行入口
    # ------------------------------------------------------------------
    async def run(self, initial_state: PaperState) -> Dict[str, Any]:
        """运行工作流"""
        return await self.graph.ainvoke(initial_state)

    async def stream(self, initial_state: PaperState) -> AsyncIterator[Dict[str, Any]]:
        """流式运行工作流"""
        async for event in self.graph.astream(initial_state):
            yield event

    @staticmethod
    def dumps_outline(outline: dict) -> str:
        """序列化大纲为 JSON 字符串"""
        return json.dumps(outline, ensure_ascii=False)


# 创建全局工作流图实例
paper_workflow_graph = PaperWorkflowGraph()