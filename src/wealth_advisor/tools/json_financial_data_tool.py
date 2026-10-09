
import json
import logging
from pathlib import Path

from pydantic import ValidationError

from wealth_advisor.models import ClientFinancialData

logger = logging.getLogger(__name__)


class FinancialDataError(Exception):
    """Raised when financial data cannot be loaded or validated."""


class JsonFinancialDataTool:
    """Loads client financial data from a JSON file."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def load_client_data(self) -> ClientFinancialData:
        logger.info("Loading financial data from %s", self.file_path)

        try:
            raw_data = json.loads(self.file_path.read_text(encoding="utf-8"))
            client = ClientFinancialData.model_validate(raw_data)
            logger.info(
                "Loaded financial data for client_id=%s",
                client.client_id,
            )
            return client

        except FileNotFoundError as exc:
            logger.exception("Financial data file not found")
            raise FinancialDataError(
                f"Financial data file not found: {self.file_path}"
            ) from exc

        except (json.JSONDecodeError, ValidationError) as exc:
            logger.exception("Financial data is invalid")
            raise FinancialDataError(
                "Financial data could not be parsed or validated"
            ) from exc

        except OSError as exc:
            logger.exception("Could not read financial data file")
            raise FinancialDataError(
                "Financial data file could not be read"
            ) from exc
