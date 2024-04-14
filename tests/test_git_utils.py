import datetime
from pathlib import Path

from pytest_subprocess import FakeProcess  # type: ignore[import-not-found]

from release2mqtt.integrations.git_utils import git_timestamp, git_trust


def test_git_timestamp(fake_process: FakeProcess) -> None:
    fake_process.register([fake_process.any()], stdout="""2024-04-12T00:16:33+01:00""")
    assert git_timestamp(Path("/my/path")) == datetime.datetime(
        2024,
        4,
        12,
        0,
        16,
        33,
        0,
        datetime.timezone(offset=datetime.timedelta(hours=1)),
    )


def test_git_trust(fake_process: FakeProcess) -> None:
    fake_process.register("git config --global --add safe.directory /my/path", returncode=0)
    assert git_trust(Path("/my/path"))
