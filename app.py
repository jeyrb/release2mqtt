import os
import asyncio
import logging as log
import sys
from omegaconf import OmegaConf
from config import Config
from integrations.docker import DockerProvider
from mqtt import MqttClient
import uuid


CONF_FILE='conf/config.yaml'

## TODO
# Set install in progress
# Support d-c build with git pull
# Support apt
# Retry on registry fetch fail
# Fetcher in subproc or thread
# Clear command message after install
# use git hash as alt to img ref for builds, or daily builds


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
            self.scanners.append(DockerProvider(self.cfg.docker))
        log.info('REL2MQTT App configured - node:%s, scan_interval: %s', self.cfg.node.name, self.cfg.scan_interval)
        
    async def scan(self):
        log.info('Starting scan')
        for scanner in self.scanners:
            session=uuid.uuid4().hex
            log.info('Scanning %s [session %s]',scanner.source_type,session)
            async for discovery in scanner.scan(session):
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.on_discovery(discovery))
            await self.publisher.clean_topics(scanner,session)
                
        log.info('Scan complete') 
        
    async def run(self):
        self.publisher.start()
        for scanner in self.scanners:
            self.publisher.subscribe_hass_command(scanner)
        while True:
            await self.scan()
            await asyncio.sleep(self.cfg.scan_interval)
    
    async def on_discovery(self,discovery):
        if self.cfg.homeassistant.discovery.enabled:
            self.publisher.publish_hass_config(discovery)

        self.publisher.publish_hass_state(discovery)
    
if __name__ == '__main__':
    app=App()
    asyncio.run(app.run())