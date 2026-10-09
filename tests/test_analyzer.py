
import json
from pathlib import Path

import pytest

from wealth_advisor.agents.analyzer import AnalyzerAgent
from wealth_advisor.agents.data_fetcher import FetchedClientData
from wealth_advisor.models import ClientFinancialData


DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "client_financial_data.json"
)


@pytest.fixture
def fetched_data():
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    client = ClientFinancialData.model_validate(raw)

    return FetchedClientData(
        client=client,
        crm_context=None,
    )


def test_analyzer_calculates_cash_flow(fetched_data):
    report = AnalyzerAgent().run(fetched_data)

    assert report.summary.total_income == 162000
    assert report.summary.total_expenses == 160300
    assert report.summary.net_cash_flow == 1700
    assert report.summary.transaction_count == 10


def test_analyzer_flags_large_electronics_purchase(fetched_data):
    report = AnalyzerAgent().run(fetched_data)

    flagged_ids = {
        anomaly.transaction_id for anomaly in report.anomalies
    }

    assert "TXN-008" in flagged_ids

    anomaly = next(
        item for item in report.anomalies
        if item.transaction_id == "TXN-008"
    )

    assert anomaly.amount == 95000
    assert anomaly.requires_human_review is True


def test_analyzer_calculates_category_spending(fetched_data):
    report = AnalyzerAgent().run(fetched_data)

    assert report.summary.spending_by_category["housing"] == 25000
    assert report.summary.spending_by_category["electronics"] == 95000
    assert report.summary.spending_by_category["investment"] == 20000


def test_analyzer_rejects_mixed_currencies(fetched_data):
    client = fetched_data.client
    transactions = list(client.transactions)

    transactions[0] = transactions[0].model_copy(
        update={"currency": "USD"}
    )

    mixed_currency_client = client.model_copy(
        update={"transactions": transactions}
    )

    mixed_data = FetchedClientData(
        client=mixed_currency_client,
        crm_context=None,
    )

    with pytest.raises(ValueError, match="Mixed-currency"):
        AnalyzerAgent().run(mixed_data)
