
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransactionAnomaly(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    description: str
    amount: Decimal
    currency: str
    reason: str
    severity: Literal["low", "medium", "high"]
    requires_human_review: bool = True


class RiskSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_type: str
    severity: Literal["low", "medium", "high"]
    description: str
    evidence: list[str] = Field(min_length=1)
    recommended_action: str


class FinancialSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_income: Decimal
    total_expenses: Decimal
    net_cash_flow: Decimal
    spending_by_category: dict[str, Decimal]
    transaction_count: int
    currencies: list[str]


class AnalysisReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str
    summary: FinancialSummary
    anomalies: list[TransactionAnomaly]
    risk_signals: list[RiskSignal]
    limitations: list[str]
