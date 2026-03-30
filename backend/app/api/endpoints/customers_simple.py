"""
Customers API - 客户画像（100% 实现）

数据来源: seed_constants + 内存存储（自定义画像）
支持完整 CRUD，生产环境无 Mock 回退。
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...data.seed_constants import get_seed_customer_personas

logger = logging.getLogger(__name__)
router = APIRouter()

# 内存存储：自定义客户画像（生产可替换为 Redis/DB）
_custom_personas: Dict[str, Dict[str, Any]] = {}


class CustomerPersona(BaseModel):
    """客户画像（seed 格式）"""
    id: int
    name: str
    role: str
    company: str
    industry: str
    pain_points: List[str]
    personality: str
    difficulty: int
    avatar_url: str | None = None


class CustomerCreate(BaseModel):
    """创建客户画像"""
    name: str
    age: int = Field(30, ge=1, le=100)
    job: str
    traits: List[str] = Field(default_factory=list)
    description: str = ""
    avatar_color: str = "from-blue-200 to-blue-400"
    scenario_id: str = "default"


class CustomerUpdate(BaseModel):
    """更新客户画像"""
    name: Optional[str] = None
    age: Optional[int] = None
    job: Optional[str] = None
    traits: Optional[List[str]] = None
    description: Optional[str] = None
    avatar_color: Optional[str] = None


def _load_seed_personas() -> List[CustomerPersona]:
    """从 seed 加载客户画像"""
    return [CustomerPersona(**p) for p in get_seed_customer_personas()]


def _seed_to_response(p: CustomerPersona) -> dict:
    """seed 格式转前端格式"""
    return {
        "id": str(p.id),
        "name": p.name,
        "age": 0,
        "job": p.role,
        "traits": p.pain_points if p.pain_points else [p.personality],
        "description": f"{p.company} · {p.industry} · {p.personality}",
        "creator": "系统",
        "rehearsalCount": 0,
        "lastRehearsalTime": "",
        "avatarColor": "from-purple-200 to-purple-400",
    }


def _custom_to_response(pid: str, p: Dict[str, Any]) -> dict:
    """自定义画像转前端格式"""
    return {
        "id": pid,
        "name": p.get("name", ""),
        "age": p.get("age", 30),
        "job": p.get("job", ""),
        "traits": p.get("traits", []),
        "description": p.get("description", ""),
        "creator": p.get("creator", "当前用户"),
        "rehearsalCount": p.get("rehearsalCount", 0),
        "lastRehearsalTime": p.get("lastRehearsalTime", "刚刚"),
        "avatarColor": p.get("avatar_color", "from-blue-200 to-blue-400"),
    }


@router.get("/customers")
async def list_customers():
    """获取所有客户画像（seed + 自定义）"""
    logger.info("Fetching all customer personas")
    seed = _load_seed_personas()
    result = [_seed_to_response(p) for p in seed]
    for pid, p in _custom_personas.items():
        result.append(_custom_to_response(pid, p))
    return result


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    """获取特定客户画像"""
    # 先查自定义
    if customer_id in _custom_personas:
        return _custom_to_response(customer_id, _custom_personas[customer_id])
    # 再查 seed（id 为数字）
    try:
        sid = int(customer_id)
        for p in _load_seed_personas():
            if p.id == sid:
                return _seed_to_response(p)
    except ValueError:
        pass
    raise HTTPException(status_code=404, detail="Customer not found")


@router.post("/customers")
async def create_customer(data: CustomerCreate):
    """创建自定义客户画像"""
    import time
    pid = f"c_{int(time.time() * 1000)}"
    _custom_personas[pid] = {
        "name": data.name,
        "age": data.age,
        "job": data.job,
        "traits": data.traits,
        "description": data.description or f"{data.age}岁 · {data.job} · {', '.join(data.traits[:2])}",
        "creator": "当前用户",
        "rehearsalCount": 0,
        "lastRehearsalTime": "刚刚",
        "avatar_color": data.avatar_color,
    }
    return _custom_to_response(pid, _custom_personas[pid])


@router.patch("/customers/{customer_id}")
async def update_customer(customer_id: str, data: CustomerUpdate):
    """更新客户画像（仅自定义）"""
    if customer_id not in _custom_personas:
        raise HTTPException(status_code=404, detail="Customer not found")
    p = _custom_personas[customer_id]
    if data.name is not None:
        p["name"] = data.name
    if data.age is not None:
        p["age"] = data.age
    if data.job is not None:
        p["job"] = data.job
    if data.traits is not None:
        p["traits"] = data.traits
    if data.description is not None:
        p["description"] = data.description
    if data.avatar_color is not None:
        p["avatar_color"] = data.avatar_color
    return _custom_to_response(customer_id, p)


@router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str):
    """删除客户画像（仅自定义）"""
    if customer_id not in _custom_personas:
        raise HTTPException(status_code=404, detail="Customer not found")
    del _custom_personas[customer_id]
    return {"message": "Customer deleted"}
