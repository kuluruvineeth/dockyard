class FakeContainers:
    def run(self, image, command, remove=False, **kwargs):
        return b"4\n8589934592"


class FakeDockerClient:
    def __init__(self):
        self.containers = FakeContainers()
