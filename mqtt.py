import paho.mqtt.client as mqtt
import paho.mqtt
from config import MqttConfig, NodeConfig, HomeAssistantConfig
from model import Discovery
import logging as log
import asyncio
import time
import json
from hass_formatter import hass_format_config, hass_format_state


class MqttClient:
    def __init__(
        self, cfg: MqttConfig, node_cfg: NodeConfig, hass_cfg: HomeAssistantConfig
    ):
        self.cfg = cfg
        self.node_cfg = node_cfg
        self.hass_cfg = hass_cfg
        self.providers_by_topic = {}

    def start(self):
        try:
            self.event_loop = asyncio.get_event_loop()
            self.client = mqtt.Client(
                client_id="release2mqtt_%s" % self.node_cfg.name, clean_session=True
            )
            self.client.username_pw_set(self.cfg.user, password=self.cfg.password)
            self.client.connect(host=self.cfg.host, port=self.cfg.port, keepalive=60)
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            self.client.loop_start()
            log.info(
                "MQTT Connected to broker at %s:%s" % (self.cfg.host, self.cfg.port)
            )
        except Exception as e:
            log.error(
                "MQTT Failed to connect to broker %s:%s - %s",
                self.cfg.host,
                self.cfg.port,
                e,
            )
            raise EnvironmentError(
                "MQTT Connection Failure to %s:%s as %s -- %s"
                % (self.cfg.host, self.cfg.port, self.cfg.user, e)
            )

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, _client, _userdata, _flags, rc):
        log.info("MQTT Connected to broker with result code " + str(rc))

    def on_disconnect(self, _client, _userdata, rc):
        log.info("MQTT Disconnected from broker with result code " + str(rc))

    async def clean_topics(self, provider, last_scan_session, timeout=30):
        log.info("MQTT-Clean Starting clean cycle")
        cleaner = mqtt.Client(
            client_id="release2mqtt_clean_%s" % self.node_cfg.name, clean_session=True
        )
        cleaner.username_pw_set(self.cfg.user, password=self.cfg.password)
        cleaner.connect(host=self.cfg.host, port=self.cfg.port, keepalive=60)

        def cleanup(_client, _userdata, msg):
            if msg.retain:
                session = None
                try:
                    payload = json.loads(msg.payload)
                    session = payload.get("source_session")
                except Exception as e:
                    log.warn(
                        "MQTT-CLEAN Unable to handle payload for %s: %s",
                        msg.topic,
                        e,
                        exc_info=1,
                    )
                if session is None or session != last_scan_session:
                    log.info("MQTT-CLEAN Removing %s [%s]", msg.topic, session)
                    cleaner.publish(msg.topic, None, retain=False)
                else:
                    log.debug(
                        "MQTT-Clean Retaining topic with current sesssion: %s",
                        msg.topic,
                    )
            else:
                log.debug("MQTT-Clean Skipping clean of %s", msg.topic)

        cleaner.on_message = cleanup
        options = paho.mqtt.subscribeoptions.SubscribeOptions(noLocal=True)
        cleaner.subscribe(
            "%s/update/%s_%s/#"
            % (
                self.hass_cfg.discovery.prefix,
                self.node_cfg.name,
                provider.source_type,
            ),
            options=options
        )
        cleaner.subscribe(
            "%s/%s/%s/#" % (
            self.cfg.topic_root,
            self.node_cfg.name,
            provider.source_type,
            ),
            options=options
        )
        loop_end = time.time() + timeout
        while time.time() <= loop_end:
            cleaner.loop()

        log.info("MQTT-Clean Completed clean cycle")

    async def execute_command(self,msg):
        try:
            log.info('MQTT Execution starting for %s',msg.topic)
            payload = json.loads(msg.payload)
            provider = self.providers_by_topic[msg.topic]
            if provider.source_type != payload['source_type']:
                log.warn('MQTT Unexpected source type %s on %s',payload['source_type'],msg.topic)
            else:
                log.info('MQTT Passing %s command to %s scanner for %s',payload['command'],provider.source_type,payload['name'])
                updated=provider.command(payload['name'],payload['command'])
                if updated:
                    self.publish_hass_state(updated)
                else:
                    log.debug('MQTT No change to republish after execution for %s',msg.topic)
            log.info('MQTT Execution ended for %s',msg.topic)
        except Exception as e:
            log.error('MQTT Execution failed for %s: %s',msg.topic, e, exc_info=1)
        
    def on_message(self, _client, _userdata, msg):
       
        if msg.topic in self.providers_by_topic:
            log.info("MQTT Handling message for %s", msg.topic)
            asyncio.run_coroutine_threadsafe(self.execute_command(msg), self.event_loop)
        else:
            log.warn("MQTT Unhandled message: %s", msg.topic)

    def config_topic(self, discovery, sub_topic=None):
        return "%s/update/%s_%s/%s" % (
            self.hass_cfg.discovery.prefix,
            self.node_cfg.name,
            discovery.source_type,
            discovery.name,
        )

    def state_topic(self, discovery):
        return "%s/%s/%s/%s" % (
            self.cfg.topic_root,
            self.node_cfg.name,
            discovery.source_type,
            discovery.name,
        )

    def command_topic(self, provider):
        return "%s/%s/%s" % (
            self.cfg.topic_root,
            self.node_cfg.name,
            provider.source_type
        )

    def publish_hass_state(self, discovery):
        self.publish(
            self.state_topic(discovery),
            hass_format_state(discovery, self.node_cfg.name, discovery.session),
        )

    def publish_hass_config(self, discovery):
        object_id = "%s_%s_%s" % (
            discovery.source_type,
            self.node_cfg.name,
            discovery.name,
        )
        command_topic = self.command_topic(discovery.provider) if discovery.can_update else None
        self.publish(
            self.config_topic(discovery),
            hass_format_config(
                discovery,
                object_id,
                self.node_cfg.name,
                self.state_topic(discovery),
                command_topic,
                discovery.session,
            ),
        )

    def subscribe_hass_command(self,provider):
        topic=self.command_topic(provider)
        if topic in self.providers_by_topic:
            log.debug("MQTT Skipping subscription for %s", topic)
        else:
            log.info("MQTT Handler subscribing to %s", topic)
            self.providers_by_topic[topic] = provider
            self.client.subscribe(topic)

    def loop_once(self):
        self.client.loop()

    def publish(self, topic, payload):
        self.client.publish(topic, payload=json.dumps(payload), qos=0, retain=True)

