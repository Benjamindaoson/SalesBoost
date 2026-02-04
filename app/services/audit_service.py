import logging
import uuid
from datetime import datetime
from core.database import get_db_session
from models.saas_models import AuditLog
from app.infra.events.bus import bus
from app.infra.events.schemas import EventType, AuditEventPayload

logger = logging.getLogger(__name__)

class AuditService:
    """
    Subscribes to audit events and persists them to the database.
    """
    
    @staticmethod
    @bus.subscribe(EventType.SENSITIVE_CONTENT_BLOCKED)
    async def handle_security_violation(payload: AuditEventPayload):
        logger.warning(f"Security violation detected: {payload.reason}")
        await AuditService.save_audit_log(
            tenant_id=payload.tenant_id,
            user_id=payload.user_id,
            action="SECURITY_BLOCK",
            resource_type="content",
            resource_id=payload.session_id,
            details={
                "reason": payload.reason,
                "severity": payload.severity,
                "risk_score": payload.risk_score
            }
        )

    @staticmethod
    @bus.subscribe(EventType.ACCESS_LOGGED)
    async def handle_access_log(payload: AuditEventPayload):
        await AuditService.save_audit_log(
            tenant_id=payload.tenant_id,
            user_id=payload.user_id,
            action="ACCESS",
            resource_type="api",
            resource_id=payload.details.get("path") if isinstance(payload.details, dict) else None,
            details={
                "reason": payload.reason,
                "severity": payload.severity,
                "details": payload.details,
            },
        )

    @staticmethod
    @bus.subscribe(EventType.MODEL_LIFECYCLE_DECISION)
    async def handle_model_lifecycle(payload: AuditEventPayload):
        await AuditService.save_audit_log(
            tenant_id=payload.tenant_id,
            user_id=payload.user_id,
            action="MODEL_LIFECYCLE",
            resource_type="model",
            resource_id=payload.details.get("model_key") if isinstance(payload.details, dict) else None,
            details={
                "reason": payload.reason,
                "severity": payload.severity,
                "details": payload.details,
            },
        )

    @staticmethod
    async def save_audit_log(
        tenant_id: str,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict
    ):
        """Helper to save a log entry to DB in a fresh session."""
        async for db in get_db_session():
            try:
                entry = AuditLog(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(entry)
                await db.commit()
                logger.debug(f"Audit log saved: {action} for {resource_id}")
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to save audit log: {e}")
            finally:
                break # Ensure we only use one session

# Initialize service to register subscribers
audit_service = AuditService()


def initialize_plugin():
    """Plugin initialization hook for startup orchestration.
    Allows future replacement via external plugin loading without changing core startup.
    """
    logger.info("Initializing AuditService plugin (startup hook)")
    return audit_service
