import paho.mqtt.client as mqtt
import json
from config import MqttConfig
import logging as log
import aiomqtt
import math

class MqttClient:
    def __init__(self,cfg: MqttConfig):
        self.cfg=cfg
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
            #self.client.on_connect = self.on_connect
            #self.client.on_message = self.on_message
            #self.client.username_pw_set(username=self.cfg.user,password=self.cfg.password)
            #self.client.connect(self.cfg.host, int(self.cfg.port), 60)
            #self.client.loop_start()
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
                
        
    def wait(self):
        log.info('MQTT Starting event loop')
        self.client.loop_forever()
        log.info('MQTT Ended event loop')
        
    def loop_once(self):
        self.client.loop()
        
    async def publish(self,topic,payload):
        await self.client.publish(topic, payload=json.dumps(payload), qos=0, retain=True)

class MqttHandler:
    def __init__(self,handler,discovery):
        self.handler=handler
        self.discovery=discovery
    def handle(self,msg):
        self.handler.handle(msg.payload,self.discovery)
        
        