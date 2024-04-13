from abc import abstractmethod
from collections.abc import AsyncGenerator, Callable


class Discovery:
    """Discovered component from a scan"""

    def __init__(
        self,
        provider: "ReleaseProvider",
        name: str,
        session: str,
        entity_picture_url: str | None = None,
        current_version: str | None = None,
        latest_version: str | None = None,
        can_update: bool = False,
        status="on",
        update_policy=None,
        update_last_attempt=None,
        release_url: str | None = None,
        release_summary: str | None = None,
        title_template: str = "Update for {name} on {node}",
        device_icon: str | None = None,
        custom=None,
    ):
        self.provider = provider
        self.source_type = provider.source_type
        self.session = session
        self.name = name
        self.entity_picture_url = entity_picture_url
        self.current_version = current_version
        self.latest_version = latest_version
        self.can_update = can_update
        self.release_url = release_url
        self.release_summary = release_summary
        self.title_template = title_template
        self.device_icon = device_icon
        self.status = status
        self.update_policy = update_policy
        self.update_last_attempt = update_last_attempt
        self.custom = custom or {}

    def __repr__(self) -> str:
        """Custom string representation"""
        return f"Discovery('{self.name}','{self.source_type}')"


class ReleaseProvider:
    source_type = "base"

    def update(self, discovery: Discovery) -> bool:
        _ = discovery
        return False

    def rescan(self, discovery: Discovery) -> Discovery | None:
        pass

    @abstractmethod
    async def scan(self, session: str) -> AsyncGenerator[Discovery, None]:
        """Scan for components to monitor"""

    def hass_config_format(self, discovery: Discovery):
        _ = discovery
        return {}

    def hass_state_format(self, discovery: Discovery):
        _ = discovery
        return {}

    @abstractmethod
    def command(self, discovery_name: str, command: str, on_update_start: Callable, on_update_end: Callable) -> bool:
        """Execute a command on a discovered component"""
