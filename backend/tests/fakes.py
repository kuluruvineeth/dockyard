class FakeContainers:
    def run(self, image, command, remove=False, **kwargs):
        return b"4\n8589934592"


class FakeImages:
    def search(self, term, limit=30):
        return [
            {"name": "caddy", "description": "Caddy web server"},
            {"name": "siwecos/caddy", "description": "Caddy with security headers"},
        ]


class FakeNetwork:
    def __init__(self, network_id, name, labels):
        self.id = network_id
        self.name = name
        self.attrs = {"Labels": labels or {}}
        self.removed = False

    def remove(self):
        self.removed = True


class FakeNetworks:
    def __init__(self):
        self._networks: list[FakeNetwork] = []
        self._counter = 0

    def create(self, name, labels=None, **kwargs):
        self._counter += 1
        network = FakeNetwork(f"net_{self._counter}", name, labels)
        self._networks.append(network)
        return network

    def list(self, filters=None):
        live = [n for n in self._networks if not n.removed]
        if not filters:
            return live
        if "name" in filters:
            return [n for n in live if n.name == filters["name"]]
        if "label" in filters:
            key, _, value = filters["label"].partition("=")
            return [
                n
                for n in live
                if n.attrs["Labels"].get(key) == value
                or (value == "" and key in n.attrs["Labels"])
            ]
        return live

    def prune(self, filters=None):
        return {"NetworksDeleted": []}


class FakeDockerClient:
    def __init__(self):
        self.containers = FakeContainers()
        self.images = FakeImages()
        self.networks = FakeNetworks()
