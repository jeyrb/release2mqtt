from pytest_mqtt.model import MqttMessage
import pytest
from model import Discovery
from mqtt import MqttClient, MqttHandler
from config import MqttConfig, HomeAssistantConfig, NodeConfig
from time import sleep
import time


@pytest.mark.capmqtt_decode_utf8
def test_publish(mosquitto,capmqtt):
    config=MqttConfig()
    hass_config=HomeAssistantConfig()
    node_config=NodeConfig()
    uut=MqttClient(config,node_config,hass_config)
    #ßuut.connect()
    uut.publish('test.topic.123',{'foo':'abc','bar':False})
    assert capmqtt.messages == [
        MqttMessage(topic="test.topic.123", payload='{"foo": "abc", "bar": false}', userdata=None),
    ]

@pytest.mark.capmqtt_decode_utf8
@pytest.mark.asyncio
async def test_handler(mosquitto,capmqtt):
    config=MqttConfig()
    hass_config=HomeAssistantConfig()
    node_config=NodeConfig()
    uut=MqttClient(config,node_config,hass_config)
    #uut.connect()
    capture=[]
    def func(user_data,msg,discovery):
        capture.append(msg)
        capture.append(discovery)

    discovery=Discovery('unit_test_fixture','fixture001')
    uut.subscribe('test.status.abc',MqttHandler(discovery))
    capmqtt.publish(topic="test.status.abc", payload="qux")
    uut.loop_once()
    cutoff=time.time()+15
    while time.time()<=cutoff and len(capture)<2:
        sleep(0.2)
    assert capture[1]['src']==123
    assert capture[0].payload==b'qux'