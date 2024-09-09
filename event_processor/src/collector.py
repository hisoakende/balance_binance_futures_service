from abc import abstractmethod
from collections import defaultdict
from typing import Any, Iterable

from prometheus_client.core import GaugeMetricFamily, REGISTRY
from prometheus_client.registry import Collector
from prometheus_client.metrics_core import Metric

from src.logger import LOGGER

TokenMetrics = dict[str, float]
PositionMetrics = dict[str, float]
AccountBalanceMetrics = dict[str, TokenMetrics]
AccountPositionMetrics = dict[str, PositionMetrics]
Metrics = dict[str, Any]


class MetricsCollector(Collector):
    state: dict[str, Metrics] = None  # type: ignore

    @classmethod
    def save(cls, account_name: str, metrics: dict[str, Any]):
        cls.state[account_name] |= metrics
        LOGGER.info(
            f"Current {cls.__name__} metrics "
            f"for '{account_name}' account: {metrics}"
        )

    @abstractmethod
    def collect(self) -> Iterable[Metric]:
        pass


class BalanceMetricsCollector(MetricsCollector):
    state: dict[str, AccountBalanceMetrics] = defaultdict(dict)

    def collect(self) -> Iterable[Metric]:
        wallet_balance = GaugeMetricFamily(
            "wallet_balance",
            "Wallet balance for each account and token",
            labels=["account_name", "token"]
        )
        cross_wallet_balance = GaugeMetricFamily(
            "cross_wallet_balance",
            "Cross wallet balance for each account and token",
            labels=["account_name", "token"]
        )
        balance_change = GaugeMetricFamily(
            "balance_change",
            "Balance change for each account and token",
            labels=["account_name", "token"]
        )

        for account_name, tokens in self.state.items():
            for currency, metrics in tokens.items():
                wallet_balance.add_metric(
                    [account_name, currency], metrics["wb"]
                )
                cross_wallet_balance.add_metric(
                    [account_name, currency], metrics["cw"]
                )
                balance_change.add_metric(
                    [account_name, currency], metrics["bc"]
                )

        yield wallet_balance
        yield cross_wallet_balance
        yield balance_change


class PositionMetricsCollector(MetricsCollector):
    state: dict[str, AccountPositionMetrics] = defaultdict(dict)

    def collect(self) -> Iterable[Metric]:
        position_amount = GaugeMetricFamily(
            "position_amount",
            "Position amount for each account and symbol",
            labels=["account_name", "symbol"]
        )

        for account_name, positions in self.state.items():
            for position, metrics in positions.items():
                position_amount.add_metric(
                    [account_name, position], metrics["pa"]
                )

        yield position_amount


REGISTRY.register(BalanceMetricsCollector())
REGISTRY.register(PositionMetricsCollector())
