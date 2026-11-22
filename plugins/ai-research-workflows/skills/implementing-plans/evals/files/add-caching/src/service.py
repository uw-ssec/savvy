"""Station lookups, cached in front of the slow catalogue query."""
from src.cache import TTLCache

_cache = TTLCache(maxsize=256, ttl=300.0)


def slow_lookup(station_id):
    """Stand-in for the catalogue query."""
    return {"id": station_id, "name": f"Station {station_id}"}


def get_station(station_id):
    hit = _cache.get(station_id)
    if hit is None:
        hit = slow_lookup(station_id)
        _cache.set(station_id, hit)
    return hit
