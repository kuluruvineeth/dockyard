from app.docker_helpers import (
    get_config_resource_name,
    get_env_network_resource_name,
    get_network_resource_name,
    get_resource_labels,
    get_swarm_service_name_for_deployment,
    get_volume_resource_name,
)


def test_network_resource_name():
    assert get_network_resource_name("prj_abc") == "net-prj_abc"


def test_env_network_resource_name():
    assert (
        get_env_network_resource_name("project_env_x", "prj_abc")
        == "net-prj_abc-project_env_x"
    )


def test_resource_labels():
    labels = get_resource_labels("prj_abc", is_production="True")
    assert labels == {
        "dky-managed": "true",
        "dky-project": "prj_abc",
        "is_production": "True",
    }


def test_volume_resource_name():
    assert get_volume_resource_name("vol_x") == "vol-vol_x"


def test_config_resource_name():
    assert get_config_resource_name("cf_x", 2) == "cf-cf_x-2"


def test_swarm_service_name_for_deployment():
    assert (
        get_swarm_service_name_for_deployment("dpl_hash", "prj_abc", "srv_dkr_x")
        == "srv-prj_abc-srv_dkr_x-dpl_hash"
    )
