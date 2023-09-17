import integrations.docker as mut
from docker import DockerClient
from docker.models.containers import Container, ContainerCollection
from docker.models.images import Image, RegistryData
import pytest


@pytest.mark.asyncio
async def test_scanner(mocker):
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
    uut = mut.DockerProvider(mut.DockerConfig(),mut.UpdateInfoConfig())
    session='unit_123'
    results = [d async for d in uut.scan(session)]

    unchanged = [d for d in results if d.current_version == d.latest_version]
    assert len(unchanged) == 1
    assert unchanged[0].entity_picture_url == "https://piccy"
    assert unchanged[0].release_url == "https://release"
    assert unchanged[0].custom["platform"] == "linux/amd64"
    changed = [d for d in results if d.current_version != d.latest_version]
    assert len(changed) == 2


def build_mock_container(
    mocker, tag, picture=None, relnotes=None, opsys="linux", arch="arm64"
):
    c = mocker.Mock(spec=Container)
    c.image = mocker.Mock(spec=Image)
    c.image.tags = [tag]
    c.image.attrs = {}
    c.image.attrs["Os"] = opsys
    c.image.attrs["Architecture"] = arch
    bare_tag = tag.split(":")[0]
    long_hash = "9e2bbca079387d7965c3a9cee6d0c53f4f4e63ff7637877a83c4c05f2a666112"
    c.image.attrs["RepoDigests"] = ["%s@sha256:%s" % (bare_tag, long_hash)]
    c.attrs = {}
    c.attrs["Config"] = {}
    c.attrs["Config"]["Env"] = []
    if picture:
        c.attrs["Config"]["Env"].append("REL2MQTT_PICTURE=%s" % picture)
    if relnotes:
        c.attrs["Config"]["Env"].append("REL2MQTT_RELNOTES=%s" % relnotes)
    return c
