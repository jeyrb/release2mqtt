from dataclasses import dataclass, field
from typing import Optional
from omegaconf import MISSING

@dataclass
class MqttConfig:
    host: str = "localhost"
    user: str = MISSING
    password: str = MISSING
    port: int = 1883

@dataclass
class DockerConfig:
    default: bool = True
    allow_pull: bool = True
    allow_restart: bool = True
    default_icon_url: str = 'https://www.docker.com/wp-content/uploads/2022/03/Moby-logo.png'
    
@dataclass
class HomeAssistantDiscoveryConfig:   
    prefix: str = "homeassistant"
    enabled: bool = True
    
@dataclass
class HomeAssistantConfig:
    discovery: HomeAssistantDiscoveryConfig = field(default_factory=HomeAssistantDiscoveryConfig)
    state_topic_suffix: str = "state"

@dataclass
class NodeConfig:
    name: Optional[str]=None
    
@dataclass
class LogConfig:
    level: str = 'INFO'

@dataclass
class Config:
    log: LogConfig = field(default_factory=LogConfig)
    node: NodeConfig = field(default_factory=NodeConfig)
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    homeassistant: HomeAssistantConfig = field(default_factory=HomeAssistantConfig)
    docker: DockerConfig = field(default_factory=DockerConfig)