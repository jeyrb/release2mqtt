import pytest

import release2mqtt.integrations.docker as mut
from release2mqtt.model import Discovery


@pytest.mark.asyncio
async def test_scanner(mocker, mock_docker_client):
    mocker.patch("docker.from_env", return_value=mock_docker_client)
    uut = mut.DockerProvider(mut.DockerConfig(), mut.UpdateInfoConfig())
    session = "unit_123"
    results = [d async for d in uut.scan(session)]

    unchanged = [d for d in results if d.current_version == d.latest_version]
    assert len(unchanged) == 1
    assert unchanged[0].entity_picture_url == "https://piccy"
    assert unchanged[0].release_url == "https://release"
    assert unchanged[0].custom["platform"] == "linux/amd64"
    changed = [d for d in results if d.current_version != d.latest_version]
    assert len(changed) == 2


async def test_build(mocker, mock_docker_client, fake_process):
    mocker.patch("docker.from_env", return_value=mock_docker_client)

    uut = mut.DockerProvider(mut.DockerConfig(), mut.UpdateInfoConfig())
    d = Discovery(uut, "build-test-dummy", session="test-123")
    fake_process.register("docker-compose build", returncode=0)
    assert uut.build(d, "build-test-dc-path")
    fake_process.register("docker-compose build", returncode=33)
    assert not uut.build(d, "build-test-dc-path")
