"""参考文献数据模型"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Reference(Base):
    """参考文献模型"""

    __tablename__ = "references"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), comment="关联论文")

    title = Column(String(500), nullable=False, comment="文献标题")
    authors = Column(String(500), comment="作者")
    journal = Column(String(200), comment="期刊名")
    year = Column(Integer, comment="发表年份")
    volume = Column(String(50), comment="卷号")
    issue = Column(String(50), comment="期号")
    pages = Column(String(50), comment="页码")
    doi = Column(String(100), comment="DOI")
    url = Column(String(500), comment="链接")
    abstract = Column(Text, comment="摘要")

    # 向量存储的 ID，用于相似度检索
    vector_id = Column(String(100), comment="向量库 ID")

    # 关系
    paper = relationship("Paper", back_populates="references")

    def __repr__(self):
        return f"<Reference(id={self.id}, title='{self.title}')>"