from app.services.networks import (
    create_project_network,
    delete_environment_network,
    remove_project_networks,
)


def test_create_project_network(fake_docker):
    network_id = create_project_network("prj_abc", "project_env_x")
    assert network_id is not None
    networks = fake_docker.networks.list(filters={"name": "net-prj_abc-project_env_x"})
    assert len(networks) == 1
    assert networks[0].attrs["Labels"]["dky-project"] == "prj_abc"
    assert networks[0].attrs["Labels"]["is_production"] == "True"


def test_create_project_network_is_idempotent(fake_docker):
    first = create_project_network("prj_abc", "project_env_x")
    second = create_project_network("prj_abc", "project_env_x")
    assert first == second
    assert len(fake_docker.networks.list()) == 1


def test_remove_project_networks(fake_docker):
    create_project_network("prj_abc", "project_env_x")
    removed = remove_project_networks("prj_abc")
    assert removed == ["net-prj_abc-project_env_x"]
    assert len(fake_docker.networks.list()) == 0


def test_delete_environment_network(fake_docker):
    create_project_network("prj_abc", "project_env_x")
    delete_environment_network("project_env_x", "prj_abc")
    assert len(fake_docker.networks.list()) == 0
