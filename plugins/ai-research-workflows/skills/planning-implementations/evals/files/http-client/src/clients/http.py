"""Thin JSON client over http.client used by the catalogue sync."""
import http.client
import json


class HttpError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}")
        self.status, self.body = status, body


class JsonClient:
    def __init__(self, host, timeout=10.0, connection_factory=http.client.HTTPSConnection):
        self.host = host
        self.timeout = timeout
        self._connect = connection_factory

    def request(self, method, path, payload=None):
        """Send one request and return the decoded JSON body; raise HttpError on a non-2xx status."""
        conn = self._connect(self.host, timeout=self.timeout)
        try:
            body = json.dumps(payload) if payload is not None else None
            conn.request(method, path, body=body, headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            data = resp.read()
        finally:
            conn.close()
        if not 200 <= resp.status < 300:
            raise HttpError(resp.status, data)
        return json.loads(data) if data else None

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, payload):
        return self.request("POST", path, payload)
