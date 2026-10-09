
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Transaction(BaseModel):
    """A single transaction from a client's financial account."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(min_length=1)
    date: date
    description: str = Field(min_length=1)
    amount: Decimal
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    transaction_type: Literal["credit", "debit"]
    category: str = Field(min_length=1)
    merchant: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("Transaction amount must be a positive finite number")
        return value


class Account(BaseModel):
    """A client's financial account."""

    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(min_length=1)
    account_type: Literal[
        "savings",
        "current",
        "investment",
        "credit_card",
    ]
    balance: Decimal
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")

    @field_validator("balance")
    @classmethod
    def balance_must_be_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Account balance must be finite")
        return value


class RiskProfile(BaseModel):
    """Client's declared investment preferences."""

    model_config = ConfigDict(extra="forbid")

    risk_tolerance: Literal["low", "moderate", "high"]
    investment_horizon_years: int = Field(ge=0, le=100)
    investment_goals: list[str] = Field(min_length=1)


class ClientFinancialData(BaseModel):
    """Validated financial data used by the advisor assistant."""

    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    age: int = Field(ge=18, le=120)
    monthly_income: Decimal = Field(gt=0)
    accounts: list[Account] = Field(min_length=1)
    transactions: list[Transaction]
    risk_profile: RiskProfile
