FROM python:3.13-alpine

ENV METRICS_PORT=9617
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE ${METRICS_PORT}

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
RUN rm requirements.txt

WORKDIR /code
COPY ./pihole_metrics /code/pihole_metrics

RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /code
USER appuser

LABEL org.opencontainers.image.source="https://github.com/jimmydoh/pihole-metrics"
LABEL org.opencontainers.image.description="Prometheus Exporter for Pihole"

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD wget -q -O - http://127.0.0.1:$METRICS_PORT/health || exit 1

CMD ["sh", "-c", "fastapi run pihole_metrics/main.py --port $METRICS_PORT"]
