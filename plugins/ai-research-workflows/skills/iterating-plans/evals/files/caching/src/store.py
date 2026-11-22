"""Write-behind store in front of the results database."""


class Store:
    def __init__(self, db):
        self.db = db
        self.cache = {}

    def get(self, key):
        if key not in self.cache:
            self.cache[key] = self.db.read(key)
        return self.cache[key]

    def put(self, key, value):
        self.cache[key] = value
        self.db.write(key, value)
