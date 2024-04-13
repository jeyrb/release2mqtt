from unittest.mock import MagicMock, Mock

import paho.mqtt.client
import pytest
from docker import DockerClient  # type: ignore
from docker.models.containers import Container, ContainerCollection  # type: ignore
from docker.models.images import Image, RegistryData  # type: ignore


@pytest.fixture
def mock_mqtt_client() -> Mock:
    mock = MagicMock(spec=paho.mqtt.client.Client, name="MQTT Client Fixture")
    return mock


@pytest.fixture
def mock_docker_client(mocker) -> Mock:
    client = mocker.Mock(spec=DockerClient)
    coll = mocker.Mock(spec=ContainerCollection)

    def reg_data_select(v):
        reg_data = mocker.Mock(spec=RegistryData)
        match v:
            case "testy/mctest:latest":
                reg_data.short_id = "sha256:c5385387575"
            case "testy/mctest":
                reg_data.short_id = "sha256:9e2bbca07938"
            case "ubuntu":
                reg_data.short_id = "sha256:85a5385853bd"
            case _:
                reg_data.short_id = "sha256:999999999999"
        return reg_data

    client.images.get_registry_data = mocker.Mock(side_effect=reg_data_select)

    client.containers = coll
    coll.list.return_value = [
        build_mock_container(mocker, "testy/mctest:latest", opsys="macos"),
        build_mock_container(mocker, "ubuntu"),
        build_mock_container(
            mocker,
            "testy/mctest",
            picture="https://piccy",
            relnotes="https://release",
            arch="amd64",
        ),
    ]
    mocker.patch("docker.from_env", return_value=client)
    return client


def build_mock_container(mocker, tag, picture=None, relnotes=None, opsys="linux", arch="arm64"):
    c = mocker.Mock(spec=Container)
    c.image = mocker.Mock(spec=Image)
    c.image.tags = [tag]
    c.image.attrs = {}
    c.image.attrs["Os"] = opsys
    c.image.attrs["Architecture"] = arch
    bare_tag = tag.split(":")[0]
    long_hash = "9e2bbca079387d7965c3a9cee6d0c53f4f4e63ff7637877a83c4c05f2a666112"
    c.image.attrs["RepoDigests"] = [f"{bare_tag}@sha256:{long_hash}"]
    c.attrs = {}
    c.attrs["Config"] = {}
    c.attrs["Config"]["Env"] = []
    if picture:
        c.attrs["Config"]["Env"].append(f"REL2MQTT_PICTURE={picture}")
    if relnotes:
        c.attrs["Config"]["Env"].append(f"REL2MQTT_RELNOTES={relnotes}")
    return c
