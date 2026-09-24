"""章节相关 Pydantic 模式"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChapterBase(BaseModel):
    """章节基础模式"""

    title: str = Field(..., min_length=1, max_length=200, description="章节标题")
    content: Optional[str] = Field(None, description="章节内容")
    summary: Optional[str] = Field(None, description="章节摘要")
    order_index: Optional[int] = Field(0, description="排序索引")
    parent_id: Optional[int] = Field(None, description="父章节 ID")


class ChapterCreate(ChapterBase):
    """创建章节模式"""

    paper_id: int = Field(..., description="所属论文 ID")


class ChapterUpdate(BaseModel):
    """更新章节模式"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    summary: Optional[str] = None
    order_index: Optional[int] = None
    parent_id: Optional[int] = None


class ChapterResponse(ChapterBase):
    """章节响应模式"""

    id: int
    paper_id: int
    word_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChapterGenerateRequest(BaseModel):
    """AI 撰写章节请求模式"""

    word_count: Optional[int] = Field(1000, ge=200, le=8000, description="目标字数")
    style: Optional[str] = Field("formal", description="写作风格")
    outline_points: Optional[list] = Field(None, description="内容要点")
    use_references: Optional[bool] = Field(True, description="是否结合参考文献")


class ChapterPolishRequest(BaseModel):
    """AI 润色章节请求模式"""

    focus: Optional[str] = Field("all", description="润色重点：language / logic / format / all")