from unittest.mock import patch

import pytest
from docker import DockerClient  # type:ignore[import-not-found]
from pytest_subprocess import FakeProcess  # type: ignore[import-not-found]

import release2mqtt.integrations.docker as mut
from release2mqtt.model import Discovery


@pytest.mark.asyncio
async def test_scanner(mock_docker_client: DockerClient) -> None:
    with patch("docker.from_env", return_value=mock_docker_client):
        uut = mut.DockerProvider(mut.DockerConfig(), mut.UpdateInfoConfig())
        session = "unit_123"
        results: list[Discovery] = [d async for d in uut.scan(session)]

    unchanged: list[Discovery] = [d for d in results if d.current_version == d.latest_version]
    assert len(unchanged) == 1
    assert unchanged[0].entity_picture_url == "https://piccy"
    assert unchanged[0].release_url == "https://release"
    assert unchanged[0].custom["platform"] == "linux/amd64"
    changed = [d for d in results if d.current_version != d.latest_version]
    assert len(changed) == 2


def test_build(mock_docker_client: DockerClient, fake_process: FakeProcess) -> None:
    with patch("docker.from_env", return_value=mock_docker_client):
        uut = mut.DockerProvider(mut.DockerConfig(), mut.UpdateInfoConfig())
        d = Discovery(uut, "build-test-dummy", session="test-123")
        fake_process.register("docker-compose build", returncode=0)
        assert uut.build(d, "build-test-dc-path")
        fake_process.register("docker-compose build", returncode=33)
        assert not uut.build(d, "build-test-dc-path")
