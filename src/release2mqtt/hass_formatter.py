from typing import Any

from release2mqtt.model import Discovery


def hass_format_config(
    discovery: Discovery, object_id: str, node_name: str, state_topic: str, command_topic: str | None, session: str
) -> dict[str, Any]:
    config = {
        "name": f"{discovery.name} {discovery.source_type} on {node_name}",
        "device_class": None,  # not firmware, so defaults to null
        "unique_id": object_id,
        "state_topic": state_topic,
        "source_session": session,
        "supported_features": discovery.features,
        "entity_picture": discovery.entity_picture_url,
        "icon": discovery.device_icon,
        "can_update": discovery.can_update,
        "update_policy": discovery.update_policy,
        "latest_version_topic": state_topic,
        "latest_version_template": "{{value_json.latest_version}}",
    }
    if command_topic:
        config["command_topic"] = command_topic
        config["payload_install"] = f"{discovery.source_type}|{discovery.name}|install"
    config.update(discovery.provider.hass_config_format(discovery))
    return config


def hass_format_state(discovery: Discovery, node_name: str, session: str, in_progress: bool = False) -> dict[str, Any]:  # noqa: ARG001
    title: str = (
        discovery.title_template.format(name=discovery.name, node=node_name) if discovery.title_template else discovery.name
    )
    state = {
        "installed_version": discovery.current_version,
        "latest_version": discovery.latest_version,
        "title": title,
    }
    if discovery.release_summary:
        state["release_summary"] = discovery.release_summary
    if discovery.release_url:
        state["release_url"] = discovery.release_url
    # custom_state = discovery.provider.hass_state_format(discovery)
    # if custom_state:
    #    state.update(custom_state)
    return state
