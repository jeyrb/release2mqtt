

import os
import asyncio
import logging as log
import sys
from omegaconf import OmegaConf
from config import Config
from integrations.docker import DockerInstaller, DockerScanner
from mqtt import MqttClient, MqttHandler
import aiocron

CONF_FILE='conf/config.yaml'


class App:
    def __init__(self):
        log.basicConfig(stream=sys.stdout, level='INFO')
        base_cfg = OmegaConf.structured(Config)
        if os.path.exists(CONF_FILE):
            self.cfg=OmegaConf.merge(base_cfg,OmegaConf.load(CONF_FILE))
        else:
            with open(CONF_FILE,'w') as f:
                f.write(OmegaConf.to_yaml(base_cfg))
            self.cfg=base_cfg

        if self.cfg.node.name is None:
            self.cfg.node.name = os.uname().nodename
            
        log.basicConfig(stream=sys.stdout, level=self.cfg.log.level)
        self.publisher=MqttClient(self.cfg.mqtt)
        #self.publisher.connect()
        self.installer=DockerInstaller(self.cfg.docker)
        self.scanners=[]
        if self.cfg.docker.enabled:
            self.scanners.append(DockerScanner(self.cfg.docker))
    
    @aiocron.crontab('0 */3 * * *')
    async def periodic_scan(self):
        self.scan()
        
    async def scan(self):
        log.info('Starting scan')
        for scanner in self.scanners:
            async for discovery in scanner.scan():
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.on_discovery(discovery))
                
        log.info('Scan complete') 
        
    async def run(self):
        await self.publisher.start()
        await self.scan()
        await self.publisher.listen()
    
    async def on_discovery(self,discovery):
        node_id='%s_%s' % (self.cfg.node.name,discovery.source_type)
        object_id='%s_%s_%s' % ( discovery.source_type,self.cfg.node.name,discovery.name)
        state_topic='%s/update/%s/%s/%s' % ( self.cfg.homeassistant.discovery.prefix,
                                            node_id,discovery.name,
                                            self.cfg.homeassistant.state_topic_suffix )
        if self.cfg.docker.allow_pull or self.cfg.docker.allow_restart:
            command_topic='%s/update/%s/%s/command' % ( self.cfg.homeassistant.discovery.prefix,
                                                        node_id,discovery.name )
            await self.publisher.subscribe(command_topic,MqttHandler(self.installer,discovery))
            #self.installer.connect(command_topic,discovery)
        else:
            command_topic=None
        if self.cfg.homeassistant.discovery.enabled:
            config_topic='%s/update/%s/%s/config' % ( self.cfg.homeassistant.discovery.prefix,
                                                    node_id,discovery.name )
            await self.publisher.publish(config_topic,hass_format_config(discovery,object_id,
                                                              self.cfg.node.name,
                                                              state_topic,command_topic))
        await self.publisher.publish(state_topic,hass_state_config(discovery,self.cfg.node.name))
    

        
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
    asyncio.run(app.run())