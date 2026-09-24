"""章节接口"""

from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_llm_config
from app.database import get_db
from app.schemas.chapter import (
    ChapterCreate,
    ChapterGenerateRequest,
    ChapterPolishRequest,
    ChapterResponse,
    ChapterUpdate,
)
from app.services.chapter_service import chapter_service
from app.services.version_service import version_service

router = APIRouter()


@router.get("/paper/{paper_id}", response_model=List[ChapterResponse])
async def list_chapters(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取论文下的所有章节"""
    return await chapter_service.list_by_paper(db, paper_id)


@router.post("/", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
async def create_chapter(
    chapter_data: ChapterCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建章节"""
    return await chapter_service.create(db, chapter_data)


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取章节详情"""
    chapter = await chapter_service.get(db, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="章节不存在")
    return chapter


@router.put("/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: int,
    chapter_data: ChapterUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新章节"""
    chapter = await chapter_service.update(db, chapter_id, chapter_data)
    if chapter is None:
        raise HTTPException(status_code=404, detail="章节不存在")
    return chapter


@router.delete("/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chapter(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除章节"""
    deleted = await chapter_service.delete(db, chapter_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="章节不存在")


@router.post("/{chapter_id}/generate", response_model=ChapterResponse, dependencies=[Depends(require_llm_config)])
async def generate_chapter_content(
    chapter_id: int,
    options: Optional[ChapterGenerateRequest] = Body(None),
    db: AsyncSession = Depends(get_db),
):
    """使用写作 Agent 生成章节内容"""
    try:
        chapter = await chapter_service.generate_content(
            db,
            chapter_id,
            options.model_dump(exclude_none=True) if options else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"章节生成失败：{exc}")

    if chapter is None:
        raise HTTPException(status_code=404, detail="章节不存在")

    # 关键节点：章节撰写完成后自动版本
    await version_service.auto_version(
        chapter.paper_id,
        f"章节「{chapter.title}」撰写完成",
        trigger_node="section",
        workflow_state={"last_node": "write_sections", "chapter_id": chapter.id},
    )
    return chapter


@router.post("/{chapter_id}/polish", response_model=ChapterResponse, dependencies=[Depends(require_llm_config)])
async def polish_chapter_content(
    chapter_id: int,
    options: Optional[ChapterPolishRequest] = Body(None),
    db: AsyncSession = Depends(get_db),
):
    """使用润色 Agent 优化章节内容"""
    focus = options.focus if options else "all"

    try:
        chapter = await chapter_service.polish_content(db, chapter_id, focus or "all")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"章节润色失败：{exc}")

    if chapter is None:
        raise HTTPException(status_code=404, detail="章节不存在")

    # 关键节点：章节润色完成后自动版本
    await version_service.auto_version(
        chapter.paper_id,
        f"章节「{chapter.title}」润色完成（{focus or 'all'}）",
        trigger_node="polish",
        workflow_state={"last_node": "polish_paper", "chapter_id": chapter.id},
    )
    return chapter