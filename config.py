from dataclasses import dataclass, field
from typing import Optional, Dict
from omegaconf import OmegaConf
import os
from omegaconf import MISSING
import structlog

log = structlog.get_logger()

@dataclass
class MqttConfig:
    host: str = "localhost"
    user: str = MISSING
    password: str = MISSING
    port: int = 1883
    topic_root: str = "rel2mqtt"


@dataclass
class DockerConfig:
    enabled: bool = True
    default: bool = True
    allow_pull: bool = True
    allow_restart: bool = True
    allow_build: bool = True
    default_entity_picture_url: str = (
        "https://www.docker.com/wp-content/uploads/2022/03/Moby-logo.png"
    )
    device_icon: str = "mdi:train-car-container"


@dataclass
class HomeAssistantDiscoveryConfig:
    prefix: str = "homeassistant"
    enabled: bool = True


@dataclass
class HomeAssistantConfig:
    discovery: HomeAssistantDiscoveryConfig = field(
        default_factory=HomeAssistantDiscoveryConfig
    )
    state_topic_suffix: str = "state"


@dataclass
class NodeConfig:
    name: Optional[str] = None


@dataclass
class LogConfig:
    level: str = "INFO"


@dataclass
class Config:
    log: LogConfig = field(default_factory=LogConfig)
    node: NodeConfig = field(default_factory=NodeConfig)
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    homeassistant: HomeAssistantConfig = field(default_factory=HomeAssistantConfig)
    docker: DockerConfig = field(default_factory=DockerConfig)
    scan_interval: int = 60 * 60 * 3


@dataclass
class DockerPackageUpdateInfo:
    image_name: str = MISSING


@dataclass
class PackageUpdateInfo:
    docker: Optional[DockerPackageUpdateInfo] = field(default_factory=DockerPackageUpdateInfo)
    logo_url: Optional[str] = None
    release_notes_url: Optional[str] = None


@dataclass
class UpdateInfoConfig:
    common_packages: Dict[str, PackageUpdateInfo] = field(default_factory=lambda: {})


def load_package_info(pkginfo_file_path):
    if os.path.exists(pkginfo_file_path):
        log.debug("Loading common package update info from %s", pkginfo_file_path)
        cfg = OmegaConf.load(pkginfo_file_path)
    else:
        log.warn("No common package update info found at %s", pkginfo_file_path)
        cfg = OmegaConf.structured(UpdateInfoConfig)
    OmegaConf.set_readonly(cfg, True)   
    return cfg


def load_app_config(conf_file_path):
    base_cfg = OmegaConf.structured(Config)
    if os.path.exists(conf_file_path):
        cfg = OmegaConf.merge(base_cfg, OmegaConf.load(conf_file_path))
    else:
        with open(conf_file_path, "w") as f:
            f.write(OmegaConf.to_yaml(base_cfg))
        cfg = base_cfg

    if cfg.node.name is None:
        cfg.node.name = os.uname().nodename

    OmegaConf.set_readonly(cfg, True)
    return cfg
