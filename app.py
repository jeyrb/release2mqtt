

import os
import asyncio
import logging as log
import sys
from omegaconf import OmegaConf
from config import Config
from integrations.docker import DockerScanner
from mqtt import MqttClient
import aiocron

CONF_FILE='conf/config.yaml'

## TODO
# Set install in progress
# Clean up dead docker from topic
# Support d-c build with git pull
# Support apt
# Retry on registry fetch fail
# Fetcher in subproc or thread

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
        self.publisher=MqttClient(self.cfg.mqtt,self.cfg.node,self.cfg.homeassistant)

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
            await self.publisher.clean_topics(scanner.source_type)
                
        log.info('Scan complete') 
        
    async def run(self):
        await self.publisher.start()
        await self.scan()
        await self.publisher.listen()
    
    async def on_discovery(self,discovery):
        if discovery.fetcher or discovery.restarter:
            await self.publisher.subscribe_hass_command(discovery)
            commandable=True
        else:
            commandable=False
        if self.cfg.homeassistant.discovery.enabled:
            await self.publisher.publish_hass_config(discovery,
                                                     commandable=commandable)

        await self.publisher.publish_hass_state(discovery)
    
if __name__ == '__main__':
    app=App()
    asyncio.run(app.run())