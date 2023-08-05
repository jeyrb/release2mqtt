import paho.mqtt.client as mqtt
from config import MqttConfig, NodeConfig, HomeAssistantConfig
import logging as log
import aiomqtt
import json
from hass_formatter import hass_format_config,hass_state_config

class MqttClient:
    def __init__(self,cfg: MqttConfig, node_cfg: NodeConfig, hass_cfg: HomeAssistantConfig):
        self.cfg=cfg
        self.node_cfg = node_cfg
        self.hass_cfg = hass_cfg
        self.topic_handlers = {}
    
    async def start(self):  
        try:
            self.client=aiomqtt.Client(hostname=self.cfg.host,
                                         port=self.cfg.port,
                                         username=self.cfg.user,
                                         password=self.cfg.password,
                                         client_id='release2mqtt',
                                         keepalive=60,
                                         clean_session=True)
            # context manager has naive expectations of mqtt pub/sub
            # so to use same client in multiple places manually set it up
            await self.client.__aenter__()

            log.info("MQTT Connected to broker at %s:%s" % (self.cfg.host, self.cfg.port))
        except Exception as e:
            log.error("MQTT Failed to connect to broker %s:%s - %s", self.cfg.host, self.cfg.port, e)
            raise EnvironmentError("MQTT Connection Failure to %s:%s as %s -- %s" % ( self.cfg.host,self.cfg.port,self.cfg.user,e))
    
    async def stop(self):
        self.client.__aexit__()
        
    def on_connect(self, _client, _userdata, _flags, rc):
        log.info("MQTT Connected to broker with result code " + str(rc))
        
    def on_message(self,msg):
        if msg.topic.value in self.topic_handlers:
            log.info('MQTT Handling message for %s',msg.topic)
            handler=self.topic_handlers[msg.topic.value]
            try:
                handler.handle(msg)
            except Exception as e:
                log.error('MQTT failed handling %s: %s',msg.topic,e)
        else:
            log.warn('MQTT Unhandled message: %s',msg.topic)
        
    async def subscribe(self,topic,handler):
        log.info('MQTT Handler subscribing to %s',topic)
        self.topic_handlers[topic]=handler
        await self.client.subscribe(topic)
        
    async def listen(self):
        log.info('MQTT listening for subscribed messages')
        async with self.client.messages() as messages:   
            async for msg in messages:
                log.info('MQTT message received on %s',msg.topic)
                self.on_message(msg) 
        log.info('MQTT terminated listening for subscribed messages')          
    
    def base_topic(self):
        return '%s/update/%s' % ( self.hass_cfg.discovery.prefix,
                                  self.node_cfg.name)
    def command_topic(self,discovery):
        return '%s_%s/%s/command' % ( self.base_topic(),discovery.source_type,
                                      discovery.name )       
    def config_topic(self,discovery):
        return '%s_%s/%s/config' % ( self.base_topic(),discovery.source_type,
                                     discovery.name )
          
    def state_topic(self,discovery):
        return '%s_%s/%s/%s' % ( self.base_topic(),discovery.source_type,
                                discovery.name,
                                self.hass_cfg.state_topic_suffix )
        
    async def publish_hass_state(self,discovery):
        await self.publish(self.state_topic(discovery),
                           hass_state_config(discovery,self.node_cfg.name))
        
    async def publish_hass_config(self,discovery,commandable=True):
        object_id='%s_%s_%s' % ( discovery.source_type,self.node_cfg.name,discovery.name)
        command_topic = self.command_topic(discovery) if commandable else None
        await self.publish(self.config_topic(discovery),
                           hass_format_config(discovery,object_id,
                                              self.node_cfg.name,
                                              self.state_topic(discovery),
                                              command_topic))
    async def subscribe_hass_command(self,discovery):
        await self.subscribe(self.command_topic(discovery),MqttHandler(discovery))
               
               
        
    def wait(self):
        log.info('MQTT Starting event loop')
        self.client.loop_forever()
        log.info('MQTT Ended event loop')
        
    def loop_once(self):
        self.client.loop()
        
    async def publish(self,topic,payload):
        await self.client.publish(topic, payload=json.dumps(payload), qos=0, retain=True)

class MqttHandler:
    def __init__(self,discovery):
        self.discovery=discovery
    def handle(self,msg):
        try:
            if self.discovery.fetcher:
                log.info('MQTT-Handler Starting %s fetch ...',self.discovery.name)
                self.discovery.fetcher.fetch(msg.payload)
            if self.discovery.restarter:
                log.info('MQTT-Handler Restarting %s ...',self.discovery.name)
                if self.discovery.restarter.restart(msg.payload):
                    if self.discovery.rescanner:
                        log.info('MQTT-Handler Rescanning %s ...',self.discovery.name)
                        self.discovery.rescanner.rescan(self.discovery.name)
        except Exception as e:
            log.error('MQTT-Handler Failed to handle %s: %s', msg,e)


