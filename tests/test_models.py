
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from wealth_advisor.models import ClientFinancialData, Transaction


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "client_financial_data.json"


def load_client_data():
    return json.loads(DATA_PATH.read_text())


def test_sample_client_data_is_valid():
    client = ClientFinancialData.model_validate(load_client_data())

    assert client.client_id == "CLIENT-1001"
    assert len(client.accounts) == 3
    assert len(client.transactions) == 10


def test_transaction_amount_must_be_positive():
    with pytest.raises(ValidationError):
        Transaction.model_validate(
            {
                "transaction_id": "TXN-BAD",
                "date": "2026-09-28",
                "description": "Invalid payment",
                "amount": "-500.00",
                "currency": "INR",
                "transaction_type": "debit",
                "category": "shopping",
            }
        )


def test_unexpected_client_fields_are_rejected():
    data = load_client_data()
    data["unexpected_field"] = "should not be accepted"

    with pytest.raises(ValidationError):
        ClientFinancialData.model_validate(data)
