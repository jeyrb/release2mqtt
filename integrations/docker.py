import docker
from config import DockerConfig
import logging as log
from model import Discovery, Fetcher, Restarter
import subprocess

# TODO: distinguish docker build from docker pull

class DockerFetcher(Fetcher):
    def __init__(self, name, client, image_ref=None, platform=None):
        self.name=name
        self.client=client
        self.image_ref=image_ref
        self.platform=platform
    def fetch(self,command):
        log.info('DOCKER-PULL Pulling %s for %s - %s',self.image_ref,self.platform,command)
        image=self.client.images.pull(self.image_ref,platform=self.platform)
        log.info('DOCKER-PULL %s %s', self.name, image.id)
        
class DockerRestarter(Restarter):
    def __init__(self, name, compose_path=None):
        self.compose_path=compose_path
        self.name=name
        
    def restart(self,command):
        if self.compose_path:
            log.info('DOCKER-CMD Restarting %s: %s',self.name, command)
            proc=subprocess.run('docker-compose up --detach',shell=True,cwd=self.compose_path)
            if proc.returncode==0:
                log.info('DOCKER-CMD Restart %s via compose successful',self.name)
                return True
            else:
                log.warn('DOCKER-CMD Restart of %s failed: %s', self.name, proc.returncode)
    
class DockerScanner:
    def __init__(self, cfg: DockerConfig):
        self.client = docker.from_env()
        self.cfg=cfg
        
    def rescan(self,container_name):
        c=self.client.containers.get(container_name)
        if c:
            self.analyze(c)
        else:
            log.warn('DOCKER-RESCAN Unable to find %s',container_name)
                 
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
            compose_path=c.labels.get('com.docker.compose.project.working_dir')
            if self.cfg.allow_restart and compose_path:
                restarter=DockerRestarter(c.name,compose_path=compose_path)
            else:
                restarter=None
            if self.cfg.allow_pull and image_ref:
                fetcher=DockerFetcher(c.name,self.client, image_ref=image_ref,platform=platform)
            else:
                fetcher=None
            
            return Discovery('docker_image',c.name,
                                entity_picture_url=picture_url,
                                release_url=relnotes_url,
                                current_version=local_version,
                                latest_version=reg_data and reg_data.short_id[7:] or local_version,
                                title_template='Docker image update for {name} on {node}',
                                device_icon=self.cfg.device_icon,
                                restarter=restarter,
                                fetcher=fetcher,
                                rescanner=self
                            )
        except Exception as e:
            log.error('DOCKER-SCAN ERROR %s: %s',c.name,e)
            log.debug(c.attrs)
  
    async def scan(self):
        for c in self.client.containers.list():
            result = self.analyze(c)
            if result:
                yield result
           
               