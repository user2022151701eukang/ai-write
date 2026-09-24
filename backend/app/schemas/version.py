"""版本管理 Pydantic 模式"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VersionCreateRequest(BaseModel):
    """手动保存版本请求"""

    description: str = Field("", max_length=500, description="版本说明")


class VersionSummary(BaseModel):
    """版本列表条目（不含快照内容）"""

    id: int
    paper_id: int
    version_number: int
    version_type: str
    description: str = ""
    trigger_node: Optional[str] = None
    word_count: int = 0
    chapter_count: int = 0
    reference_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class VersionDetail(VersionSummary):
    """版本详情（含全量快照）"""

    snapshot: Dict[str, Any]


class DiffSegment(BaseModel):
    """行内/行级差异片段"""

    type: str  # equal / insert / delete
    text: str


class DiffItem(BaseModel):
    """某个维度下的一条差异项（章节 / 大纲小节 / 文献）"""

    key: str
    title: str
    status: str  # added / removed / modified / unchanged
    old_title: Optional[str] = None
    word_count_old: Optional[int] = None
    word_count_new: Optional[int] = None
    segments: List[DiffSegment] = []
    truncated: bool = False


class DiffDimension(BaseModel):
    """一个对比维度"""

    key: str
    label: str
    status: str  # added / removed / modified / unchanged
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    segments: List[DiffSegment] = []
    items: List[DiffItem] = []


class DiffSide(BaseModel):
    """对比的一侧"""

    version_number: int  # 与「当前内容」对比时返回 0
    label: str
    version_type: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class VersionDiffResponse(BaseModel):
    """结构化差异对比结果"""

    paper_id: int
    left: DiffSide
    right: DiffSide
    summary: Dict[str, int]
    dimensions: List[DiffDimension]


class RollbackResponse(BaseModel):
    """回滚结果"""

    message: str
    paper_id: int
    target_version_number: int
    backup_version_number: int
    rollback_version_number: int
    restored: Dict[str, int]