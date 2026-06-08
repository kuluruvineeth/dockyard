class FakeContainers:
    def run(self, image, command, remove=False, **kwargs):
        return b"4\n8589934592"


class FakeImages:
    def search(self, term, limit=30):
        return [
            {"name": "caddy", "description": "Caddy web server"},
            {"name": "siwecos/caddy", "description": "Caddy with security headers"},
        ]


class FakeDockerClient:
    def __init__(self):
        self.containers = FakeContainers()
        self.images = FakeImages()
