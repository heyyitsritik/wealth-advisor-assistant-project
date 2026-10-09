
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ReviewDecision = Literal["approved", "rejected", "investigate"]


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision
    reviewer: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=3, max_length=1000)


class ReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: int
    report_id: str
    client_id: str
    decision: ReviewDecision
    reviewer: str
    reason: str
    reviewed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
