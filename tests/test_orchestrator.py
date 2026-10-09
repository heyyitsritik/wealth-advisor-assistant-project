
import json
from pathlib import Path

from wealth_advisor.agents.analyzer import AnalyzerAgent
from wealth_advisor.agents.data_fetcher import DataFetcherAgent
from wealth_advisor.agents.orchestrator import OrchestratorAgent
from wealth_advisor.models import ClientFinancialData
from wealth_advisor.tools.json_financial_data_tool import JsonFinancialDataTool
from wealth_advisor.tools.mock_crm_tool import MockCRMTool


DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "client_financial_data.json"
)


class FailingFinancialDataTool:
    def load_client_data(self):
        raise RuntimeError("Simulated financial data outage")


class FailingAnalyzer:
    def run(self, fetched):
        raise RuntimeError("Simulated analyzer failure")


class StaticFinancialDataTool:
    def __init__(self, client):
        self.client = client

    def load_client_data(self):
        return self.client


def build_orchestrator(
    financial_tool=None,
    crm_tool=None,
    analyzer=None,
):
    fetcher = DataFetcherAgent(
        financial_tool=financial_tool or JsonFinancialDataTool(DATA_PATH),
        crm_tool=crm_tool or MockCRMTool(),
    )

    return OrchestratorAgent(
        data_fetcher=fetcher,
        analyzer=analyzer or AnalyzerAgent(),
    )


def test_orchestrator_returns_completed_report():
    report = build_orchestrator().run()

    assert report.status == "completed"
    assert report.client_id == "CLIENT-1001"
    assert report.summary is not None
    assert report.limitations
    assert any(
        "transactions supplied" in limitation
        for limitation in report.limitations
    )
    assert report.summary.net_cash_flow == 1700
    assert len(report.anomalies) >= 1
    assert report.requires_human_review is True
    assert report.errors == []


def test_orchestrator_continues_without_crm():
    class FailingCRM:
        def get_client_context(self, client_id):
            raise RuntimeError("Simulated CRM outage")

    report = build_orchestrator(crm_tool=FailingCRM()).run()

    assert report.status == "completed"
    assert report.summary is not None
    assert report.crm_context is None
    assert any("CRM context unavailable" in w for w in report.warnings)


def test_orchestrator_returns_failed_report_on_data_failure():
    report = build_orchestrator(
        financial_tool=FailingFinancialDataTool()
    ).run()

    assert report.status == "failed"
    assert report.summary is None
    assert report.errors
    assert report.client_id is None


def test_orchestrator_returns_failed_report_on_analysis_failure():
    client = ClientFinancialData.model_validate(
        json.loads(DATA_PATH.read_text(encoding="utf-8"))
    )

    report = build_orchestrator(
        financial_tool=StaticFinancialDataTool(client),
        analyzer=FailingAnalyzer(),
    ).run()

    assert report.status == "failed"
    assert report.client_id == "CLIENT-1001"
    assert report.summary is None
    assert report.errors

def test_orchestrator_returns_helpful_error_on_invalid_analysis_data():
    client = ClientFinancialData.model_validate(
        json.loads(DATA_PATH.read_text(encoding="utf-8"))
    )

    class InvalidDataAnalyzer:
        def run(self, fetched):
            raise ValueError(
                "Mixed-currency transactions require currency conversion."
            )

    report = build_orchestrator(
        financial_tool=StaticFinancialDataTool(client),
        analyzer=InvalidDataAnalyzer(),
    ).run()

    assert report.status == "failed"
    assert report.summary is None
    assert report.errors
    assert "consistent currency" in report.errors[0]
    assert "Mixed-currency transactions require currency conversion" not in (
        report.errors[0]
    )
