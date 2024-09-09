import datetime

from aiohttp import ClientConnectionError, ClientResponseError
from asyncio.exceptions import TimeoutError


def get_now() -> int:
    return int(datetime.datetime.utcnow().timestamp())


def is_not_backoff_case(
        e: TimeoutError | ClientConnectionError | ClientResponseError
) -> bool:
    is_backoff_case = (
            isinstance(e, (TimeoutError, ClientConnectionError))
            or e.status == 429
            or e.status >= 500
    )
    return not is_backoff_case
