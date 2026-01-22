from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_admin
from app.models.saas_models import User

router = APIRouter()

class Permission(BaseModel):
    code: str
    name: str
    description: Optional[str] = None

class RoleSchema(BaseModel):
    id: str
    name: str
    description: str
    permissions: List[str]
    is_system: bool = False

# Mock Role Data (In production this would be in DB)
ROLES_DB = [
    {
        "id": "admin",
        "name": "超级管理员",
        "description": "拥有系统所有权限",
        "permissions": ["all"],
        "is_system": True
    },
    {
        "id": "operator",
        "name": "运营管理员",
        "description": "负责内容管理和用户查看",
        "permissions": ["content:read", "content:write", "user:read"],
        "is_system": False
    },
    {
        "id": "content_admin",
        "name": "内容管理员",
        "description": "仅负责知识库和课程维护",
        "permissions": ["content:read", "content:write"],
        "is_system": False
    },
    {
        "id": "student",
        "name": "学员",
        "description": "普通学员用户",
        "permissions": ["practice:read", "practice:write"],
        "is_system": True
    }
]

@router.get("/", response_model=List[RoleSchema])
async def list_roles(admin: User = Depends(get_current_admin)):
    return ROLES_DB

@router.put("/{role_id}", response_model=RoleSchema)
async def update_role_permissions(
    role_id: str, 
    permissions: List[str],
    admin: User = Depends(get_current_admin)
):
    # Mock update
    for role in ROLES_DB:
        if role["id"] == role_id:
            if role["is_system"]:
                 raise HTTPException(status_code=400, detail="Cannot modify system roles")
            role["permissions"] = permissions
            return role
    raise HTTPException(status_code=404, detail="Role not found")
