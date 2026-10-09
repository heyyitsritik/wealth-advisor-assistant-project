
from wealth_advisor.models import ClientFinancialData


class InMemoryFinancialDataTool:
    """Provides validated financial data supplied to the API."""

    def __init__(self, client: ClientFinancialData):
        self.client = client

    def load_client_data(self) -> ClientFinancialData:
        return self.client
