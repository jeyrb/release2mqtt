import os
import typing
from dataclasses import dataclass, field

import structlog
from omegaconf import MISSING, OmegaConf

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
    default_entity_picture_url: str = "https://www.docker.com/wp-content/uploads/2022/03/Moby-logo.png"
    device_icon: str = "mdi:train-car-container"


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
    name: str | None = None


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
    docker: DockerPackageUpdateInfo | None = field(default_factory=DockerPackageUpdateInfo)
    logo_url: str | None = None
    release_notes_url: str | None = None


@dataclass
class UpdateInfoConfig:
    common_packages: dict[str, PackageUpdateInfo] = field(default_factory=lambda: {})


def load_package_info(pkginfo_file_path) -> UpdateInfoConfig:
    if os.path.exists(pkginfo_file_path):
        log.debug("Loading common package update info from %s", pkginfo_file_path)
        cfg = OmegaConf.load(pkginfo_file_path)
    else:
        log.warn("No common package update info found at %s", pkginfo_file_path)
        cfg = OmegaConf.structured(UpdateInfoConfig)
    OmegaConf.set_readonly(cfg, True)
    return typing.cast(UpdateInfoConfig, cfg)


def load_app_config(conf_file_path) -> Config:
    base_cfg = OmegaConf.structured(Config)
    if os.path.exists(conf_file_path):
        cfg = OmegaConf.merge(base_cfg, OmegaConf.load(conf_file_path))
    else:
        try:
            with open(conf_file_path, "w", encoding="utf-8") as f:
                f.write(OmegaConf.to_yaml(base_cfg))
        except Exception as e:
            log.error("Unable to write config file to %s: %s", conf_file_path, e)
        cfg = base_cfg

    if cfg.node.name is None:
        cfg.node.name = os.uname().nodename

    OmegaConf.set_readonly(cfg, True)
    return typing.cast(Config, cfg)
