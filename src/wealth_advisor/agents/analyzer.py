
import logging
from collections import defaultdict
from decimal import Decimal
from statistics import median

from wealth_advisor.agents.data_fetcher import FetchedClientData
from wealth_advisor.analysis_models import (
    AnalysisReport,
    FinancialSummary,
    RiskSignal,
    TransactionAnomaly,
)

logger = logging.getLogger(__name__)

ZERO = Decimal("0")
MINIMUM_UNUSUAL_AMOUNT = Decimal("25000")
UNUSUAL_AMOUNT_MULTIPLIER = Decimal("5")


class AnalyzerAgent:
    """Performs deterministic financial analysis and anomaly detection."""

    def run(self, fetched: FetchedClientData) -> AnalysisReport:
        logger.info(
            "Analyzer Agent started for client_id=%s",
            fetched.client.client_id,
        )

        client = fetched.client
        transactions = client.transactions

        currencies = sorted({txn.currency for txn in transactions})

        # Avoid combining amounts from different currencies.
        if len(currencies) > 1:
            raise ValueError(
                "Mixed-currency transactions require currency conversion "
                "before consolidated analysis."
            )

        credits = [
            txn for txn in transactions if txn.transaction_type == "credit"
        ]
        debits = [
            txn for txn in transactions if txn.transaction_type == "debit"
        ]

        total_income = sum((txn.amount for txn in credits), ZERO)
        total_expenses = sum((txn.amount for txn in debits), ZERO)
        net_cash_flow = total_income - total_expenses

        category_totals: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for txn in debits:
            category_totals[txn.category] += txn.amount

        summary = FinancialSummary(
            total_income=total_income,
            total_expenses=total_expenses,
            net_cash_flow=net_cash_flow,
            spending_by_category=dict(sorted(category_totals.items())),
            transaction_count=len(transactions),
            currencies=currencies,
        )

        anomalies = self._detect_anomalies(debits)
        risk_signals = self._detect_risk_signals(
            client,
            total_income,
            total_expenses,
            net_cash_flow,
            anomalies,
        )

        limitations = [
            "Analysis covers only the transactions supplied in the input.",
            "An unusual amount is a review signal, not proof of fraud.",
            "Long-term spending trends cannot be established from this "
            "single-period sample.",
            "Anomaly thresholds are heuristic and may be unreliable when "
            "few comparison transactions are available.",
            "No investment recommendation is made by this analysis.",
        ]

        report = AnalysisReport(
            client_id=client.client_id,
            summary=summary,
            anomalies=anomalies,
            risk_signals=risk_signals,
            limitations=limitations,
        )

        logger.info(
            "Analyzer Agent completed for client_id=%s; anomalies=%d",
            client.client_id,
            len(anomalies),
        )

        return report

    @staticmethod
    def _detect_anomalies(debits) -> list[TransactionAnomaly]:
        """Flag large debits using a baseline that excludes the transaction."""
        if not debits:
            return []

        anomalies = []

        for index, txn in enumerate(debits):
            # Exclude the transaction being evaluated from its own baseline.
            peer_amounts = [
                other.amount
                for peer_index, other in enumerate(debits)
                if peer_index != index
            ]

            if peer_amounts:
                typical_amount = Decimal(str(median(peer_amounts)))
                threshold = max(
                    MINIMUM_UNUSUAL_AMOUNT,
                    typical_amount * UNUSUAL_AMOUNT_MULTIPLIER,
                )
                baseline_description = (
                    f"median of other debit transactions "
                    f"({typical_amount})"
                )
            else:
                # With one debit, there is no peer baseline.
                threshold = MINIMUM_UNUSUAL_AMOUNT
                baseline_description = "minimum unusual-amount threshold"

            if txn.amount >= threshold:
                anomalies.append(
                    TransactionAnomaly(
                        transaction_id=txn.transaction_id,
                        description=txn.description,
                        amount=txn.amount,
                        currency=txn.currency,
                        reason=(
                            f"Debit amount meets or exceeds the threshold "
                            f"({threshold}), based on the "
                            f"{baseline_description} and minimum threshold "
                            f"({MINIMUM_UNUSUAL_AMOUNT})."
                        ),
                        severity=(
                            "high"
                            if txn.amount >= threshold * 2
                            else "medium"
                        ),
                    )
                )

        return anomalies

    @staticmethod
    def _detect_risk_signals(
        client,
        total_income: Decimal,
        total_expenses: Decimal,
        net_cash_flow: Decimal,
        anomalies: list[TransactionAnomaly],
    ) -> list[RiskSignal]:
        signals = []

        if total_expenses > total_income:
            signals.append(
                RiskSignal(
                    signal_type="negative_cash_flow",
                    severity="high",
                    description=(
                        "Observed debit transactions exceed observed credits."
                    ),
                    evidence=[
                        f"Observed credits: {total_income}",
                        f"Observed debits: {total_expenses}",
                        f"Net cash flow: {net_cash_flow}",
                    ],
                    recommended_action=(
                        "Review the transaction period and recurring "
                        "expenses before drawing conclusions about "
                        "the client's overall financial position."
                    ),
                )
            )

        for anomaly in anomalies:
            signals.append(
                RiskSignal(
                    signal_type="unusual_transaction",
                    severity=anomaly.severity,
                    description=(
                        f"Transaction {anomaly.transaction_id} warrants review."
                    ),
                    evidence=[
                        f"Description: {anomaly.description}",
                        f"Amount: {anomaly.amount} {anomaly.currency}",
                        f"Reason: {anomaly.reason}",
                    ],
                    recommended_action=(
                        "Ask the client or authorized relationship manager "
                        "to verify the transaction before taking action."
                    ),
                )
            )

        for account in client.accounts:
            if (
                account.account_type == "credit_card"
                and account.balance < ZERO
            ):
                signals.append(
                    RiskSignal(
                        signal_type="credit_card_balance_convention",
                        severity="low",
                        description=(
                            "The credit-card account has a negative "
                            "reported balance. Confirm the source system's "
                            "balance convention before interpreting it."
                        ),
                        evidence=[
                            f"Account ID: {account.account_id}",
                            f"Reported balance: {account.balance} "
                            f"{account.currency}",
                        ],
                        recommended_action=(
                            "Verify whether the negative balance represents "
                            "outstanding debt, a credit balance, or a "
                            "source-system sign convention."
                        ),
                    )
                )

        return signals
