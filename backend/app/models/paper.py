"""论文数据模型"""

import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database import Base


class PaperStatus(enum.Enum):
    """论文状态枚举"""

    DRAFT = "draft"           # 草稿
    OUTLINE = "outline"       # 大纲阶段
    WRITING = "writing"       # 撰写中
    REVIEW = "review"         # 审核中
    COMPLETED = "completed"   # 已完成


class Paper(Base):
    """论文数据模型"""

    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, comment="论文标题")
    topic = Column(String(200), comment="选题方向")
    keywords = Column(String(500), comment="关键词，逗号分隔")
    abstract = Column(Text, comment="摘要")
    status = Column(Enum(PaperStatus), default=PaperStatus.DRAFT, comment="状态")
    outline = Column(Text, comment="大纲 JSON")
    content = Column(Text, comment="论文全文")
    paper_type = Column(String(50), default="research", comment="论文类型")
    word_limit = Column(Integer, default=10000, comment="目标字数")

    # 元数据
    author_id = Column(Integer, ForeignKey("users.id"), comment="作者 ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系
    author = relationship("User", back_populates="papers")
    chapters = relationship("Chapter", back_populates="paper", cascade="all, delete-orphan")
    references = relationship("Reference", back_populates="paper", cascade="all, delete-orphan")
    versions = relationship(
        "PaperVersion",
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="PaperVersion.version_number",
    )

    def __repr__(self):
        return f"<Paper(id={self.id}, title='{self.title}', status='{self.status}')>"