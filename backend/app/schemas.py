"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DonationCreate(BaseModel):
    donor_name: str = Field(min_length=1, max_length=120)
    donor_type: str = Field(default="restaurant", pattern="^(restaurant|business|individual)$")
    category: str = Field(min_length=1, max_length=60)
    food_name: str = Field(default="Surplus meal", max_length=160)
    total_portions: int = Field(gt=0, le=100_000)
    pickup_deadline: datetime
    pickup_address: str = Field(default="Demo kitchen", max_length=255)
    notes: str | None = None
    is_demo: bool = False


class DonationOut(BaseModel):
    id: int
    donor_name: str
    category: str
    food_name: str
    total_portions: int
    remaining_portions: int
    pickup_deadline: datetime
    pickup_address: str
    notes: str | None
    status: str
    is_demo: bool
    created_at: datetime | None = None


class PickupUpdate(BaseModel):
    pickup_status: str = Field(pattern="^(pending|confirmed|completed|failed)$")


class DonationReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    feedback: str = Field(default="", max_length=2000)


class ExplainMatchRequest(BaseModel):
    donation_id: int


class ExplainMatchResponse(BaseModel):
    donation_id: int
    source: str  # Gemini only; unavailable or invalid output returns HTTP 503
    summary: str
    matches: list[dict]
    suggested_actions: list[str]


class HealthOut(BaseModel):
    status: str
    service: str
    demo_mode: bool
    database: str
