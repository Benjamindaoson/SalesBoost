"""
Admin API - Knowledge Governance
"""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_schemas import UserSchema as User
from api.deps import get_current_user
from core.database import get_db_session
from models.knowledge_models import KnowledgeAsset, KnowledgeVersion

# 如果使用了 Qdrant，这里需要导入 KnowledgeService
from app.agents.study.knowledge_service_qdrant import HAS_QDRANT, QdrantKnowledgeService

router = APIRouter()

# 权限依赖
async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.username != "admin": 
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user

# Models
class AssetCreate(BaseModel):
    title: str
    source_type: str
    content: str
    commit_message: Optional[str] = "Initial commit"

class AssetUpdate(BaseModel):
    title: Optional[str] = None
    content: str
    commit_message: Optional[str] = "Update"

class VersionResponse(BaseModel):
    id: str
    version_number: int
    content: str
    content_hash: str
    commit_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AssetResponse(BaseModel):
    id: str
    title: str
    source_type: str
    active_version_id: Optional[str]
    active_version: Optional[VersionResponse] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Helper to sync with Vector DB
async def sync_to_vector_db(asset: KnowledgeAsset, version: KnowledgeVersion):
    """
    同步到向量数据库
    Metadata: asset_id, version_id, version_number, source_type
    """
    if not HAS_QDRANT:
        return
        
    try:
        service = QdrantKnowledgeService()
        
        # 删除旧版本的向量 (可选：保留历史版本用于特定查询，这里我们只保留 active 版本以节省空间？
        # 或者 PRD 要求 RAG 查询必须标注使用的 version_id，这意味着我们需要保留历史版本吗？
        # PRD B2: "RAG 查询 必须标注使用的 version_id" -> 这通常指返回结果中标注。
        # 如果要支持回滚，向量库最好也支持。为了简化 MVP，我们每次 update 都新增向量，metadata 带 version。
        # 实际检索时，如果未指定 version，则默认过滤 active_version_id。
        
        # Add new version
        await service.add_document_with_processing(
            content=version.content.encode('utf-8'),
            filename=f"{asset.title}_v{version.version_number}.txt",
            content_type="text/plain",
            meta={
                "asset_id": asset.id,
                "version_id": version.id,
                "version_number": version.version_number,
                "source_type": asset.source_type,
                "title": asset.title,
                "is_active": True # 标记为活跃
            },
            doc_type="knowledge"
        )
        
        # 标记旧版本为非活跃 (Qdrant update payload)
        # 暂时跳过复杂的 payload 更新，依靠 RAG 检索时的 active_version_id 过滤
        
    except Exception as e:
        print(f"Vector DB sync failed: {e}")

# Routes
@router.post("", response_model=AssetResponse)
async def create_asset(
    asset_in: AssetCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """创建知识资产"""
    # 1. Create Asset
    asset_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    
    db_asset = KnowledgeAsset(
        id=asset_id,
        title=asset_in.title,
        source_type=asset_in.source_type,
        active_version_id=version_id,
    )
    
    # 2. Create Initial Version
    content_hash = KnowledgeVersion.calculate_hash(asset_in.content)
    db_version = KnowledgeVersion(
        id=version_id,
        asset_id=asset_id,
        version_number=1,
        content=asset_in.content,
        content_hash=content_hash,
        commit_message=asset_in.commit_message,
        created_by=admin.username
    )
    
    db.add(db_asset)
    db.add(db_version)
    await db.commit()
    
    # 3. Sync to Vector DB
    await sync_to_vector_db(db_asset, db_version)
    
    await db.refresh(db_asset)
    # Manually attach version for response
    # db_asset.active_version = db_version 
    # (SQLAlchemy relationship might not populate immediately on same session without refresh with eager load)
    
    return AssetResponse(
        id=db_asset.id,
        title=db_asset.title,
        source_type=db_asset.source_type,
        active_version_id=db_asset.active_version_id,
        created_at=db_asset.created_at,
        updated_at=db_asset.updated_at,
        active_version=VersionResponse.from_orm(db_version)
    )

@router.get("", response_model=List[AssetResponse])
async def list_assets(
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """列出知识资产"""
    # Eager load versions is too heavy, maybe just join active version?
    # For MVP list, we might not need content.
    result = await db.execute(
        select(KnowledgeAsset).order_by(desc(KnowledgeAsset.updated_at))
    )
    assets = result.scalars().all()
    
    # TODO: Optimize N+1 query for active version
    resp = []
    for asset in assets:
        active_v = None
        if asset.active_version_id:
             # Find in loaded versions if lazy='selectin'
             for v in asset.versions:
                 if v.id == asset.active_version_id:
                     active_v = v
                     break
        
        resp.append(AssetResponse(
            id=asset.id,
            title=asset.title,
            source_type=asset.source_type,
            active_version_id=asset.active_version_id,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            active_version=VersionResponse.from_orm(active_v) if active_v else None
        ))
    return resp

@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    update_in: AssetUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """更新资产（创建新版本）"""
    result = await db.execute(select(KnowledgeAsset).where(KnowledgeAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Determine next version number
    last_version = 0
    if asset.versions:
        last_version = max(v.version_number for v in asset.versions)
    
    new_version_number = last_version + 1
    new_version_id = str(uuid.uuid4())
    
    # Update Asset Metadata
    if update_in.title:
        asset.title = update_in.title
    asset.active_version_id = new_version_id
    
    # Create New Version
    content_hash = KnowledgeVersion.calculate_hash(update_in.content)
    new_version = KnowledgeVersion(
        id=new_version_id,
        asset_id=asset.id,
        version_number=new_version_number,
        content=update_in.content,
        content_hash=content_hash,
        commit_message=update_in.commit_message,
        created_by=admin.username
    )
    
    db.add(new_version)
    await db.commit()
    
    # Sync
    await sync_to_vector_db(asset, new_version)
    
    await db.refresh(asset)
    return AssetResponse(
        id=asset.id,
        title=asset.title,
        source_type=asset.source_type,
        active_version_id=asset.active_version_id,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        active_version=VersionResponse.from_orm(new_version)
    )

@router.get("/{asset_id}/history", response_model=List[VersionResponse])
async def get_asset_history(
    asset_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """获取版本历史"""
    result = await db.execute(
        select(KnowledgeVersion)
        .where(KnowledgeVersion.asset_id == asset_id)
        .order_by(desc(KnowledgeVersion.version_number))
    )
    return result.scalars().all()

@router.post("/{asset_id}/rollback", response_model=AssetResponse)
async def rollback_version(
    asset_id: str,
    version_id: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """回滚到指定版本"""
    # Check asset
    asset_res = await db.execute(select(KnowledgeAsset).where(KnowledgeAsset.id == asset_id))
    asset = asset_res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    # Check version
    version_res = await db.execute(select(KnowledgeVersion).where(KnowledgeVersion.id == version_id))
    version = version_res.scalar_one_or_none()
    if not version or version.asset_id != asset_id:
        raise HTTPException(status_code=404, detail="Version not found")
        
    # Set active
    asset.active_version_id = version.id
    await db.commit()
    
    # TODO: Notify Vector DB to set this version as active?
    # Or just rely on RAG to fetch `active_version_id` from DB first then filter Qdrant?
    
    await db.refresh(asset)
    return AssetResponse(
        id=asset.id,
        title=asset.title,
        source_type=asset.source_type,
        active_version_id=asset.active_version_id,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        active_version=VersionResponse.from_orm(version)
    )
