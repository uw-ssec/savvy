"""Station lookups; the plan puts a cache in front of slow_lookup()."""


def slow_lookup(station_id):
    return {"id": station_id, "name": f"Station {station_id}"}


def get_station(station_id):
    return slow_lookup(station_id)
