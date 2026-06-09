import docker.errors

NONEXISTANT_IMAGE = "nonexistent/donotexist:latest"


class FakeContainer:
    def stats(self, stream=False):
        return {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 2_000_000, "percpu_usage": [1, 1]},
                "system_cpu_usage": 10_000_000,
                "online_cpus": 2,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 1_000_000},
                "system_cpu_usage": 5_000_000,
            },
            "memory_stats": {"usage": 52_428_800},
            "networks": {"eth0": {"rx_bytes": 1000, "tx_bytes": 2000}},
            "blkio_stats": {
                "io_service_bytes_recursive": [
                    {"op": "Read", "value": 4096},
                    {"op": "Write", "value": 8192},
                ]
            },
        }


class FakeContainers:
    def run(self, image, command, remove=False, **kwargs):
        return b"4\n8589934592"

    def list(self, filters=None, **kwargs):
        return [FakeContainer()]


class FakeImages:
    def __init__(self):
        self.pulled = []

    def pull(self, image, auth_config=None, **kwargs):
        self.pulled.append({"image": image, "auth_config": auth_config})
        return image

    def search(self, term, limit=30):
        return [
            {"name": "caddy", "description": "Caddy web server"},
            {"name": "siwecos/caddy", "description": "Caddy with security headers"},
        ]

    def get_registry_data(self, image, auth_config=None):
        if image == NONEXISTANT_IMAGE:
            raise docker.errors.ImageNotFound("This image does not exist")
        return {"name": image}


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


class FakeSwarmService:
    # set False on the class to simulate a replica that never reaches "running"
    running = True

    def __init__(self, service_id, name, image, labels, env=None, resources=None):
        self.id = service_id
        self.name = name
        self.image = image
        self.env = env or []
        self.resources = resources
        self.attrs = {"Spec": {"Labels": labels or {}}}
        self.removed = False

    def tasks(self, filters=None):
        state = "running" if FakeSwarmService.running else "starting"
        return [{"Status": {"State": state}}]

    def scale(self, replicas):
        self.replicas = replicas

    def logs(self, **kwargs):
        return [
            b"2026-06-09T10:00:00 starting service\n",
            b"2026-06-09T10:00:01 listening on :3000\n",
        ]

    def remove(self):
        self.removed = True


class FakeServices:
    def __init__(self):
        self._services: dict[str, FakeSwarmService] = {}
        self._counter = 0

    def create(self, image, name, labels=None, env=None, resources=None, **kwargs):
        self._counter += 1
        service = FakeSwarmService(
            f"swarm_{self._counter}", name, image, labels, env, resources
        )
        self._services[name] = service
        return service

    def get(self, name):
        if name not in self._services:
            raise docker.errors.NotFound(f"service {name} not found")
        return self._services[name]

    def list(self, filters=None):
        live = [s for s in self._services.values() if not s.removed]
        if filters and "name" in filters:
            return [s for s in live if s.name == filters["name"]]
        return live


class FakeResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


class FakeCaddyClient:
    ROUTES_SUFFIX = "/handle/0/routes"

    def __init__(self):
        self.domains: dict[str, dict] = {}

    def get(self, path):
        if path.endswith(self.ROUTES_SUFFIX):
            domain = path[len("/id/") : -len(self.ROUTES_SUFFIX)]
            domain_route = self.domains.get(domain)
            routes = domain_route["handle"][0]["routes"] if domain_route else []
            return FakeResponse(200, routes)
        if path.startswith("/id/"):
            domain = path[len("/id/") :]
            if domain in self.domains:
                return FakeResponse(200, self.domains[domain])
            return FakeResponse(404, None)
        return FakeResponse(404, None)

    def post(self, path, json):
        self.domains[json["@id"]] = json
        return FakeResponse(200, json)

    def put(self, path, json):
        self.domains[json["@id"]] = json
        return FakeResponse(200, json)

    def patch(self, path, json):
        domain = path[len("/id/") : -len(self.ROUTES_SUFFIX)]
        if domain in self.domains:
            self.domains[domain]["handle"][0]["routes"] = json
        return FakeResponse(200, json)

    def delete(self, path):
        route_id = path[len("/id/") :]
        if route_id in self.domains:
            del self.domains[route_id]
        for domain_route in self.domains.values():
            routes = domain_route["handle"][0]["routes"]
            domain_route["handle"][0]["routes"] = [
                r for r in routes if r["@id"] != route_id
            ]
        return FakeResponse(200, None)


class FakeVolume:
    def __init__(self, name, labels):
        self.name = name
        self.attrs = {"Labels": labels or {}}
        self.removed = False

    def remove(self, force=False):
        self.removed = True


class FakeVolumes:
    def __init__(self):
        self._volumes: dict[str, FakeVolume] = {}

    def create(self, name, driver=None, labels=None, **kwargs):
        volume = FakeVolume(name, labels)
        self._volumes[name] = volume
        return volume

    def get(self, name):
        if name not in self._volumes or self._volumes[name].removed:
            raise docker.errors.NotFound(f"volume {name} not found")
        return self._volumes[name]

    def list(self, filters=None):
        live = [v for v in self._volumes.values() if not v.removed]
        if filters and "label" in filters:
            labels = filters["label"]
            labels = labels if isinstance(labels, list) else [labels]
            for label in labels:
                key, _, value = label.partition("=")
                live = [v for v in live if v.attrs["Labels"].get(key) == value]
        return live


class FakeConfig:
    def __init__(self, config_id, name, labels, data):
        self.id = config_id
        self.name = name
        self.attrs = {"Spec": {"Labels": labels or {}}}
        self.data = data
        self.removed = False

    def remove(self):
        self.removed = True


class FakeConfigs:
    def __init__(self):
        self._configs: dict[str, FakeConfig] = {}
        self._counter = 0

    def create(self, name, data=None, labels=None, **kwargs):
        self._counter += 1
        config = FakeConfig(f"cfg_{self._counter}", name, labels, data)
        self._configs[name] = config
        return config

    def get(self, name):
        if name not in self._configs or self._configs[name].removed:
            raise docker.errors.NotFound(f"config {name} not found")
        return self._configs[name]

    def list(self, filters=None):
        return [c for c in self._configs.values() if not c.removed]


class FakeDockerClient:
    NONEXISTANT_IMAGE = NONEXISTANT_IMAGE

    def __init__(self):
        self.containers = FakeContainers()
        self.images = FakeImages()
        self.networks = FakeNetworks()
        self.services = FakeServices()
        self.volumes = FakeVolumes()
        self.configs = FakeConfigs()
