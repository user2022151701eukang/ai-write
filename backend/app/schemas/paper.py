"""论文 / 文献相关 Pydantic 模式"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.paper import PaperStatus


# ---------------------------------------------------------------------------
# 论文模式
# ---------------------------------------------------------------------------

class PaperBase(BaseModel):
    """论文基础模式"""

    title: str = Field(..., min_length=5, max_length=500, description="论文标题")
    topic: Optional[str] = Field(None, max_length=200, description="选题方向")
    keywords: Optional[str] = Field(None, max_length=500, description="关键词")
    abstract: Optional[str] = Field(None, description="摘要")


class PaperCreate(PaperBase):
    """创建论文模式"""

    paper_type: Optional[str] = Field("research", description="论文类型")
    word_limit: Optional[int] = Field(10000, ge=1000, le=100000, description="目标字数")


class PaperUpdate(BaseModel):
    """更新论文模式"""

    title: Optional[str] = Field(None, min_length=5, max_length=500)
    topic: Optional[str] = None
    keywords: Optional[str] = None
    abstract: Optional[str] = None
    outline: Optional[str] = None
    content: Optional[str] = None
    paper_type: Optional[str] = None
    word_limit: Optional[int] = None
    status: Optional[PaperStatus] = None


class PaperResponse(PaperBase):
    """论文响应模式"""

    id: int
    status: PaperStatus
    outline: Optional[str] = None
    content: Optional[str] = None
    paper_type: Optional[str] = "research"
    word_limit: Optional[int] = 10000
    author_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChapterBrief(BaseModel):
    """章节简要信息"""

    id: int
    title: str
    order_index: int

    class Config:
        from_attributes = True


class ReferenceBrief(BaseModel):
    """文献简要信息"""

    id: int
    title: str
    authors: Optional[str] = None
    year: Optional[int] = None

    class Config:
        from_attributes = True


class PaperDetail(PaperResponse):
    """论文详情模式"""

    chapters: List[ChapterBrief] = []
    references: List[ReferenceBrief] = []


class PaperGenerateRequest(BaseModel):
    """论文生成请求模式"""

    paper_type: Optional[str] = Field("research", description="论文类型")
    word_limit: Optional[int] = Field(10000, ge=1000, le=100000, description="目标字数")
    is_topic_clear: Optional[bool] = Field(True, description="选题是否明确")
    topic: Optional[str] = Field(None, description="确认/覆盖的选题")


# ---------------------------------------------------------------------------
# 文献模式
# ---------------------------------------------------------------------------

class ReferenceBase(BaseModel):
    """文献基础模式"""

    title: str = Field(..., max_length=500, description="文献标题")
    authors: Optional[str] = Field(None, max_length=500, description="作者")
    journal: Optional[str] = Field(None, max_length=200, description="期刊名")
    year: Optional[int] = Field(None, description="发表年份")
    volume: Optional[str] = Field(None, max_length=50, description="卷号")
    issue: Optional[str] = Field(None, max_length=50, description="期号")
    pages: Optional[str] = Field(None, max_length=50, description="页码")
    doi: Optional[str] = Field(None, max_length=100, description="DOI")
    url: Optional[str] = Field(None, max_length=500, description="链接")
    abstract: Optional[str] = Field(None, description="摘要")


class ReferenceCreate(ReferenceBase):
    """创建文献模式"""

    paper_id: Optional[int] = Field(None, description="关联论文 ID")


class ReferenceUpdate(BaseModel):
    """更新文献模式"""

    title: Optional[str] = None
    authors: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None


class ReferenceResponse(ReferenceBase):
    """文献响应模式"""

    id: int
    paper_id: Optional[int] = None
    vector_id: Optional[str] = None

    class Config:
        from_attributes = True


class ReferenceSearchRequest(BaseModel):
    """文献检索请求模式"""

    query: str = Field(..., min_length=1, description="检索主题")
    top_k: int = Field(5, ge=1, le=20, description="返回条数")
    format: str = Field("gbt", description="引用格式：gbt / apa / mla")


class ReferenceSearchResponse(BaseModel):
    """文献检索响应模式"""

    query: str
    references: List[dict] = []
    formatted: str = ""


# 更新前向引用
PaperDetail.model_rebuild()