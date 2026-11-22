"""Nightly catalogue sync; every call goes through JsonClient."""
from src.clients.http import JsonClient


def sync_stations(client: JsonClient):
    stations = client.get("/v1/stations")
    for station in stations:
        client.post("/v1/mirror", station)
    return len(stations)
