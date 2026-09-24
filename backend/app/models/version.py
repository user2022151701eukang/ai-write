"""论文版本数据模型 - 全量快照式版本管理"""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class VersionType(str, enum.Enum):
    """版本类型"""

    MANUAL = "manual"        # 用户手动保存
    AUTO = "auto"            # 工作流关键节点自动生成
    ROLLBACK = "rollback"    # 回滚动作生成的新版本
    BACKUP = "backup"        # 回滚前对当前内容的自动备份


class PaperVersion(Base):
    """论文版本快照

    设计约束：
    - 每个版本保存 Paper + Chapters + References + Outline + 工作流状态的**全量 JSON 快照**；
    - 版本一旦创建即为**不可变**，只允许新增，不允许修改历史版本内容；
    - 回滚不会删除后续版本，而是「恢复目标版本内容 + 生成一个新的 rollback 版本」。
    """

    __tablename__ = "paper_versions"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, comment="所属论文")
    version_number = Column(Integer, nullable=False, comment="版本号，同一论文内从 1 递增")
    version_type = Column(String(20), default=VersionType.AUTO.value, comment="版本类型")
    description = Column(String(500), comment="版本说明")
    trigger_node = Column(String(50), comment="触发节点（工作流节点 / rollback）")

    # 全量快照 JSON
    snapshot = Column(Text, nullable=False, comment="全量快照 JSON")
    word_count = Column(Integer, default=0, comment="快照时论文总字数")
    chapter_count = Column(Integer, default=0, comment="快照时章节数")
    reference_count = Column(Integer, default=0, comment="快照时文献数")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    created_by = Column(Integer, ForeignKey("users.id"), comment="操作用户")

    # 关系
    paper = relationship("Paper", back_populates="versions")

    __table_args__ = (Index("idx_versions_paper", "paper_id", "version_number"),)

    def __repr__(self):
        return (
            f"<PaperVersion(paper_id={self.paper_id}, "
            f"version_number={self.version_number}, type='{self.version_type}')>"
        )