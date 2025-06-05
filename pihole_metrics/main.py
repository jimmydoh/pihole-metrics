# main.py
"""TODO: Module Docstring"""
import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from starlette.routing import Mount
from . import exporter

VALID_LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


# Filter out health check access logs from uvicorn.access
class LogFilter(logging.Filter):
    """TODO: LogFilter Class Docstring"""

    def filter(self, record):
        if record.args and len(record.args) >= 3:
            if record.args[2] in ["/health", "/healthz"]:
                return False
        return True


logger_access = logging.getLogger("uvicorn.access")
logger_access.addFilter(LogFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """TODO: lifespan Docstring"""

    # Offload logging to upstream uvicorn
    logger = logging.getLogger("uvicorn.asgi")
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    if log_level_name in VALID_LOG_LEVELS:
        log_level = VALID_LOG_LEVELS[log_level_name]
    else:
        logger.warning("Invalid log level: %s. Defaulting to INFO.", log_level_name)
        log_level = logging.INFO
    logger.setLevel(log_level)

    # Start main metrics processing
    logger.info("Starting FastAPI Lifespan")
    metrics = exporter.Metrics()
    asyncio.create_task(metrics.data_loop())

    yield

    # Close down connections
    logger.info("Ending FastAPI Lifespan")
    metrics.close()


# FastAPI app
app = FastAPI(lifespan=lifespan)


# Mount metrics from prometheus_client ASGI App
route = Mount("/metrics", make_asgi_app())
route.path_regex = re.compile('^/metrics(?P<path>.*)$')
app.routes.append(route)

# Basic health check route
@app.get("/health")
@app.get("/healthz")
def health_page():
    """A simple health page"""
    data = {"status": "OK"}
    return JSONResponse(content=data)


if __name__ == '__main__':
    print("Pihole Prometheus Exporter")
    print("FastAPI Routes:")
    for route in app.routes:
        print(f"  >> {route.path}")