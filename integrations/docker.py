import docker
from config import DockerConfig
import logging as log
from model import Discovery, ReleaseProvider
import subprocess

# TODO: distinguish docker build from docker pull
      
class DockerProvider(ReleaseProvider):
    def __init__(self, cfg: DockerConfig):
        self.client = docker.from_env()
        self.cfg=cfg
        self.source_type='docker_image'
        
    def update(self,command,discovery):
        log.info('DOCKER-UPDATE Updating %s - %s',discovery.name,command)
        self.fetch(discovery)
        self.restart(discovery)
        log.info('DOCKER-UPDATE Updated %s - %s',discovery.name,command)
    
    def fetch(self,discovery):
        image_ref=discovery.custom.get('image_ref')
        platform=discovery.custom.get('platform')
        log.info('DOCKER-PULL Pulling %s for %s',image_ref,platform)
        image=self.client.images.pull(image_ref,platform=platform)
        log.info('DOCKER-PULL %s %s', discovery.name, image.id)
        
    def restart(self,discovery):
        compose_path=discovery.custom.get('compose_path')
        if compose_path:
            log.info('DOCKER-CMD Restarting %s: %s',discovery.name)
            proc=subprocess.run('docker-compose up --detach',shell=True,cwd=compose_path)
            if proc.returncode==0:
                log.info('DOCKER-CMD Restart %s via compose successful',discovery.name)
                return True
            else:
                log.warn('DOCKER-CMD Restart of %s failed: %s', discovery.name, proc.returncode)
        
    def rescan(self,discovery):
        c=self.client.containers.get(discovery.name)
        if c:
            return self.analyze(c,discovery.session)
        else:
            log.warn('DOCKER-RESCAN Unable to find %s',discovery.name)
                 
    def analyze(self, c, session):
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
            repo_path=c_env.get('REL2MQTT_REPO')
            
            platform='/'.join(filter(None,[c.image.attrs['Os'],c.image.attrs['Architecture'],c.image.attrs.get('Variant')]))

            reg_data=None
            if image_ref and local_version:
                retries_left=3
                while reg_data is None and retries_left > 0:
                    try:
                        reg_data = self.client.images.get_registry_data(image_ref)
                    except Exception as e:
                        retries_left-=1
                        if retries_left==0:
                            log.warn('DOCKER-SCAN Failed to fetch registry data for %s',c.name)
                        else:
                            log.debug('DOCKER-SCAN Failed to fetch registry data for %s',c.name)             

            local_version = local_version or 'Unknown'
            image_ref = image_ref or ''
            compose_path=c.labels.get('com.docker.compose.project.working_dir')
 
            custom={}
            custom['platform']=platform
            custom['image_ref']=image_ref
            custom['compose_path']=compose_path
            custom['repo_path']=repo_path
            custom['apt_pkgs']=c_env.get('REL2MQTT_APT')
            can_update=(self.cfg.allow_pull and image_ref) or (self.cfg.allow_restart and compose_path)  
            return Discovery(self,c.name,session,
                                entity_picture_url=picture_url,
                                release_url=relnotes_url,
                                current_version=local_version,
                                latest_version=reg_data and reg_data.short_id[7:] or local_version,
                                title_template='Docker image update for {name} on {node}',
                                device_icon=self.cfg.device_icon,
                                can_update=can_update,
                                custom=custom
                            )
        except Exception as e:
            log.error('DOCKER-SCAN ERROR %s: %s',c.name,e)
            log.debug(c.attrs)
  
    async def scan(self,session):
        for c in self.client.containers.list():
            result = self.analyze(c,session)
            if result:
                yield result
           
               