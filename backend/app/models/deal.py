"""
Deal & Encounter Models

Core data models for the sales battle system.
A Deal represents a real sales opportunity tracked through the methodology pipeline.
An Encounter represents a single interaction (prep, live, review) within a deal.
"""

from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, Enum, Integer, ForeignKey, Float, DateTime, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class DealStage(str, PyEnum):
    LEAD = "lead"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class EncounterType(str, PyEnum):
    PREP = "prep"
    LIVE = "live"
    REVIEW = "review"


class Deal(BaseModel):
    """
    A sales opportunity (deal / pipeline item).

    methodology_state stores the full MethodologyState JSON.
    methodology_score is a denormalized 0-100 for fast queries/sorting.
    """

    __tablename__ = "deals"
    __table_args__ = (
        Index("ix_deals_owner_stage", "owner_id", "stage"),
        Index("ix_deals_tenant_stage", "tenant_id", "stage"),
    )

    tenant_id = Column(String(100), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    customer_name = Column(String(200), nullable=False)
    customer_company = Column(String(200))
    customer_title = Column(String(200))
    customer_info = Column(Text)

    amount = Column(Float, default=0)
    stage = Column(Enum(DealStage), default=DealStage.LEAD, nullable=False)
    expected_close_date = Column(DateTime)
    close_reason = Column(Text)

    methodology_framework = Column(String(50), default="meddpicc")
    methodology_state = Column(Text)
    methodology_score = Column(Float, default=0)

    deal_metadata = Column(Text)

    owner = relationship("User", backref="deals")
    encounters = relationship("Encounter", back_populates="deal", cascade="all, delete-orphan", order_by="Encounter.created_at.desc()")

    def __repr__(self) -> str:
        return f"<Deal(id={self.id}, customer={self.customer_name}, stage={self.stage})>"


class Encounter(BaseModel):
    """A single interaction within a deal (preparation, live call, or review)."""

    __tablename__ = "encounters"

    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)

    encounter_type = Column(Enum(EncounterType), nullable=False)
    summary = Column(Text)
    methodology_before = Column(Text)
    methodology_after = Column(Text)
    action_items = Column(Text)

    encounter_metadata = Column(Text)

    deal = relationship("Deal", back_populates="encounters")
    session = relationship("Session", backref="encounters")

    def __repr__(self) -> str:
        return f"<Encounter(id={self.id}, deal_id={self.deal_id}, type={self.encounter_type})>"


class CockpitEvent(BaseModel):
    """Event stream for the executive cockpit dashboard."""

    __tablename__ = "cockpit_events"

    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(50), nullable=False, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True, index=True)
    payload = Column(Text)

    def __repr__(self) -> str:
        return f"<CockpitEvent(id={self.id}, type={self.event_type})>"
