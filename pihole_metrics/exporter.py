# exporter.py
"""TODO: exporter Docstring"""
import asyncio
import logging
import os
from prometheus_client import disable_created_metrics, Counter
from . import collector


class Metrics(object):
    """TODO: Metrics class Docstring"""

    # Offload logging to upstream uvicorn
    logger = logging.getLogger("uvicorn.asgi")

    def __init__(self):
        self.pihole_host = os.getenv("PIHOLE_HOST", "localhost")
        self.pihole_password = os.getenv(
            "PIHOLE_PASSWORD", "correct horse battery staple"
        )
        self.pihole_refresh = (int)(os.getenv("PIHOLE_REFRESH", "5"))
        disable_created_metrics()
        self.queries_count = Counter(
            "pihole_queries_count",
            "Count of queries handled by Pihole",
        )
        self.queries_rich = Counter(
            "pihole_queries",
            "Count of queries handled by Pihole, with labels for query type, status and upstream",
            ["type", "status", "upstream"],
        )
        self.responses_rich = Counter(
            "pihole_responses",
            "Count of responses, with labels for response type",
            ["type"],
        )
        self.clients_rich = Counter(
            "pihole_clients",
            "Count of queries, with labels for client ip and name",
            ["ip", "name"],
        )

        Metrics.logger.info("Setting up Pihole API Bridge")

        try:
            self.collector = collector.Client(
                host=self.pihole_host,
                key=self.pihole_password,
                timeout=(self.pihole_refresh - 1),
            )
        except Exception as e:
            Metrics.logger.error(e)
            raise e

    async def data_loop(self):
        """TODO: data_loop Docstring"""
        Metrics.logger.info("Starting Pihole collection loop")
        while True:
            self.update_results()
            await asyncio.sleep(self.pihole_refresh)

    def update_results(self):
        """Trigger the api calls and return the raw queries since last call"""
        r_queries = self.collector.get_queries(self.pihole_refresh)
        self.queries_count.inc(int(len(r_queries["queries"])))
        for query in r_queries["queries"]:
            self.queries_rich.labels(
                query["type"], query["status"], query["upstream"]
            ).inc()
            self.responses_rich.labels(query["reply"]["type"]).inc()
            self.clients_rich.labels(
                query["client"]["ip"], query["client"]["name"]
            ).inc()

    def close(self):
        """TODO: close Docstring"""
        self.collector.delete_sid()
