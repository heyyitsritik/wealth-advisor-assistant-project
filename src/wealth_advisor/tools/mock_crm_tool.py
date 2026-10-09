
import logging

logger = logging.getLogger(__name__)


class CRMError(Exception):
    """Raised when CRM data cannot be retrieved."""


class MockCRMTool:
    """Simulates a CRM integration without external dependencies."""

    def __init__(self, records: dict[str, dict] | None = None):
        self.records = records or {
            "CLIENT-1001": {
                "client_id": "CLIENT-1001",
                "relationship_manager": "Neha Verma",
                "last_contact_date": "2026-09-20",
                "preferred_contact_channel": "email",
                "notes": [
                    "Client is saving toward a home purchase.",
                    "Client prefers quarterly portfolio reviews.",
                ],
            }
        }

    def get_client_context(self, client_id: str) -> dict | None:
        logger.info("Fetching CRM context for client_id=%s", client_id)

        try:
            record = self.records.get(client_id)

            if record is None:
                logger.warning(
                    "No CRM record found for client_id=%s",
                    client_id,
                )
                return None

            # Return a copy so callers cannot mutate the stored record.
            return dict(record)

        except Exception as exc:
            logger.exception("CRM lookup failed")
            raise CRMError("Unable to retrieve CRM context") from exc
