
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wealth_advisor.analysis_models import (
    FinancialSummary,
    RiskSignal,
    TransactionAnomaly,
)


class AdvisoryReport(BaseModel):
    """Structured result produced by the orchestrator."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    client_id: str | None = None
    generated_at: datetime
    summary: FinancialSummary | None = None
    anomalies: list[TransactionAnomaly] = Field(default_factory=list)
    risk_signals: list[RiskSignal] = Field(default_factory=list)
    crm_context: dict | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    requires_human_review: bool = False

    @classmethod
    def create(
        cls,
        status: Literal["completed", "failed"],
        **kwargs,
    ) -> "AdvisoryReport":
        return cls(
            status=status,
            generated_at=datetime.now(timezone.utc),
            **kwargs,
        )
