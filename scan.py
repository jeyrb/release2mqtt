import docker
import paho.mqtt.client as mqtt
import os
import logging as log
import json
import sys
from omegaconf import OmegaConf, DictConfig
from config import MqttConfig, DockerConfig, Config

CONF_FILE='conf/config.yaml'

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

class Handler:
    def __init__(self,handler_func,discovery):
        self.handler_func=handler_func
        self.discovery=discovery
    def handle(self,userdata,msg):
        self.handler_func(userdata,msg,self.discovery)
        
        
class DockerInstaller:
    def __init__(self, mqtt_client, cfg: DockerConfig):
        self.mqtt_client=mqtt_client
        self.client = docker.from_env()
    def connect(self,command_topic,discovery):
        self.mqtt_client.subscribe(command_topic,Handler(self.handler,discovery))
    def handler(self,user_data,msg,discovery):
        log.info('DOCKERINSTALL %s',msg.topic)
        repo=discovery
        self.client.images.pull()
    
class DockerScanner:
    def __init__(self, cfg: DockerConfig):
        self.client = docker.from_env()
        self.cfg=cfg
  
    def scan(self):
        for c in self.client.containers.list():
            registry=None
            try:
                registry,img=docker.auth.resolve_repository_name(c.image.tags[0])
                reg_data = self.client.images.get_registry_data(c.image.tags[0])
                local_version=c.image.attrs["RepoDigests"][0].split("@")[1][:19]

                yield Discovery('docker_image',c.name,
                                    icon_url=self.cfg.default_icon_url,
                                    current_version=local_version,
                                    latest_version=reg_data.short_id,
                                    title_template='Docker image update for {name} on {node}' )
            except Exception as e:
                log.error('ERROR %s: %s',c.name,e)
                
class Discovery:
    def __init__(self,source_type,name,icon_url=None,current_version=None,latest_version=None,
                 release_url=None,release_summary=None,title_template=None):
        self.source_type=source_type
        self.name=name
        self.icon_url=icon_url
        self.current_version=current_version
        self.latest_version=latest_version
        self.release_url=release_url
        self.release_summary=release_summary
        self.title_template=title_template

class App:
    def configure(self):
        base_cfg = OmegaConf.structured(Config)
        if os.path.exists(CONF_FILE):
            cfg=OmegaConf.merge(base_cfg,OmegaConf.load(CONF_FILE))
        else:
            with open(CONF_FILE,'w') as f:
                f.write(OmegaConf.to_yaml(base_cfg))
            cfg=base_cfg

        if cfg.node.name is None:
            cfg.node.name = os.uname().nodename
            
        log.basicConfig(stream=sys.stdout, level=cfg.log.level)
        return cfg
    
    def run(self,cfg):
        publisher=MqttClient(cfg.mqtt)
        publisher.connect()
        scanner=DockerScanner(cfg.docker)
        installer=DockerInstaller(publisher,cfg.docker)
        
        for discovery in scanner.scan():
            node_id='%s_%s' % (cfg.node.name,discovery.source_type)
            object_id='%s_%s_%s' % ( discovery.source_type,cfg.node.name,discovery.name)
            state_topic='%s/update/%s/%s/%s' % ( cfg.homeassistant.discovery.prefixy_prefix,
                                                node_id,discovery.name,cfg.homeassistant.state_topic_suffix )
            if cfg.docker.allow_pull or cfg.docker.allow_restart:
                command_topic='%s/update/%s/%s/command' % ( cfg.homeassistant.discovery.prefix,
                                                            node_id,discovery.name )
                installer.connect(command_topic,discovery)
            else:
                command_topic=None
            if cfg.homeassistant.discovery.enabled:
                config_topic='%s/update/%s/%s/config' % ( cfg.homeassistant.discovery.prefix,
                                                          node_id,discovery.name )
                publisher.publish(config_topic,hass_format_config(discovery,object_id,cfg.node.name,state_topic,command_topic))
            publisher.publish(state_topic,hass_state_config(discovery,cfg.node.name))
            
        log.info('Initial scan complete') 
        if cfg.docker.allow_pull or cfg.docker.allow_restart:
            publisher.wait()
        else:
            log.info('No auto update configured, so terminating')
        
def hass_format_config(discovery,object_id,node_name,state_topic,command_topic):
    return {
        'name':'%s %s' % (discovery.name,discovery.source_type),
        'device_class':None, # not firmware, so defaults to null
        'unique_id':object_id,
        'state_topic':state_topic,
        'command_topic':command_topic,
        'payload_install':'install',
        'latest_version_topic':state_topic,
        'latest_version_template':'{{value_json.latest_version}}',
    }  
def hass_state_config(discovery,node_name):
    return {
        'state'             : 'on' if discovery.latest_version != discovery.current_version else 'off',
        'installed_version' : discovery.current_version,
        'latest_version'    : discovery.latest_version,
        'title'             : discovery.title_template.format(name=discovery.name,node=node_name),
        'release_url'       : discovery.release_url,
        'release_summary'   : discovery.release_summary,
        'entity_picture'    : discovery.icon_url,
        'icon'              : 'mdi:train-car-container'
    }
 
    
if __name__ == '__main__':
    app=App()
    cfg=app.configure()
    app.run(cfg)