"""LangGraph 工作流状态定义"""

from typing import Annotated, Dict, List, Optional, TypedDict

from langgraph.graph.message import add_messages


class PaperState(TypedDict, total=False):
    """论文生成工作流状态"""

    # 基本信息
    paper_id: int
    title: str
    topic: str
    keywords: List[str]
    paper_type: str
    word_limit: int

    # 工作流控制
    current_step: str
    is_topic_clear: bool
    requires_revision: bool

    # 内容存储
    outline: Optional[dict]
    current_section: Optional[str]
    sections_content: Dict[str, str]

    # 文献相关
    references: List[dict]
    formatted_references: Optional[str]
    analysis_result: Optional[str]

    # 质量控制
    quality_score: float
    revision_count: int
    max_revisions: int

    # 输出
    final_paper: Optional[str]
    messages: Annotated[list, add_messages]