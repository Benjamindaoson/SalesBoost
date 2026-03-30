"""
Export API Endpoints

Handles exporting content in multiple formats (JSON, Markdown, PDF).
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json

from app.core.database import get_db_session
from app.models.session import Session as SessionModel
from app.services.export_service import export_service, ExportFormat

router = APIRouter()


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: int,
    format: ExportFormat = Query(ExportFormat.JSON, description="Export format"),
    include_messages: bool = Query(True, description="Include conversation messages"),
    include_evaluation: bool = Query(True, description="Include evaluation data"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Export session data in specified format.

    Args:
        session_id: Session ID to export
        format: Export format (json, markdown, pdf)
        include_messages: Include conversation messages
        include_evaluation: Include evaluation data

    Returns:
        Exported data in specified format
    """
    # Fetch session from database
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Prepare session data
    session_data = {
        "id": session.id,
        "user_id": session.user_id,
        "task_id": session.task_id,
        "status": session.status.value if hasattr(session.status, 'value') else session.status,
        "score": session.score,
        "duration_seconds": session.duration_seconds,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "sales_state": session.sales_state,
        "customer_interest": session.customer_interest,
        "objections_raised": session.objections_raised,
        "objections_resolved": session.objections_resolved,
        "turns_count": session.turns_count,
    }

    # Include messages if requested
    if include_messages and hasattr(session, 'messages'):
        session_data["messages"] = [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in session.messages
        ]

    # Include evaluation if requested
    if include_evaluation and hasattr(session, 'evaluations') and session.evaluations:
        evaluation = session.evaluations[0]  # Get first evaluation
        session_data["evaluation"] = {
            "overall_score": evaluation.overall_score,
            "methodology_score": evaluation.methodology_score,
            "objection_handling_score": evaluation.objection_handling_score,
            "goal_orientation_score": evaluation.goal_orientation_score,
            "empathy_score": evaluation.empathy_score,
            "clarity_score": evaluation.clarity_score,
            "strengths": json.loads(evaluation.strengths) if evaluation.strengths else [],
            "weaknesses": json.loads(evaluation.weaknesses) if evaluation.weaknesses else [],
            "suggestions": json.loads(evaluation.suggestions) if evaluation.suggestions else [],
            "detailed_feedback": evaluation.detailed_feedback,
        }

    # Export data
    exported_data = await export_service.export_session(
        session_data,
        format,
        include_messages,
        include_evaluation,
    )

    # Determine content type and filename
    content_type_map = {
        ExportFormat.JSON: "application/json",
        ExportFormat.MARKDOWN: "text/markdown",
        ExportFormat.PDF: "application/pdf",
    }

    extension_map = {
        ExportFormat.JSON: "json",
        ExportFormat.MARKDOWN: "md",
        ExportFormat.PDF: "pdf",
    }

    content_type = content_type_map.get(format, "application/octet-stream")
    extension = extension_map.get(format, "bin")
    filename = f"session_{session_id}.{extension}"

    return Response(
        content=exported_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.get("/projects/{project_id}/export")
async def export_project(
    project_id: int,
    format: ExportFormat = Query(ExportFormat.JSON, description="Export format"),
    include_sessions: bool = Query(True, description="Include session data"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Export project data in specified format.

    Args:
        project_id: Project ID to export
        format: Export format (json, markdown, pdf)
        include_sessions: Include session data

    Returns:
        Exported data in specified format
    """
    # For now, return a placeholder since Project model might not exist yet
    # In production, fetch from database
    project_data = {
        "id": project_id,
        "name": f"Project {project_id}",
        "description": "Project description",
        "status": "active",
        "created_at": "2024-01-01T00:00:00",
        "tasks_count": 10,
        "completed_tasks": 5,
        "completion_rate": 50.0,
        "total_sessions": 25,
        "avg_score": 75.5,
    }

    if include_sessions:
        # Fetch sessions for this project
        result = await db.execute(
            select(SessionModel).where(SessionModel.task_id == project_id).limit(10)
        )
        sessions = result.scalars().all()
        project_data["sessions"] = [
            {
                "id": s.id,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "score": s.score,
                "status": s.status.value if hasattr(s.status, 'value') else s.status,
            }
            for s in sessions
        ]

    # Export data
    exported_data = await export_service.export_project(
        project_data,
        format,
        include_sessions,
    )

    # Determine content type and filename
    content_type_map = {
        ExportFormat.JSON: "application/json",
        ExportFormat.MARKDOWN: "text/markdown",
        ExportFormat.PDF: "application/pdf",
    }

    extension_map = {
        ExportFormat.JSON: "json",
        ExportFormat.MARKDOWN: "md",
        ExportFormat.PDF: "pdf",
    }

    content_type = content_type_map.get(format, "application/octet-stream")
    extension = extension_map.get(format, "bin")
    filename = f"project_{project_id}.{extension}"

    return Response(
        content=exported_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.get("/analytics/export")
async def export_analytics(
    format: ExportFormat = Query(ExportFormat.JSON, description="Export format"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Export analytics data in specified format.

    Args:
        format: Export format (json, markdown, csv)
        start_date: Start date for analytics
        end_date: End date for analytics

    Returns:
        Exported analytics data
    """
    # Fetch analytics data (placeholder)
    analytics_data = {
        "overview": {
            "total_sessions": 150,
            "total_users": 45,
            "avg_score": 78.5,
            "completion_rate": 85.2,
        },
        "metrics": {
            "performance": {
                "avg_methodology_score": 7.8,
                "avg_objection_handling": 7.5,
                "avg_empathy": 8.2,
            },
            "engagement": {
                "avg_session_duration": 1200,
                "avg_turns_per_session": 15,
            },
        },
    }

    # Export data
    exported_data = await export_service.export_analytics(
        analytics_data,
        format,
    )

    # Determine content type and filename
    content_type_map = {
        ExportFormat.JSON: "application/json",
        ExportFormat.MARKDOWN: "text/markdown",
        ExportFormat.CSV: "text/csv",
    }

    extension_map = {
        ExportFormat.JSON: "json",
        ExportFormat.MARKDOWN: "md",
        ExportFormat.CSV: "csv",
    }

    content_type = content_type_map.get(format, "application/octet-stream")
    extension = extension_map.get(format, "bin")
    filename = f"analytics.{extension}"

    return Response(
        content=exported_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )
