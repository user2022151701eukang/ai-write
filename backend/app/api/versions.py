"""版本管理接口 - 全量快照版本、回滚、差异对比"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_optional_user
from app.database import get_db
from app.models.user import User
from app.schemas.version import (
    RollbackResponse,
    VersionCreateRequest,
    VersionDetail,
    VersionDiffResponse,
    VersionSummary,
)
from app.services.version_service import version_service

router = APIRouter()


def _to_summary(version) -> VersionSummary:
    """版本对象 → 列表条目"""
    return VersionSummary.model_validate(version)


def _to_detail(version) -> VersionDetail:
    """版本对象 → 详情（含快照）"""
    import json

    try:
        snapshot = json.loads(version.snapshot or "{}")
    except (ValueError, TypeError):
        snapshot = {}
    return VersionDetail(**VersionSummary.model_validate(version).model_dump(), snapshot=snapshot)


@router.get("", response_model=List[VersionSummary])
async def list_versions(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取论文的全部历史版本（版本号倒序）"""
    versions = await version_service.list_versions(db, paper_id)
    return [_to_summary(version) for version in versions]


@router.post("", response_model=VersionSummary, status_code=status.HTTP_201_CREATED)
async def create_version(
    paper_id: int,
    payload: Optional[VersionCreateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """手动保存一个版本（论文级全量快照）"""
    version = await version_service.create_snapshot(
        paper_id,
        version_type="manual",
        description=(payload.description if payload else "") or "手动保存",
        created_by=current_user.id if current_user else None,
    )
    if version is None:
        raise HTTPException(status_code=404, detail=f"论文 ID {paper_id} 不存在")
    return _to_summary(version)


@router.get("/{version_id}", response_model=VersionDetail)
async def get_version(
    paper_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取版本详情（含全量快照）"""
    version = await version_service.get_version(db, paper_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail=f"版本 ID {version_id} 不存在")
    return _to_detail(version)


@router.post("/{version_id}/rollback", response_model=RollbackResponse)
async def rollback_version(
    paper_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """回滚到指定版本

    历史版本不会被删除：系统会先把当前内容备份为新版本，再恢复目标版本内容，
    最后生成一个类型为 rollback 的新版本，全过程可追溯。
    """
    try:
        result = await version_service.rollback(
            db,
            paper_id,
            version_id,
            created_by=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"回滚失败：{exc}")

    return RollbackResponse(
        message=f"已回滚到 v{result['target_version_number']}，并生成新版本 v{result['rollback_version_number']}",
        **result,
    )


@router.get("/{version_id}/diff", response_model=VersionDiffResponse)
async def diff_version(
    paper_id: int,
    version_id: int,
    target_version_id: Optional[int] = Query(
        None, description="对比目标版本 ID，不传表示与该版本的当前内容对比"
    ),
    db: AsyncSession = Depends(get_db),
):
    """按结构维度对比两个版本（标题 / 摘要 / 关键词 / 大纲 / 章节 / 参考文献）"""
    try:
        result = await version_service.diff(
            db,
            paper_id,
            left_version_id=version_id,
            right_version_id=target_version_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"版本对比失败：{exc}")

    return result