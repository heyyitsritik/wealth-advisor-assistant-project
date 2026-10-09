
import json
from pathlib import Path

from wealth_advisor.agents.analyzer import AnalyzerAgent
from wealth_advisor.agents.data_fetcher import DataFetcherAgent
from wealth_advisor.agents.orchestrator import OrchestratorAgent
from wealth_advisor.models import ClientFinancialData
from wealth_advisor.review_models import ReviewRequest
from wealth_advisor.services.memory_store import MemoryStore
from wealth_advisor.tools.json_financial_data_tool import JsonFinancialDataTool
from wealth_advisor.tools.mock_crm_tool import MockCRMTool


DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "client_financial_data.json"
)


def create_report():
    client = ClientFinancialData.model_validate(
        json.loads(DATA_PATH.read_text(encoding="utf-8"))
    )

    fetcher = DataFetcherAgent(
        financial_tool=JsonFinancialDataTool(DATA_PATH),
        crm_tool=MockCRMTool(),
    )

    return OrchestratorAgent(
        data_fetcher=fetcher,
        analyzer=AnalyzerAgent(),
    ).run()


def test_report_can_be_saved_and_retrieved(tmp_path):
    store = MemoryStore(tmp_path / "test.db")
    report = create_report()

    report_id = store.save_report(report)
    saved = store.get_report(report_id)

    assert saved is not None
    assert saved["client_id"] == "CLIENT-1001"
    assert json.loads(saved["report_json"])["status"] == "completed"


def test_report_history_is_filtered_by_client(tmp_path):
    store = MemoryStore(tmp_path / "test.db")

    report_id = store.save_report(create_report())

    history = store.list_reports("CLIENT-1001")

    assert len(history) == 1
    assert history[0]["report_id"] == report_id
    assert store.list_reports("CLIENT-9999") == []


def test_review_is_persisted(tmp_path):
    store = MemoryStore(tmp_path / "test.db")
    report_id = store.save_report(create_report())

    review = store.save_review(
        report_id,
        ReviewRequest(
            decision="investigate",
            reviewer="Test Reviewer",
            reason="Please verify the unusually large purchase.",
        ),
    )

    reviews = store.list_reviews(report_id)

    assert review.decision == "investigate"
    assert review.client_id == "CLIENT-1001"
    assert len(reviews) == 1
    assert reviews[0]["reviewer"] == "Test Reviewer"


def test_review_for_unknown_report_is_rejected(tmp_path):
    store = MemoryStore(tmp_path / "test.db")

    try:
        store.save_review(
            "unknown-report",
            ReviewRequest(
                decision="rejected",
                reviewer="Test Reviewer",
                reason="No report exists for this ID.",
            ),
        )
    except KeyError:
        pass
    else:
        raise AssertionError("Expected unknown report to be rejected")
