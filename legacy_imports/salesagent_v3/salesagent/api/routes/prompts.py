"""Prompts Registry API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from salesagent.dependencies import get_db
from salesagent.models.db_models import PromptTemplate
from salesagent.models.schemas import PromptTemplateCreate, PromptTemplateResponse, PromptTemplateUpdate
from salesagent.auth.dependencies import get_current_user
from salesagent.auth.permissions import require_admin

router = APIRouter()


@router.get("", response_model=list[PromptTemplateResponse])
async def list_prompts(
    name: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[PromptTemplateResponse]:
    q = select(PromptTemplate).order_by(PromptTemplate.created_at.desc())
    if name:
        q = q.where(PromptTemplate.name == name)
    if status:
        q = q.where(PromptTemplate.status == status)
    result = await db.execute(q)
    return [PromptTemplateResponse.model_validate(p) for p in result.scalars().all()]


@router.post("", response_model=PromptTemplateResponse)
async def create_prompt(
    body: PromptTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),  # Admin only
) -> PromptTemplateResponse:
    # Find max version for this name
    from sqlalchemy import func
    result = await db.execute(
        select(func.max(PromptTemplate.version)).where(PromptTemplate.name == body.name)
    )
    max_version = result.scalar() or 0

    prompt = PromptTemplate(
        name=body.name,
        version=max_version + 1,
        template=body.template,
        variables=body.variables,
        description=body.description,
    )
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return PromptTemplateResponse.model_validate(prompt)


@router.patch("/{prompt_id}", response_model=PromptTemplateResponse)
async def update_prompt(
    prompt_id: str,
    body: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db),
) -> PromptTemplateResponse:
    result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if body.template is not None:
        prompt.template = body.template
    if body.variables is not None:
        prompt.variables = body.variables
    if body.status is not None:
        prompt.status = body.status
    if body.traffic_weight is not None:
        prompt.traffic_weight = body.traffic_weight

    await db.commit()
    await db.refresh(prompt)
    return PromptTemplateResponse.model_validate(prompt)


@router.post("/{prompt_id}/run-regression")
async def run_regression(prompt_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    from salesagent.prompt_registry.regression import PromptRegressionRunner
    runner = PromptRegressionRunner(db=db)
    return await runner.run(new_prompt_id=prompt_id)


@router.get("/{name}/versions", response_model=list[dict])
async def get_prompt_versions(name: str) -> list[dict]:
    """Get all versions of a specific prompt."""
    from salesagent.prompt_registry.loader import PromptLoader
    return await PromptLoader.get_prompt_versions(name)


@router.post("/{name}/rollback")
async def rollback_prompt(name: str, target_version: int) -> dict:
    """
    Rollback a prompt to a specific version.

    This will:
    1. Archive all other versions
    2. Activate the target version with 100% traffic
    3. Return the activated prompt details
    """
    from salesagent.prompt_registry.loader import PromptLoader
    try:
        result = await PromptLoader.rollback_prompt(name, target_version)
        return {
            "status": "success",
            "message": f"Prompt '{name}' rolled back to version {target_version}",
            "prompt": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
