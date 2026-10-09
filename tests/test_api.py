
import json
from pathlib import Path

from fastapi.testclient import TestClient

from wealth_advisor.api import app


client = TestClient(app)

DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "client_financial_data.json"
)


def load_sample_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_analyze_endpoint_returns_structured_report():
    response = client.post("/analyze", json=load_sample_data())

    assert response.status_code == 200

    payload = response.json()

    assert payload["report_id"]
    report = payload["report"]

    assert report["status"] == "completed"
    assert report["client_id"] == "CLIENT-1001"
    assert report["summary"]["net_cash_flow"] == "1700.00"
    assert len(report["anomalies"]) >= 1
    assert report["requires_human_review"] is True


def test_analyze_endpoint_rejects_invalid_input():
    response = client.post(
        "/analyze",
        json={"client_id": "CLIENT-1001"},
    )

    assert response.status_code == 422


def test_analyze_endpoint_reports_pipeline_failure():
    data = load_sample_data()
    data["transactions"][0]["currency"] = "USD"

    response = client.post("/analyze", json=data)

    assert response.status_code == 500

    payload = response.json()

    assert payload["report_id"]
    report = payload["report"]

    assert report["status"] == "failed"
    assert report["summary"] is None
    assert report["errors"]
