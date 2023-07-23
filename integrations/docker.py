import docker
from config import DockerConfig
import logging as log
from mqtt import MqttHandler
from model import Discovery

# TODO: distinguish docker build from docker pull

class DockerInstaller:
    def __init__(self, mqtt_client, cfg: DockerConfig):
        self.mqtt_client=mqtt_client
        self.client = docker.from_env()
    def connect(self,command_topic,discovery):
        self.mqtt_client.subscribe(command_topic,MqttHandler(self.handler,discovery))
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
                                    entity_picture_url=self.cfg.default_entity_picture_url,
                                    current_version=local_version,
                                    latest_version=reg_data.short_id,
                                    title_template='Docker image update for {name} on {node}',
                                    device_icon=self.cfg.device_icon)
            except Exception as e:
                log.error('ERROR %s: %s',c.name,e)
               