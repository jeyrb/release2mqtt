import asyncio
import json
import time
from unittest.mock import Mock, patch

import pytest

from release2mqtt.config import HomeAssistantConfig, MqttConfig, NodeConfig
from release2mqtt.model import Discovery, ReleaseProvider
from release2mqtt.mqtt import MqttClient


async def test_publish(mocker, mock_mqtt_client):
    config = MqttConfig()
    hass_config = HomeAssistantConfig()
    node_config = NodeConfig()

    with patch("release2mqtt.mqtt.mqtt.Client", new=mock_mqtt_client):
        uut = MqttClient(config, node_config, hass_config)
        uut.start()

        uut.publish("test.topic.123", {"foo": "abc", "bar": False})
        uut.client.connect.assert_called_once()
        uut.client.publish.assert_called_with("test.topic.123", payload='{"foo": "abc", "bar": false}', qos=0, retain=True)


@pytest.mark.asyncio
async def test_handler(mocker, mock_mqtt_client, event_loop):
    config = MqttConfig()
    hass_config = HomeAssistantConfig()
    node_config = NodeConfig()
    node_config.name = "testing"
    with patch("release2mqtt.mqtt.mqtt.Client", new=mock_mqtt_client):
        uut = MqttClient(config, node_config, hass_config)
        uut.start(event_loop=event_loop)

        provider = mocker.Mock(spec=ReleaseProvider)
        provider.source_type = "unit_test"
        discovery = Discovery(provider, "qux")
        provider.command.return_value = discovery
        provider.hass_state_format.return_value = {}

        topic_name = uut.subscribe_hass_command(provider)
        payload = {"source_type": provider.source_type, "name": "qux", "command": "install"}
        mock_message = Mock()
        mock_message.topic = topic_name
        mock_message.payload = json.dumps(payload)
        uut.on_message(None, None, mock_message)

        cutoff = time.time() + 10
        while time.time() <= cutoff and not provider.command.called:
            await asyncio.sleep(0.5)

        provider.command.assert_called_with("qux", "install", mocker.ANY, mocker.ANY)
