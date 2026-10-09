
from typing import Protocol

from wealth_advisor.models import ClientFinancialData


class FinancialDataTool(Protocol):
    """Interface for retrieving validated client financial data."""

    def load_client_data(self) -> ClientFinancialData:
        ...


class CRMTool(Protocol):
    """Interface for retrieving additional CRM context."""

    def get_client_context(self, client_id: str) -> dict | None:
        ...
