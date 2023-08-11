import paho.mqtt.client as mqtt
import paho.mqtt
from config import MqttConfig, NodeConfig, HomeAssistantConfig
import logging as log
import asyncio
import json
import uuid
from hass_formatter import hass_format_config,hass_state_config

class MqttClient:
    def __init__(self,cfg: MqttConfig, node_cfg: NodeConfig, hass_cfg: HomeAssistantConfig):
        self.cfg=cfg
        self.node_cfg = node_cfg
        self.hass_cfg = hass_cfg
        self.topic_handlers = {}
        self.session=uuid.uuid4().hex
    
    def start(self):  
        try:
            self.event_loop=asyncio.get_event_loop()
            self.client=mqtt.Client(client_id='beta_release2mqtt_%s' % self.node_cfg.name,
                                    clean_session=True)
            self.client.username_pw_set(self.cfg.user,password=self.cfg.password)
            self.client.connect(host=self.cfg.host,port=self.cfg.port,keepalive=60)
            self.client.on_connect=self.on_connect
            self.client.on_disconnect=self.on_disconnect
            self.client.on_message=self.on_message
            self.client.loop_start()
            log.info("MQTT Connected to broker at %s:%s" % (self.cfg.host, self.cfg.port))
            log.info("MQTT client session %s", self.session)
        except Exception as e:
            log.error("MQTT Failed to connect to broker %s:%s - %s", self.cfg.host, self.cfg.port, e)
            raise EnvironmentError("MQTT Connection Failure to %s:%s as %s -- %s" % ( self.cfg.host,self.cfg.port,self.cfg.user,e))
    
    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        
    def on_connect(self, _client, _userdata, _flags, rc):
        log.info("MQTT Connected to broker with result code " + str(rc))
        
    def on_disconnect(self, _client, _userdata, rc):
        log.info("MQTT Disconnected from broker with result code " + str(rc))
      
    async def clean_topics(self,source_type,timeout=20):
        log.info('MQTT-Clean Starting clean cycle')
        cleaner=mqtt.Client(    client_id='release2mqtt_clean_%s' % self.node_cfg.name,
                                clean_session=True)
        cleaner.username_pw_set(self.cfg.user,password=self.cfg.password)
        cleaner.connect(host=self.cfg.host,port=self.cfg.port,keepalive=60)
        def cleanup(_client,_userdata,msg):
            if msg.retain and msg.payload:
                try:
                    payload=json.loads(msg.payload)
                    session=payload.get('source_session')
                    if session is None or session != self.session:
                        log.info('MQTT-CLEAN Removing %s [%s]',msg.topic,session)
                        cleaner.publish(msg.topic.value,None,retain=False)
                except Exception as e:
                    log.warn('MQTT-CLEAN Unable to handle %s: %s',msg.topic,e,exc_info=1)

        cleaner.on_message=cleanup
        options=paho.mqtt.subscribeoptions.SubscribeOptions(noLocal=True)
        cleaner.subscribe('%s_%s/#' % (self.base_topic(),source_type),options=options)
        await asyncio.sleep(60) 
                            
        log.info('MQTT-Clean Completed clean cycle')
            
    def on_message(self,_client,_userdata,msg):
        if msg.topic in self.topic_handlers:
            log.info('MQTT Handling message for %s',msg.topic)
            handler=self.topic_handlers[msg.topic]
            asyncio.run_coroutine_threadsafe(handler.handle(msg),self.event_loop)
        else:
            log.warn('MQTT Unhandled message: %s',msg.topic)
        
    def subscribe(self,topic,handler):
        log.info('MQTT Handler subscribing to %s',topic)
        self.topic_handlers[topic]=handler
        self.client.subscribe(topic)
        
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
        
    def publish_hass_state(self,discovery):
        self.publish(self.state_topic(discovery),
                           hass_state_config(discovery,self.node_cfg.name,self.session))
        
    def publish_hass_config(self,discovery,commandable=True):
        object_id='%s_%s_%s' % ( discovery.source_type,self.node_cfg.name,discovery.name)
        command_topic = self.command_topic(discovery) if commandable else None
        self.publish(self.config_topic(discovery),
                           hass_format_config(discovery,object_id,
                                              self.node_cfg.name,
                                              self.state_topic(discovery),
                                              command_topic,
                                              self.session))
    def subscribe_hass_command(self,discovery):
        self.subscribe(self.command_topic(discovery),MqttHandler(discovery))            
        
    def wait(self):
        log.info('MQTT Starting event loop')
        self.client.loop_forever()
        log.info('MQTT Ended event loop')
        
    def loop_once(self):
        self.client.loop()
        
    def publish(self,topic,payload):
        self.client.publish(topic, payload=json.dumps(payload), qos=0, retain=True)

class MqttHandler:
    def __init__(self,discovery):
        self.discovery=discovery
    async def handle(self,msg):
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
                        log.info('MQTT-Handler Rescanned %s ...',self.discovery.name)
        except Exception as e:
            log.error('MQTT-Handler Failed to handle %s: %s', msg,e)


