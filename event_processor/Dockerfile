FROM python:3.11

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT [ \
    "sh", "-c", \
    "python3 run.py --host $HOST --port $PORT --binance_http_host $BINANCE_HTTP_HOST --binance_ws_host $BINANCE_WS_HOST" \
]
