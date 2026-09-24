"""文献接口"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.paper import (
    ReferenceCreate,
    ReferenceResponse,
    ReferenceSearchRequest,
    ReferenceSearchResponse,
    ReferenceUpdate,
)
from app.services.reference_service import reference_service

router = APIRouter()


@router.get("/status")
async def vector_store_status():
    """向量库 / 模型配置状态"""
    return reference_service.status()


@router.post("/search", response_model=ReferenceSearchResponse)
async def search_references(payload: ReferenceSearchRequest):
    """RAG 语义检索文献并生成标准引用"""
    result = await reference_service.search(
        query=payload.query,
        top_k=payload.top_k,
        format_style=payload.format,
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/", response_model=List[ReferenceResponse])
async def list_references(
    paper_id: Optional[int] = None,
    keyword: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """获取文献列表"""
    return await reference_service.list(
        db,
        paper_id=paper_id,
        skip=skip,
        limit=limit,
        keyword=keyword,
    )


@router.post("/", response_model=ReferenceResponse, status_code=status.HTTP_201_CREATED)
async def create_reference(
    reference_data: ReferenceCreate,
    db: AsyncSession = Depends(get_db),
):
    """新增文献（自动写入向量库）"""
    return await reference_service.create(db, reference_data)


@router.post("/bulk", response_model=List[ReferenceResponse], status_code=status.HTTP_201_CREATED)
async def bulk_create_references(
    references_data: List[ReferenceCreate],
    db: AsyncSession = Depends(get_db),
):
    """批量导入文献"""
    if not references_data:
        raise HTTPException(status_code=400, detail="文献列表不能为空")
    return await reference_service.bulk_create(db, references_data)


@router.post("/rebuild-vector-store")
async def rebuild_vector_store(db: AsyncSession = Depends(get_db)):
    """重建向量库（全量重新向量化）"""
    try:
        count = await reference_service.rebuild_vector_store(db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"重建向量库失败：{exc}")
    return {"message": "向量库重建完成", "count": count}


@router.get("/{reference_id}", response_model=ReferenceResponse)
async def get_reference(
    reference_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取文献详情"""
    reference = await reference_service.get(db, reference_id)
    if reference is None:
        raise HTTPException(status_code=404, detail="文献不存在")
    return reference


@router.put("/{reference_id}", response_model=ReferenceResponse)
async def update_reference(
    reference_id: int,
    reference_data: ReferenceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新文献"""
    reference = await reference_service.update(db, reference_id, reference_data)
    if reference is None:
        raise HTTPException(status_code=404, detail="文献不存在")
    return reference


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference(
    reference_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除文献"""
    deleted = await reference_service.delete(db, reference_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="文献不存在")