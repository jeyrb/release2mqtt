import paho.mqtt.client as mqtt
import json
from config import MqttConfig
import logging as log

class MqttClient:
    def __init__(self,cfg: MqttConfig):
        self.cfg=cfg
        self.topic_handlers = {}
        
    def connect(self):
        try:
            self.client = mqtt.Client(clean_session=True)
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.username_pw_set(username=self.cfg.user,password=self.cfg.password)
            self.client.connect(self.cfg.host, int(self.cfg.port), 60)
            self.client.loop_start()
            log.info("Connected to MQTT at %s:%s" % (self.cfg.host, self.cfg.port))
        except Exception as e:
            log.error("Failed to connect to MQTT %s:%s - %s", self.cfg.host, self.cfg.port, e)
            raise EnvironmentError("MQTT Connection Failure")
    
    def on_connect(self, _client, _userdata, _flags, rc):
        log.info("Connected to MQTT with result code " + str(rc))
        
    def on_message(self,client,user_data,msg):
        if msg.topic in self.topic_handlers:
            log.info('MQTT Handling message for %s',msg.topic)
            self.topic_handlers[msg.topic].handle(user_data,msg)
        else:
            log.warn('MQTT Unhandled message: %s',msg.topic)
        
    def subscribe(self,topic,handler):
        self.topic_handlers[topic]=handler
        self.client.subscribe(topic)
        
    def wait(self):
        self.client.loop_forever()
        
    def publish(self,topic,payload):
        self.client.publish(topic, payload=json.dumps(payload), qos=0, retain=True)

class MqttHandler:
    def __init__(self,handler_func,discovery):
        self.handler_func=handler_func
        self.discovery=discovery
    def handle(self,userdata,msg):
        self.handler_func(userdata,msg,self.discovery)
        
        