import os
import asyncio
import logging
from omegaconf import OmegaConf
from config import Config
from integrations.docker import DockerProvider
from mqtt import MqttClient
import uuid
import structlog

log = structlog.get_logger()

CONF_FILE='conf/config.yaml'

## TODO
# Set install in progress
# Support apt
# Retry on registry fetch fail
# Fetcher in subproc or thread
# Clear command message after install
# use git hash as alt to img ref for builds, or daily builds


class App:
    def __init__(self):
        base_cfg = OmegaConf.structured(Config)
        if os.path.exists(CONF_FILE):
            self.cfg=OmegaConf.merge(base_cfg,OmegaConf.load(CONF_FILE))
        else:
            with open(CONF_FILE,'w') as f:
                f.write(OmegaConf.to_yaml(base_cfg))
            self.cfg=base_cfg

        if self.cfg.node.name is None:
            self.cfg.node.name = os.uname().nodename
            
        structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(self.cfg.log.level)))
        
        self.publisher=MqttClient(self.cfg.mqtt,self.cfg.node,self.cfg.homeassistant)

        self.scanners=[]
        if self.cfg.docker.enabled:
            self.scanners.append(DockerProvider(self.cfg.docker))
        log.info('App configured', node=self.cfg.node.name, scan_interval=self.cfg.scan_interval)
        
    async def scan(self):
        for scanner in self.scanners:
            log.info('Starting scan',source_type=scanner.source_type)
            session=uuid.uuid4().hex
            log.info('Scanning',source=scanner.source_type,session=session)
            async for discovery in scanner.scan(session):
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.on_discovery(discovery))
            await self.publisher.clean_topics(scanner,session)
                
            log.info('Scan complete',source_type=scanner.source_type) 
        
    async def run(self):
        self.publisher.start()
        for scanner in self.scanners:
            self.publisher.subscribe_hass_command(scanner)
        while True:
            await self.scan()
            await asyncio.sleep(self.cfg.scan_interval)
    
    async def on_discovery(self,discovery):
        dlog=log.bind(name=discovery.name)
        if self.cfg.homeassistant.discovery.enabled:
            self.publisher.publish_hass_config(discovery)

        self.publisher.publish_hass_state(discovery)
        if discovery.update_policy=='Auto':
            dlog.info('Initiate auto update')
            self.publisher.local_message(discovery,'install')
    
if __name__ == '__main__':
    app=App()
    asyncio.run(app.run())