from aiohttp.web import Request, Response
from prometheus_client import generate_latest


async def check_health(request: Request) -> Response:
    return Response(text="OK", status=200)


async def get_metrics(request: Request) -> Response:
    return Response(
        text=generate_latest().decode("utf-8"),
        status=200
    )
