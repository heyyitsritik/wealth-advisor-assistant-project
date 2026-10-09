
import logging

from wealth_advisor.agents.analyzer import AnalyzerAgent
from wealth_advisor.agents.data_fetcher import DataFetcherAgent
from wealth_advisor.report_models import AdvisoryReport

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Coordinates agents and produces the final advisory report."""

    def __init__(
        self,
        data_fetcher: DataFetcherAgent,
        analyzer: AnalyzerAgent,
    ):
        self.data_fetcher = data_fetcher
        self.analyzer = analyzer

    def run(self) -> AdvisoryReport:
        logger.info("Orchestrator started")

        try:
            fetched = self.data_fetcher.run()
        except Exception:
            logger.exception("Orchestrator: data fetching failed")

            return AdvisoryReport.create(
                status="failed",
                errors=[
                    "Unable to retrieve or validate essential financial data."
                ],
            )


        try:
            analysis = self.analyzer.run(fetched)
        except ValueError as exc:
            logger.exception("Orchestrator: financial analysis validation failed")

            error_message = (
                "The supplied financial data could not be analyzed. "
                "Check that all transactions use a consistent currency "
                "and that the input data is valid."
            )

            return AdvisoryReport.create(
                status="failed",
                client_id=fetched.client.client_id,
                crm_context=fetched.crm_context,
                warnings=fetched.warnings,
                errors=[error_message],
            )
        except Exception:
            logger.exception("Orchestrator: financial analysis failed")

            return AdvisoryReport.create(
                status="failed",
                client_id=fetched.client.client_id,
                crm_context=fetched.crm_context,
                warnings=fetched.warnings,
                errors=[
                    "Financial analysis failed; no completed advisory report "
                    "was produced."
                ],
            )


        requires_review = bool(
            analysis.anomalies or analysis.risk_signals
        )

        report = AdvisoryReport.create(
            status="completed",
            client_id=fetched.client.client_id,
            summary=analysis.summary,
            anomalies=analysis.anomalies,
            risk_signals=analysis.risk_signals,
            crm_context=fetched.crm_context,
            warnings=fetched.warnings,
            limitations=analysis.limitations,
            requires_human_review=requires_review,
        )

        logger.info(
            "Orchestrator completed: client_id=%s status=%s "
            "anomalies=%d review_required=%s",
            report.client_id,
            report.status,
            len(report.anomalies),
            report.requires_human_review,
        )

        return report
