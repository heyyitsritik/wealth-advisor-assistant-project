
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from wealth_advisor.agents.analyzer import AnalyzerAgent
from wealth_advisor.agents.data_fetcher import DataFetcherAgent
from wealth_advisor.agents.orchestrator import OrchestratorAgent
from wealth_advisor.models import ClientFinancialData
from wealth_advisor.report_models import AdvisoryReport
from wealth_advisor.review_models import ReviewRequest
from wealth_advisor.services.memory_store import MemoryStore
from wealth_advisor.tools.in_memory_financial_data_tool import (
    InMemoryFinancialDataTool,
)
from wealth_advisor.tools.mock_crm_tool import MockCRMTool


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Wealth Advisor Assistant",
    description=(
        "A modular multi-agent system for financial analysis, "
        "transaction anomaly detection, persistent memory, and human review."
    ),
    version="0.1.0",
)

DATABASE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "wealth_advisor.db"
)

memory_store = MemoryStore(DATABASE_PATH)


class AnalysisResponse(BaseModel):
    report_id: str
    report: AdvisoryReport


def create_orchestrator(
    client: ClientFinancialData,
) -> OrchestratorAgent:
    """Build an independent agent pipeline for one client request."""

    fetcher = DataFetcherAgent(
        financial_tool=InMemoryFinancialDataTool(client),
        crm_tool=MockCRMTool(),
    )

    return OrchestratorAgent(
        data_fetcher=fetcher,
        analyzer=AnalyzerAgent(),
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    """Check API availability."""

    return {"status": "healthy"}


@app.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        500: {"description": "The analysis pipeline failed."},
    },
)
def analyze_client(client: ClientFinancialData):
    """Analyze client data and persist the generated report."""

    logger.info(
        "Received analysis request for client_id=%s",
        client.client_id,
    )

    report = create_orchestrator(client).run()

    try:
        report_id = memory_store.save_report(report)
    except Exception:
        logger.exception("Could not persist analysis report")

        if report.status == "failed":
            report.warnings.append(
                "Report persistence failed; historical retrieval is unavailable."
            )
        else:
            report.warnings.append(
                "Analysis completed, but the report could not be persisted."
            )

        if report.status == "failed":
            return JSONResponse(
                status_code=500,
                content=report.model_dump(mode="json"),
            )

        raise HTTPException(
            status_code=500,
            detail="Analysis completed, but report persistence failed.",
        )

    if report.status == "failed":
        return JSONResponse(
            status_code=500,
            content={
                "report_id": report_id,
                "report": report.model_dump(mode="json"),
            },
        )

    return AnalysisResponse(
        report_id=report_id,
        report=report,
    )


@app.get("/memory/{client_id}")
def get_client_memory(
    client_id: str,
    limit: int = Query(default=10, ge=1, le=100),
):
    """Retrieve recent report history for a client."""

    return {
        "client_id": client_id,
        "reports": memory_store.list_reports(client_id, limit),
    }


@app.get("/reports/{report_id}")
def get_report(report_id: str):
    """Retrieve a previously stored report."""

    record = memory_store.get_report(report_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return {
        "report_id": record["report_id"],
        "client_id": record["client_id"],
        "status": record["status"],
        "created_at": record["created_at"],
        "report": AdvisoryReport.model_validate_json(
            record["report_json"]
        ),
    }


@app.post("/reports/{report_id}/review")
def review_report(
    report_id: str,
    request: ReviewRequest,
):
    """Record a human review decision for a stored report."""

    try:
        review = memory_store.save_review(report_id, request)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        ) from None

    return review


@app.get("/reports/{report_id}/reviews")
def get_report_reviews(report_id: str):
    """Retrieve recorded review decisions for a report."""

    if memory_store.get_report(report_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return {
        "report_id": report_id,
        "reviews": memory_store.list_reviews(report_id),
    }
