
import json
from pathlib import Path

import pytest

from wealth_advisor.agents.data_fetcher import DataFetcherAgent
from wealth_advisor.models import ClientFinancialData
from wealth_advisor.tools.json_financial_data_tool import (
    FinancialDataError,
    JsonFinancialDataTool,
)
from wealth_advisor.tools.mock_crm_tool import MockCRMTool


DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "client_financial_data.json"
)


class FailingCRMTool:
    def get_client_context(self, client_id: str):
        raise RuntimeError("Simulated CRM outage")


class StaticFinancialDataTool:
    def __init__(self, client: ClientFinancialData):
        self.client = client

    def load_client_data(self) -> ClientFinancialData:
        return self.client


def test_json_tool_loads_client_data():
    tool = JsonFinancialDataTool(DATA_PATH)

    client = tool.load_client_data()

    assert client.client_id == "CLIENT-1001"


def test_json_tool_handles_missing_file(tmp_path):
    tool = JsonFinancialDataTool(tmp_path / "missing.json")

    with pytest.raises(FinancialDataError):
        tool.load_client_data()


def test_fetcher_enriches_client_with_crm_context():
    agent = DataFetcherAgent(
        financial_tool=JsonFinancialDataTool(DATA_PATH),
        crm_tool=MockCRMTool(),
    )

    result = agent.run()

    assert result.client.client_id == "CLIENT-1001"
    assert result.crm_context is not None
    assert result.crm_context["relationship_manager"] == "Neha Verma"
    assert result.warnings == []


def test_fetcher_continues_when_crm_fails():
    agent = DataFetcherAgent(
        financial_tool=JsonFinancialDataTool(DATA_PATH),
        crm_tool=FailingCRMTool(),
    )

    result = agent.run()

    assert result.client.client_id == "CLIENT-1001"
    assert result.crm_context is None
    assert any("CRM context unavailable" in warning for warning in result.warnings)


def test_fetcher_rejects_mismatched_crm_client():
    client = ClientFinancialData.model_validate(
        json.loads(DATA_PATH.read_text(encoding="utf-8"))
    )

    mismatched_crm = MockCRMTool(
        records={
            "CLIENT-1001": {
                "client_id": "CLIENT-9999",
                "relationship_manager": "Unknown",
            }
        }
    )

    agent = DataFetcherAgent(
        financial_tool=StaticFinancialDataTool(client),
        crm_tool=mismatched_crm,
    )

    result = agent.run()

    assert result.crm_context is None
    assert any("IDs did not match" in warning for warning in result.warnings)
