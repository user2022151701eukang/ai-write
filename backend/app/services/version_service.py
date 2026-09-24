"""版本管理业务服务 - 全量快照、回滚、结构化差异对比

设计原则：
1. 论文级全量快照：Paper + Chapters + References + Outline + 工作流状态序列化为 JSON；
2. 历史版本不可变：只新增、不修改；
3. 回滚即新版本：先备份当前内容，再恢复目标版本，最后生成 rollback 版本，历史版本全部保留；
4. 差异对比按结构维度做：标题 / 摘要 / 关键词 / 大纲 / 章节 / 参考文献。
"""

import difflib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.chapter import Chapter
from app.models.paper import Paper, PaperStatus
from app.models.reference import Reference
from app.models.version import PaperVersion, VersionType
from app.utils.helpers import count_words

logger = logging.getLogger(__name__)

# 快照格式版本号
SNAPSHOT_FORMAT_VERSION = 1
# 单个维度差异片段上限与字符级对比阈值（避免响应体过大 / 对比过慢）
MAX_SEGMENTS = 400
MAX_INLINE_CHARS = 2000


class VersionService:
    """版本服务：快照创建、版本查询、回滚、结构维度差异对比"""

    # ------------------------------------------------------------------
    # 快照
    # ------------------------------------------------------------------
    async def build_snapshot(
        self,
        db: AsyncSession,
        paper_id: int,
        workflow_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """读取论文当前状态并序列化为全量快照"""
        paper = (
            await db.execute(select(Paper).where(Paper.id == paper_id))
        ).scalar_one_or_none()
        if paper is None:
            return None

        chapters = (
            await db.execute(
                select(Chapter)
                .where(Chapter.paper_id == paper_id)
                .order_by(Chapter.order_index, Chapter.id)
            )
        ).scalars().all()
        references = (
            await db.execute(
                select(Reference).where(Reference.paper_id == paper_id).order_by(Reference.id)
            )
        ).scalars().all()

        return {
            "format_version": SNAPSHOT_FORMAT_VERSION,
            "created_at": datetime.utcnow().isoformat(),
            "paper": {
                "title": paper.title,
                "topic": paper.topic or "",
                "keywords": paper.keywords or "",
                "abstract": paper.abstract or "",
                "status": paper.status.value if paper.status else PaperStatus.DRAFT.value,
                "outline": paper.outline or "",
                "content": paper.content or "",
                "paper_type": paper.paper_type or "research",
                "word_limit": paper.word_limit or 10000,
            },
            "chapters": [
                {
                    "title": c.title,
                    "content": c.content or "",
                    "summary": c.summary or "",
                    "order_index": c.order_index or 0,
                    "word_count": c.word_count or count_words(c.content or ""),
                }
                for c in chapters
            ],
            "references": [
                {
                    "id": r.id,
                    "title": r.title,
                    "authors": r.authors or "",
                    "journal": r.journal or "",
                    "year": r.year,
                    "volume": r.volume or "",
                    "issue": r.issue or "",
                    "pages": r.pages or "",
                    "doi": r.doi or "",
                    "url": r.url or "",
                    "abstract": r.abstract or "",
                    "vector_id": r.vector_id,
                }
                for r in references
            ],
            "workflow": workflow_state or {},
        }

    async def create_snapshot(
        self,
        paper_id: int,
        version_type: str,
        description: str = "",
        trigger_node: Optional[str] = None,
        workflow_state: Optional[Dict[str, Any]] = None,
        created_by: Optional[int] = None,
    ) -> Optional[PaperVersion]:
        """创建快照版本（使用独立会话，避免与调用方长事务耦合）"""
        async with AsyncSessionLocal() as session:
            snapshot = await self.build_snapshot(session, paper_id, workflow_state)
            if snapshot is None:
                return None

            max_number = (
                await session.execute(
                    select(func.max(PaperVersion.version_number)).where(
                        PaperVersion.paper_id == paper_id
                    )
                )
            ).scalar() or 0

            chapters = snapshot.get("chapters") or []
            version = PaperVersion(
                paper_id=paper_id,
                version_number=max_number + 1,
                version_type=version_type,
                description=description or "",
                trigger_node=trigger_node,
                snapshot=json.dumps(snapshot, ensure_ascii=False),
                word_count=count_words((snapshot.get("paper") or {}).get("content") or ""),
                chapter_count=len(chapters),
                reference_count=len(snapshot.get("references") or []),
                created_by=created_by,
            )
            session.add(version)
            await session.commit()
            await session.refresh(version)
            return version

    async def auto_version(
        self,
        paper_id: int,
        description: str,
        trigger_node: str,
        workflow_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[PaperVersion]:
        """工作流关键节点的自动版本（失败只记日志，不影响主流程）"""
        try:
            return await self.create_snapshot(
                paper_id,
                VersionType.AUTO.value,
                description=description,
                trigger_node=trigger_node,
                workflow_state=workflow_state,
            )
        except Exception as exc:  # pragma: no cover - 防御性处理
            logger.warning("关键节点自动版本创建失败（不影响主流程）：%s", exc)
            return None

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    async def list_versions(self, db: AsyncSession, paper_id: int) -> List[PaperVersion]:
        """版本列表（版本号倒序）"""
        result = await db.execute(
            select(PaperVersion)
            .where(PaperVersion.paper_id == paper_id)
            .order_by(PaperVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_version(
        self,
        db: AsyncSession,
        paper_id: int,
        version_id: int,
    ) -> Optional[PaperVersion]:
        """获取指定版本"""
        result = await db.execute(
            select(PaperVersion).where(
                PaperVersion.id == version_id,
                PaperVersion.paper_id == paper_id,
            )
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # 回滚
    # ------------------------------------------------------------------
    async def rollback(
        self,
        db: AsyncSession,
        paper_id: int,
        version_id: int,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """回滚到指定版本：备份当前内容 → 恢复目标版本 → 生成 rollback 新版本"""
        target = await self.get_version(db, paper_id, version_id)
        if target is None:
            raise LookupError(f"版本 ID {version_id} 不存在")

        snapshot = self._load_snapshot(target)

        # 1) 回滚前自动备份当前状态
        backup = await self.create_snapshot(
            paper_id,
            VersionType.BACKUP.value,
            description=f"回滚到 v{target.version_number} 前的自动备份",
            trigger_node="rollback",
            created_by=created_by,
        )
        if backup is None:
            raise LookupError(f"论文 ID {paper_id} 不存在")

        # 2) 恢复目标版本内容
        restored = await self._restore_snapshot(db, paper_id, snapshot)

        # 3) 生成回滚版本（不删除任何历史版本，保证可追溯、可再次回滚）
        rollback_version = await self.create_snapshot(
            paper_id,
            VersionType.ROLLBACK.value,
            description=f"回滚到 v{target.version_number}",
            trigger_node="rollback",
            workflow_state={
                "last_node": "rollback",
                "note": f"由 v{target.version_number} 恢复，回滚前内容见 v{backup.version_number}",
            },
            created_by=created_by,
        )

        return {
            "paper_id": paper_id,
            "target_version_number": target.version_number,
            "backup_version_number": backup.version_number,
            "rollback_version_number": rollback_version.version_number if rollback_version else 0,
            "restored": restored,
        }

    # ------------------------------------------------------------------
    # 差异对比
    # ------------------------------------------------------------------
    async def diff(
        self,
        db: AsyncSession,
        paper_id: int,
        left_version_id: int,
        right_version_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """结构化差异对比：left 版本 vs（当前内容 或 另一个历史版本）"""
        left_version = await self.get_version(db, paper_id, left_version_id)
        if left_version is None:
            raise LookupError(f"版本 ID {left_version_id} 不存在")
        left_snapshot = self._load_snapshot(left_version)

        if right_version_id:
            right_version = await self.get_version(db, paper_id, right_version_id)
            if right_version is None:
                raise LookupError(f"版本 ID {right_version_id} 不存在")
            right_snapshot = self._load_snapshot(right_version)
            right_side = {
                "version_number": right_version.version_number,
                "label": f"v{right_version.version_number}",
                "version_type": right_version.version_type,
                "description": right_version.description,
                "created_at": right_version.created_at,
            }
        else:
            right_snapshot = await self.build_snapshot(db, paper_id)
            if right_snapshot is None:
                raise LookupError(f"论文 ID {paper_id} 不存在")
            right_side = {
                "version_number": 0,
                "label": "当前内容",
                "version_type": None,
                "description": None,
                "created_at": None,
            }

        left_paper = left_snapshot.get("paper") or {}
        right_paper = right_snapshot.get("paper") or {}

        dimensions = [
            self._text_dimension("title", "论文标题", left_paper.get("title"), right_paper.get("title")),
            self._text_dimension("abstract", "摘要", left_paper.get("abstract"), right_paper.get("abstract")),
            self._text_dimension("keywords", "关键词", left_paper.get("keywords"), right_paper.get("keywords")),
            self._structure_dimension(
                "outline",
                "大纲",
                self._parse_outline_sections(left_paper.get("outline")),
                self._parse_outline_sections(right_paper.get("outline")),
                content_key="points",
            ),
            self._structure_dimension(
                "chapters",
                "章节",
                left_snapshot.get("chapters") or [],
                right_snapshot.get("chapters") or [],
                content_key="content",
            ),
            self._structure_dimension(
                "references",
                "参考文献",
                left_snapshot.get("references") or [],
                right_snapshot.get("references") or [],
                content_key="cite",
            ),
        ]

        return {
            "paper_id": paper_id,
            "left": {
                "version_number": left_version.version_number,
                "label": f"v{left_version.version_number}",
                "version_type": left_version.version_type,
                "description": left_version.description,
                "created_at": left_version.created_at,
            },
            "right": right_side,
            "summary": self._count_summary(dimensions),
            "dimensions": dimensions,
        }

    # ------------------------------------------------------------------
    # 内部方法 - 差异构建
    # ------------------------------------------------------------------
    def _text_dimension(
        self,
        key: str,
        label: str,
        old_value: Optional[str],
        new_value: Optional[str],
    ) -> Dict[str, Any]:
        """文本类维度（标题 / 摘要 / 关键词）"""
        old_value = old_value or ""
        new_value = new_value or ""
        status = self._text_status(old_value, new_value)
        segments: List[Dict[str, str]] = []
        if status == "modified":
            segments, _ = self._inline_diff(old_value, new_value)
        return {
            "key": key,
            "label": label,
            "status": status,
            "old_value": old_value,
            "new_value": new_value,
            "segments": segments,
            "items": [],
        }

    def _structure_dimension(
        self,
        key: str,
        label: str,
        old_items: List[Dict[str, Any]],
        new_items: List[Dict[str, Any]],
        content_key: str,
    ) -> Dict[str, Any]:
        """结构类维度（大纲 / 章节 / 参考文献），按名称逐项对比"""
        old_map = {self._item_title(item): item for item in old_items}
        new_map = {self._item_title(item): item for item in new_items}

        # 保持原有顺序：先旧有新再新增
        ordered = list(old_map.keys()) + [t for t in new_map if t not in old_map]

        items: List[Dict[str, Any]] = []
        for title in ordered:
            old_item = old_map.get(title)
            new_item = new_map.get(title)
            old_text = self._item_text(old_item, content_key) if old_item else ""
            new_text = self._item_text(new_item, content_key) if new_item else ""

            if old_item and new_item:
                if old_text == new_text:
                    status, segments, truncated = "unchanged", [], False
                else:
                    status = "modified"
                    segments, truncated = self._inline_diff(old_text, new_text)
            elif new_item:
                status = "added"
                segments, truncated = self._inline_diff("", new_text)
            else:
                status = "removed"
                segments, truncated = self._inline_diff(old_text, "")

            items.append({
                "key": title,
                "title": title,
                "status": status,
                "old_title": self._item_title(old_item) if old_item else None,
                "word_count_old": self._item_word_count(old_item),
                "word_count_new": self._item_word_count(new_item),
                "segments": segments,
                "truncated": truncated,
            })

        return {
            "key": key,
            "label": label,
            "status": self._items_status(items),
            "segments": [],
            "items": items,
        }

    @staticmethod
    def _text_status(old_value: str, new_value: str) -> str:
        """文本变化状态"""
        if old_value == new_value:
            return "unchanged"
        if not old_value and new_value:
            return "added"
        if old_value and not new_value:
            return "removed"
        return "modified"

    @staticmethod
    def _items_status(items: List[Dict[str, Any]]) -> str:
        """由子项状态归并出维度状态"""
        statuses = {item["status"] for item in items}
        if not statuses or statuses == {"unchanged"}:
            return "unchanged"
        for candidate in ("modified", "added", "removed"):
            if candidate in statuses:
                return candidate
        return "modified"

    def _inline_diff(
        self,
        old_text: str,
        new_text: str,
        max_segments: int = MAX_SEGMENTS,
    ) -> Tuple[List[Dict[str, str]], bool]:
        """生成行内差异片段：短文本按字符对比，长文本按行对比"""
        old_text = old_text or ""
        new_text = new_text or ""
        if len(old_text) + len(new_text) > MAX_INLINE_CHARS:
            old_seq: List[str] = old_text.splitlines(keepends=True)
            new_seq: List[str] = new_text.splitlines(keepends=True)
        else:
            old_seq = list(old_text)
            new_seq = list(new_text)

        matcher = difflib.SequenceMatcher(None, old_seq, new_seq, autojunk=False)
        segments: List[Dict[str, str]] = []
        truncated = False

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                segments.append({"type": "equal", "text": "".join(new_seq[j1:j2])})
            elif tag == "delete":
                segments.append({"type": "delete", "text": "".join(old_seq[i1:i2])})
            elif tag == "insert":
                segments.append({"type": "insert", "text": "".join(new_seq[j1:j2])})
            else:  # replace：先删后增，前端才能高亮出「变化前后」
                segments.append({"type": "delete", "text": "".join(old_seq[i1:i2])})
                segments.append({"type": "insert", "text": "".join(new_seq[j1:j2])})

            if len(segments) >= max_segments:
                truncated = True
                break

        return segments, truncated

    @staticmethod
    def _item_title(item: Optional[Dict[str, Any]]) -> str:
        """差异项的名称（章节名 / 文献标题 / 大纲小节名）"""
        if not item:
            return ""
        return (item.get("title") or "").strip() or "未命名"

    @staticmethod
    def _item_text(item: Optional[Dict[str, Any]], content_key: str) -> str:
        """取出用于对比的文本内容"""
        if not item:
            return ""
        if content_key == "points":
            points = item.get("points") or []
            if isinstance(points, str):
                return points
            return "\n".join(f"• {point}" for point in points)
        if content_key == "cite":
            parts = [item.get("authors") or "", item.get("journal") or "", str(item.get("year") or "")]
            return " · ".join(part for part in parts if part)
        return item.get("content") or ""

    @staticmethod
    def _item_word_count(item: Optional[Dict[str, Any]]) -> Optional[int]:
        """差异项字数：章节取内容字数，大纲取规划字数"""
        if not item:
            return None
        if item.get("content") is not None:
            return item.get("word_count") or count_words(item.get("content") or "")
        if item.get("word_count") is not None:
            return item.get("word_count")
        return None

    @staticmethod
    def _count_summary(dimensions: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计新增 / 删除 / 修改 / 未变化数量"""
        summary = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}
        for dimension in dimensions:
            items = dimension.get("items") or []
            if items:
                for item in items:
                    summary[item["status"]] = summary.get(item["status"], 0) + 1
            else:
                status = dimension.get("status", "unchanged")
                summary[status] = summary.get(status, 0) + 1
        return summary

    @staticmethod
    def _parse_outline_sections(raw: Optional[str]) -> List[Dict[str, Any]]:
        """容错解析大纲 JSON，返回 sections 列表"""
        if not raw:
            return []
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("sections") or []
        return []

    @staticmethod
    def _load_snapshot(version: PaperVersion) -> Dict[str, Any]:
        """解析版本快照"""
        try:
            return json.loads(version.snapshot or "{}")
        except (ValueError, TypeError):
            return {}

    # ------------------------------------------------------------------
    # 内部方法 - 恢复
    # ------------------------------------------------------------------
    async def _restore_snapshot(
        self,
        db: AsyncSession,
        paper_id: int,
        snapshot: Dict[str, Any],
    ) -> Dict[str, int]:
        """把快照内容恢复为论文当前内容"""
        paper = (
            await db.execute(select(Paper).where(Paper.id == paper_id))
        ).scalar_one_or_none()
        if paper is None:
            raise LookupError(f"论文 ID {paper_id} 不存在")

        paper_data = snapshot.get("paper") or {}

        # 1) 论文主体字段
        paper.title = paper_data.get("title") or paper.title
        paper.topic = paper_data.get("topic")
        paper.keywords = paper_data.get("keywords")
        paper.abstract = paper_data.get("abstract")
        paper.outline = paper_data.get("outline")
        paper.content = paper_data.get("content")
        paper.paper_type = paper_data.get("paper_type") or paper.paper_type
        paper.word_limit = paper_data.get("word_limit") or paper.word_limit
        if paper_data.get("status"):
            try:
                paper.status = PaperStatus(paper_data["status"])
            except ValueError:
                pass
        paper.updated_at = datetime.utcnow()

        # 2) 章节：整体重建（全量快照下重建比逐条 diff 更可靠）
        chapters = snapshot.get("chapters") or []
        await db.execute(delete(Chapter).where(Chapter.paper_id == paper_id))
        for index, item in enumerate(chapters):
            content = item.get("content") or ""
            db.add(Chapter(
                paper_id=paper_id,
                title=item.get("title") or f"第 {index + 1} 章",
                content=content,
                summary=item.get("summary") or "",
                order_index=item.get("order_index", index),
                word_count=item.get("word_count") or count_words(content),
            ))

        # 3) 文献：先解除当前关联，再按快照恢复（快照中已被删除的文献会重新入库）
        await db.execute(update(Reference).where(Reference.paper_id == paper_id).values(paper_id=None))

        restored_references = 0
        for item in snapshot.get("references") or []:
            reference: Optional[Reference] = None
            if item.get("id"):
                reference = (
                    await db.execute(
                        select(Reference).where(Reference.id == int(item["id"]))
                    )
                ).scalar_one_or_none()
            if reference is None and item.get("title"):
                reference = (
                    await db.execute(
                        select(Reference).where(Reference.title == item["title"]).limit(1)
                    )
                ).scalar_one_or_none()
            if reference is None:
                reference = Reference(title=item.get("title") or "未命名文献")
                db.add(reference)

            reference.title = item.get("title") or reference.title
            reference.authors = item.get("authors") or reference.authors
            reference.journal = item.get("journal") or reference.journal
            reference.year = item.get("year") or reference.year
            reference.volume = item.get("volume") or reference.volume
            reference.issue = item.get("issue") or reference.issue
            reference.pages = item.get("pages") or reference.pages
            reference.doi = item.get("doi") or reference.doi
            reference.url = item.get("url") or reference.url
            reference.abstract = item.get("abstract") or reference.abstract
            reference.paper_id = paper_id
            restored_references += 1

        await db.commit()

        return {
            "chapter_count": len(chapters),
            "reference_count": restored_references,
            "word_count": count_words(paper.content or ""),
        }


# 全局服务实例
version_service = VersionService()