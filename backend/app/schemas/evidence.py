from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    match_id: UUID
    submitted_by: UUID
    claimed_score_a: int
    claimed_score_b: int
    created_at: datetime


class DisputeCreate(BaseModel):
    reason: str | None = None


class ResolveDispute(BaseModel):
    score_a: int = Field(ge=0)
    score_b: int = Field(ge=0)
