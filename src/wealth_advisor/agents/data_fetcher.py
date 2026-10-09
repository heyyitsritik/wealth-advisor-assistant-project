
import logging
from dataclasses import dataclass, field

from wealth_advisor.models import ClientFinancialData
from wealth_advisor.tools.interfaces import CRMTool, FinancialDataTool

logger = logging.getLogger(__name__)


@dataclass
class FetchedClientData:
    """Financial data enriched with optional CRM context."""

    client: ClientFinancialData
    crm_context: dict | None
    warnings: list[str] = field(default_factory=list)


class DataFetcherAgent:
    """Retrieves financial data and enriches it with CRM context."""

    def __init__(
        self,
        financial_tool: FinancialDataTool,
        crm_tool: CRMTool,
    ):
        self.financial_tool = financial_tool
        self.crm_tool = crm_tool

    def run(self) -> FetchedClientData:
        logger.info("Data Fetcher Agent started")

        # Financial data is essential. If this fails, let the caller
        # handle the error rather than pretending the analysis succeeded.
        client = self.financial_tool.load_client_data()

        warnings = []
        crm_context = None

        try:
            crm_context = self.crm_tool.get_client_context(client.client_id)

            if crm_context is not None:
                crm_client_id = crm_context.get("client_id")

                if crm_client_id != client.client_id:
                    logger.error("CRM returned a mismatched client record")
                    crm_context = None
                    warnings.append(
                        "CRM context rejected because client IDs did not match."
                    )

        except Exception:
            # CRM is useful enrichment, but financial analysis can
            # continue if CRM is temporarily unavailable.
            logger.exception("CRM unavailable; continuing without CRM context")
            warnings.append(
                "CRM context unavailable; analysis will use financial data only."
            )

        if crm_context is None and not warnings:
            warnings.append("No matching CRM record was found.")

        logger.info(
            "Data Fetcher Agent completed for client_id=%s; crm_available=%s",
            client.client_id,
            crm_context is not None,
        )

        return FetchedClientData(
            client=client,
            crm_context=crm_context,
            warnings=warnings,
        )
