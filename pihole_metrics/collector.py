# collector.py
"""TODO: collector Docstring"""
import logging
from datetime import datetime
import requests
import urllib3


class Client(object):
    """TODO: Client class Docstring"""

    # Offload logging to upstream uvicorn
    logger = logging.getLogger("uvicorn.asgi")

    def __init__(self, host="localhost", key=None, timeout=2):
        self.using_auth = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.host = host
        self.last_stamp = 0
        self.timeout = timeout
        if key is not None:
            self.using_auth = True
            self.sid = self.get_sid(key)

    def get_sid(self, key):
        """Authenticate and retrieve the SID from Pihole"""
        auth_url = "https://" + self.host + ":443/api/auth"
        headers = {"accept": "application/json", "content_type": "application/json"}
        json_data = {"password": key}
        try:
            Client.logger.debug("POST %s", auth_url)
            req = requests.post(
                auth_url,
                verify=False,
                headers=headers,
                json=json_data,
                timeout=self.timeout,
            )
        except requests.exceptions.ConnectTimeout as e:
            raise ConnectionError(
                f"ConnectTimeoutError {e.request.url} - {e.args[0].reason.args[1]}"
            ) from e
        if req.status_code == 401:
            raise PermissionError("401 %s %s" % (req.reason, req.content))
        elif req.status_code == 200:
            self.logger.info("200 - SID retrieved successfully from Pihole")
            return req.json()["session"]["sid"]
        else:
            raise SystemError(
                f"Response Status Code: {req.status_code} {req.reason} {req.content}"
            )

    def delete_sid(self):
        """Cleanup the connection with Pihole by deleting the SID"""
        url = "https://" + self.host + ":443/api/auth?sid=" + self.sid
        headers = {"accept": "application/json", "sid": self.sid}
        Client.logger.debug("DELETE %s", url)
        return requests.delete(url, verify=False, headers=headers, timeout=self.timeout)

    def get_api_call(self, api_path):
        """Perform a GET API Call"""
        url = "https://" + self.host + ":443/api/" + api_path
        if self.using_auth:
            headers = {"accept": "application/json", "sid": self.sid}
        else:
            headers = {"accept": "application/json"}
        Client.logger.debug("GET %s", url)
        req = requests.get(url, verify=False, headers=headers, timeout=self.timeout)
        return req.json()

    def get_queries(self, period=15):
        """Retrieve all of the queries from the last <period> seconds"""
        now_stamp = int(datetime.now().timestamp() // 1)
        if self.last_stamp == 0:
            self.last_stamp = now_stamp - period
        reply = self.get_api_call(
            "queries?from="
            + str(self.last_stamp)
            + "&until="
            + str(now_stamp)
            + "&length=1000000"
        )
        Client.logger.debug(
            "Retrieved %s queries from %s to %s",
            len(reply["queries"]),
            datetime.fromtimestamp(self.last_stamp),
            datetime.fromtimestamp(now_stamp),
        )
        self.last_stamp = now_stamp
        return reply
