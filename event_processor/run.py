import argparse
import asyncio
from copy import deepcopy
from types import SimpleNamespace
from typing import Callable

import aiohttp
from aiohttp.client import ClientSession
from aiohttp.tracing import TraceRequestStartParams

from accounts_config import ACCOUNTS
from config import TIMEOUT_SECONDS
from src.collector import BalanceMetricsCollector, PositionMetricsCollector
from src.derivatives_api import AiohttpDerivativesUserDataAPI
from src.logger import LOGGER
from src.processor import AccountProcessor
from src.router import check_health, get_metrics


def on_request_start_aiohttp_request_logging(account_name: str) -> Callable:
    async def wrapper(
            session: ClientSession,
            context: SimpleNamespace,
            params: TraceRequestStartParams
    ):
        params_copy = deepcopy(params)
        params_copy.headers["X-MBX-APIKEY"] = "<hidden>"
        params_copy.headers["Sec-WebSocket-Key"] = "<hidden>"
        LOGGER.info(
            f"Starting request of '{account_name}' account <{params_copy}>"
        )

    return wrapper


def on_request_end_aiohttp_request_logging(account_name: str) -> Callable:
    async def wrapper(
            session: ClientSession,
            context: SimpleNamespace,
            params: TraceRequestStartParams
    ):
        LOGGER.info(
            f"Request of '{account_name}' account finished "
            f"with status {params.response.status} for {params.url}"  # type: ignore
        )

    return wrapper


async def main(
        host: str,
        port: str,
        binance_http_url: str,
        binance_ws_url: str,
):
    trace_configs = []
    for account in ACCOUNTS:
        trace_config = aiohttp.TraceConfig()
        trace_config.on_request_start.append(
            on_request_start_aiohttp_request_logging(account["name"])
        )
        trace_config.on_request_end.append(
            on_request_end_aiohttp_request_logging(account["name"])
        )
        trace_configs.append(trace_config)

    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
    sessions = [
        aiohttp.ClientSession(
            headers={
                "X-MBX-APIKEY": account["api_key"]
            },
            trace_configs=[trace_config],
            timeout=timeout,
            raise_for_status=True
        )
        for account, trace_config in zip(ACCOUNTS, trace_configs)
    ]

    account_processors = [
        AccountProcessor(
            name=account["name"],
            derivatives_api=AiohttpDerivativesUserDataAPI(
                account_name=account["name"],
                binance_http_url=binance_http_url,
                binance_ws_url=binance_ws_url,
                session=session
            ),
            balance_metrics_collector=BalanceMetricsCollector(),
            position_metrics_collector=PositionMetricsCollector()
        )
        for account, session in zip(ACCOUNTS, sessions)
    ]

    app = aiohttp.web.Application()
    app.add_routes(
        [
            aiohttp.web.get("/health", check_health),
            aiohttp.web.get("/metrics", get_metrics)
        ]
    )

    runner = aiohttp.web.AppRunner(app)
    await runner.setup()

    site = aiohttp.web.TCPSite(runner, host, int(port))
    await site.start()

    LOGGER.info(f"Start event processing for {len(ACCOUNTS)} accounts")
    LOGGER.info(f"Server started at http://{host}:{port}")

    try:
        await asyncio.gather(
            *[
                asyncio.create_task(account_processor.run())
                for account_processor in account_processors
            ]
        )
    finally:
        for session in sessions:
            await session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Welcome to balance binance futures service!"
    )

    parser.add_argument("--host")
    parser.add_argument("--port")
    parser.add_argument("--binance_http_host")
    parser.add_argument("--binance_ws_host")
    args = parser.parse_args()

    binance_http_url = f"https://{args.binance_http_host}"
    binance_ws_url = f"wss://{args.binance_ws_host}"

    asyncio.run(
        main(
            host=args.host,
            port=args.port,
            binance_http_url=binance_http_url,
            binance_ws_url=binance_ws_url
        )
    )
