import docker
from config import DockerConfig
import logging as log
from model import Discovery

# TODO: distinguish docker build from docker pull

class DockerInstaller:
    def __init__(self, cfg: DockerConfig):
        self.client = docker.from_env()

    def handle(self,payload,discovery):
        log.info('DOCKER-CMD %s',payload)
        log.info('DOCKER-PULL Pulling %s for %s',discovery.custom['image_ref'],discovery.custom['platform'])
        image=self.client.images.pull(discovery.custom['image_ref'],platform=discovery.custom['platform'])
        log.info('DOCKER-PULL %s %s', discovery.name, image.id)
    
class DockerScanner:
    def __init__(self, cfg: DockerConfig):
        self.client = docker.from_env()
        self.cfg=cfg
        
    def analyze(self, c):
        try:
            image_ref=c.image.tags[0]
        except:
            log.warn('DOCKER-SCAN No tags found for %s',c.name)
            image_ref=None
        try:
            local_version=c.image.attrs["RepoDigests"][0].split("@")[1][7:19]
        except:
            log.warn('DOCKER-SCAN Cannot determine local version - no digests found for %s',c.name)
            local_version=None
        try:
            c_env=dict(e.split('=') for e in c.attrs['Config']['Env'])
            picture_url=c_env.get('REL2MQTT_PICTURE',self.cfg.default_entity_picture_url)
            relnotes_url=c_env.get('REL2MQTT_RELNOTES')
            platform='/'.join(filter(None,[c.image.attrs['Os'],c.image.attrs['Architecture'],c.image.attrs.get('Variant')]))

            if image_ref and local_version:
                reg_data = self.client.images.get_registry_data(image_ref)
            else:
                reg_data=None
                
            local_version = local_version or 'Unknown'
            image_ref = image_ref or ''
            
            return Discovery('docker_image',c.name,
                                entity_picture_url=picture_url,
                                release_url=relnotes_url,
                                current_version=local_version,
                                latest_version=reg_data and reg_data.short_id[7:] or local_version,
                                title_template='Docker image update for {name} on {node}',
                                device_icon=self.cfg.device_icon,
                                custom={'image_ref':image_ref,'platform':platform})
        except Exception as e:
            log.error('DOCKER-SCAN ERROR %s: %s',c.name,e)
            log.debug(c.attrs)
  
    async def scan(self):
        for c in self.client.containers.list():
            result = self.analyze(c)
            if result:
                yield result
           
               