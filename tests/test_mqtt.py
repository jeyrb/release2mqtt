import asyncio
import json
import time
from collections.abc import Iterator
from unittest import mock
from unittest.mock import Mock, patch

import paho.mqtt.client
import pytest

from release2mqtt.config import HomeAssistantConfig, MqttConfig, NodeConfig
from release2mqtt.model import Discovery, ReleaseProvider
from release2mqtt.mqtt import MqttClient


async def test_publish(mock_mqtt_client: Mock):
    config = MqttConfig()
    hass_config = HomeAssistantConfig()
    node_config = NodeConfig()

    with patch.object(paho.mqtt.client.Client, "__new__", lambda *args, **kwargs: mock_mqtt_client):
        uut = MqttClient(config, node_config, hass_config)
        uut.start()

        uut.publish("test.topic.123", {"foo": "a8", "bar": False})
        mock_mqtt_client.connect.assert_called_once()
        mock_mqtt_client.publish.assert_called_with("test.topic.123", payload='{"foo": "a8", "bar": false}', qos=0, retain=True)


@pytest.mark.asyncio
async def test_handler(
    mock_mqtt_client: Mock,
    event_loop: Iterator[asyncio.AbstractEventLoop],
):
    config = MqttConfig()
    hass_config = HomeAssistantConfig()
    node_config = NodeConfig()
    node_config.name = "testing"
    with patch("release2mqtt.mqtt.mqtt.Client", new=mock_mqtt_client):
        uut = MqttClient(config, node_config, hass_config)
        uut.start(event_loop=event_loop)

        provider = Mock(spec=ReleaseProvider)
        provider.source_type = "unit_test"
        discovery = Discovery(provider, "qux", session="test-mqtt-123")
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

        provider.command.assert_called_with("qux", "install", mock.ANY, mock.ANY)
