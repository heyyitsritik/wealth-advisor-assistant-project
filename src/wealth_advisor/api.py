
import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from wealth_advisor.agents.analyzer import AnalyzerAgent
from wealth_advisor.agents.data_fetcher import DataFetcherAgent
from wealth_advisor.agents.orchestrator import OrchestratorAgent
from wealth_advisor.models import ClientFinancialData
from wealth_advisor.report_models import AdvisoryReport
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
        "transaction anomaly detection, and advisory reporting."
    ),
    version="0.1.0",
)


def create_orchestrator(
    client: ClientFinancialData,
) -> OrchestratorAgent:
    """Construct the agent pipeline for one API request."""

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
    return {"status": "healthy"}


@app.post(
    "/analyze",
    response_model=AdvisoryReport,
    responses={
        500: {
            "description": "The analysis pipeline failed.",
        }
    },
)
def analyze_client(client: ClientFinancialData):
    """Analyze submitted client data and return a structured report."""

    logger.info("Received analysis request for client_id=%s", client.client_id)

    report = create_orchestrator(client).run()

    if report.status == "failed":
        logger.error(
            "Analysis failed for client_id=%s",
            client.client_id,
        )
        return JSONResponse(
            status_code=500,
            content=report.model_dump(mode="json"),
        )

    return report
