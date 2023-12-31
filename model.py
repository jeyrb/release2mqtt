class Discovery:
    """Discovered component from a scan"""

    def __init__(
        self,
        provider,
        name,
        session=None,
        entity_picture_url=None,
        current_version=None,
        latest_version=None,
        can_update=False,
        status="on",
        update_policy=None,
        update_last_attempt=None,
        release_url=None,
        release_summary=None,
        title_template="Update for {name} on {node}",
        device_icon=None,
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
        
    def __repr__(self):
        return f'Discovery(\'{self.name}\',\'{self.source_type}\')'


class ReleaseProvider:
    source_type = "base"

    def update(self, command, discovery):
        pass

    def rescan(self, discovery):
        pass

    def scan(self, session):
        pass

    def hass_config_format(self, discovery):
        return {}

    def hass_state_format(self, discovery):
        return {}

    def command(self, payload):
        pass
