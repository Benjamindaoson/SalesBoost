"""
Data Flywheel API

Endpoints for extracting winning patterns, ranking talk tracks,
and generating playbook entries from deal outcomes.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...services.data_flywheel import DataFlywheel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["flywheel"])


@router.get("/flywheel/summary")
async def flywheel_summary(db: AsyncSession = Depends(get_db_session)):
    return await DataFlywheel.get_flywheel_summary(db)


@router.get("/flywheel/winning-patterns")
async def winning_patterns(db: AsyncSession = Depends(get_db_session)):
    return await DataFlywheel.extract_winning_patterns(db)


@router.get("/flywheel/losing-patterns")
async def losing_patterns(db: AsyncSession = Depends(get_db_session)):
    return await DataFlywheel.extract_losing_patterns(db)


@router.get("/flywheel/rankings")
async def talk_track_rankings(db: AsyncSession = Depends(get_db_session)):
    return await DataFlywheel.rank_talk_tracks(db)


@router.get("/flywheel/playbook")
async def playbook_entries(db: AsyncSession = Depends(get_db_session)):
    return await DataFlywheel.generate_playbook_entries(db)
