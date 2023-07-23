

import os
import logging as log
import sys
from omegaconf import OmegaConf
from config import Config
from integrations.docker import DockerInstaller, DockerScanner
from mqtt import MqttClient

CONF_FILE='conf/config.yaml'

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
        scanners=[]
        if cfg.docker.enabled:
            scanners.append(DockerScanner(cfg.docker))

        installer=DockerInstaller(publisher,cfg.docker)
        
        for scanner in scanners:
            for discovery in scanner.scan():
                node_id='%s_%s' % (cfg.node.name,discovery.source_type)
                object_id='%s_%s_%s' % ( discovery.source_type,cfg.node.name,discovery.name)
                state_topic='%s/update/%s/%s/%s' % ( cfg.homeassistant.discovery.prefix,
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
        'entity_picture'    : discovery.entity_picture_url,
        'icon'              : discovery.device_icon
    }
 
    
if __name__ == '__main__':
    app=App()
    cfg=app.configure()
    app.run(cfg)