from pytest_mqtt.model import MqttMessage
import pytest
from model import ReleaseProvider, Discovery
from mqtt import MqttClient
from config import MqttConfig, HomeAssistantConfig, NodeConfig
import time
import asyncio


@pytest.mark.capmqtt_decode_utf8
def test_publish(mocker, mosquitto, capmqtt):
    config = MqttConfig()
    hass_config = HomeAssistantConfig()
    node_config = NodeConfig()
    config.host, config.port = mosquitto
    uut = MqttClient(config, node_config, hass_config)
    uut.start()

    uut.publish("test.topic.123", {"foo": "abc", "bar": False})
    assert (
        MqttMessage(
            topic="test.topic.123",
            payload='{"foo": "abc", "bar": false}',
            userdata=None,
        )
        in capmqtt.messages
    )


@pytest.mark.capmqtt_decode_utf8
@pytest.mark.asyncio
async def test_handler(mocker, mosquitto, event_loop):
    config = MqttConfig()
    hass_config = HomeAssistantConfig()
    node_config = NodeConfig()
    node_config.name = "testing"
    config.host, config.port = mosquitto
    uut = MqttClient(config, node_config, hass_config)
    uut.start(event_loop=event_loop)

    provider = mocker.Mock(spec=ReleaseProvider)
    provider.source_type = "unit_test"
    discovery = Discovery(provider, "qux")
    provider.command.return_value = discovery
    provider.hass_state_format.return_value = {}

    payload = {"source_type": provider.source_type, "name": "qux", "command": "install"}
    topic_name = uut.subscribe_hass_command(provider)
    uut.publish(
        topic=topic_name,
        payload=payload
    )

    cutoff = time.time() + 10
    while time.time() <= cutoff and not provider.command.called:
        await asyncio.sleep(0.5)
        
    provider.command.assert_called_with("qux", "install", mocker.ANY, mocker.ANY)
