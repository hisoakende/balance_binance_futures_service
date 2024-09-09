from src.collector import (
    BalanceMetricsCollector,
    PositionMetricsCollector,
    AccountBalanceMetrics,
    AccountPositionMetrics
)
from src.derivatives_api import DerivativesUserDataAPI


class AccountProcessor:

    def __init__(
            self,
            name: str,
            derivatives_api: DerivativesUserDataAPI,
            balance_metrics_collector: BalanceMetricsCollector,
            position_metrics_collector: PositionMetricsCollector,
    ):
        self._name = name
        self._derivatives_api = derivatives_api
        self._balance_metrics_collector = balance_metrics_collector
        self._position_metrics_collector = position_metrics_collector

    async def run(self):
        async for event in self._derivatives_api.get_events(["ACCOUNT_UPDATE"]):
            balance_metrics = self._prepare_balance_metrics_collector(event)
            position_metrics = self._prepare_position_metrics_collector(event)

            self._balance_metrics_collector.save(
                account_name=self._name,
                metrics=balance_metrics
            )
            self._position_metrics_collector.save(
                account_name=self._name,
                metrics=position_metrics
            )

    @staticmethod
    def _prepare_balance_metrics_collector(event: dict) -> AccountBalanceMetrics:
        return {
            balance.pop("a"): balance
            for balance in event["a"]["B"]
        }

    @staticmethod
    def _prepare_position_metrics_collector(event: dict) -> AccountPositionMetrics:
        return {
            position["s"]: {"pa": position["pa"]}
            for position in event["a"]["P"]
        }
