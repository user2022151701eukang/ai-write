"""章节数据模型"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class Chapter(Base):
    """章节模型"""

    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, comment="所属论文")
    parent_id = Column(Integer, ForeignKey("chapters.id"), nullable=True, comment="父章节")
    order_index = Column(Integer, default=0, comment="排序索引")

    title = Column(String(200), nullable=False, comment="章节标题")
    content = Column(Text, comment="章节内容")
    summary = Column(Text, comment="章节摘要")
    word_count = Column(Integer, default=0, comment="章节字数")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    paper = relationship("Paper", back_populates="chapters")
    children = relationship("Chapter", backref="parent", remote_side=[id])

    def __repr__(self):
        return f"<Chapter(id={self.id}, title='{self.title}')>"