import abc
import dataclasses
import json
from asyncio.exceptions import TimeoutError
from typing import AsyncGenerator

import aiohttp
import backoff
from aiohttp import ClientConnectionError, ClientResponseError
from src.logger import LOGGER
from src.util import get_now, is_not_backoff_case


class DerivativesUserDataAPI(abc.ABC):

    @abc.abstractmethod
    def get_events(self, events_types: list[str]) -> AsyncGenerator[dict, None]:
        pass


class AiohttpDerivativesUserDataAPI(DerivativesUserDataAPI):
    _listen_key_refresh_delta = 3300  # 55 minutes

    @dataclasses.dataclass
    class ListenKey:
        key: str
        last_refresh_time: int

    def __init__(
            self,
            account_name: str,
            binance_http_url: str,
            binance_ws_url: str,
            session: aiohttp.ClientSession
    ):
        self._account_name = account_name
        self._binance_http_url = binance_http_url
        self._binance_ws_url = binance_ws_url
        self._session = session
        self._listen_key: AiohttpDerivativesUserDataAPI.ListenKey | None = None

    @backoff.on_exception(
        backoff.expo,
        (
                TimeoutError,
                ClientConnectionError,
                ClientResponseError,
        ),
        max_tries=5,
        giveup=is_not_backoff_case  # type: ignore
    )
    async def _get_listen_key(self) -> ListenKey:
        url = f"{self._binance_http_url}/fapi/v1/listenKey"
        async with self._session.post(url) as response:
            key = (await response.json())["listenKey"]

        last_refresh_time = get_now()
        return AiohttpDerivativesUserDataAPI.ListenKey(
            key=key,
            last_refresh_time=last_refresh_time
        )

    @backoff.on_exception(
        backoff.expo,
        (
                TimeoutError,
                ClientConnectionError,
                ClientResponseError,
        ),
        max_tries=5,
        giveup=is_not_backoff_case  # type: ignore
    )
    async def _refresh_listen_key(self):
        now = get_now()
        last_refresh_time = self._listen_key.last_refresh_time
        if now - self._listen_key_refresh_delta > last_refresh_time:  # type: ignore
            url = f"{self._binance_http_url}/papi/v1/listenKey"
            await self._session.put(url)
            self._listen_key.last_refresh_time = now  # type: ignore

    async def get_events(self, events_types: list[str]) -> AsyncGenerator[dict, None]:
        if self._listen_key is None:
            self._listen_key = await self._get_listen_key()
        else:
            await self._refresh_listen_key()

        url = f"{self._binance_ws_url}/ws/{self._listen_key.key}"
        while True:
            async with self._session.ws_connect(url) as response:
                async for msg in response:
                    LOGGER.info(
                        f"Received message for '{self._account_name}' "
                        f"account: {msg}"
                    )

                    if msg.type == aiohttp.WSMsgType.ERROR:
                        LOGGER.error(
                            f"Received error for '{self._account_name}' "
                            f"account: {msg}"
                        )

                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue

                    msg_json = json.loads(msg.data)
                    if msg_json["e"] == "listenKeyExpired":
                        await self._refresh_listen_key()

                    if len(events_types) == 0 or msg_json["e"] in events_types:
                        yield msg_json
