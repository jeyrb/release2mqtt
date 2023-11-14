import docker
from config import DockerConfig, UpdateInfoConfig
from docker.models.containers import Container
import os.path
import structlog
from model import Discovery, ReleaseProvider
import subprocess
import time
from integrations.git_utils import (
    git_check_update_available,
    git_pull,
    git_timestamp,
    git_trust,
)

# TODO: distinguish docker build from docker pull

log = structlog.get_logger()

safe_json_dt = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S.0000", time.gmtime(t)) if t else None


class DockerProvider(ReleaseProvider):
    def __init__(self, cfg: DockerConfig, common_pkg_cfg: UpdateInfoConfig):
        self.client = docker.from_env()
        self.cfg = cfg
        self.common_pkgs = common_pkg_cfg.common_packages
        self.source_type = "docker"
        self.discoveries = {}
        self.log = structlog.get_logger().bind(integration="docker")

    def update(self, discovery: Discovery):
        log = self.log.bind(container=discovery.name, action="update")
        log.info("Updating - last at %s", discovery.update_last_attempt)
        discovery.update_last_attempt = time.time()
        self.fetch(discovery)
        restarted = self.restart(discovery)
        log.info("Updated - recorded at %s", discovery.update_last_attempt)
        return restarted

    def fetch(self, discovery: Discovery):
        log = self.log.bind(container=discovery.name, action="fetch")
        git_repo_path = discovery.custom.get("git_repo_path")
        compose_path = discovery.custom.get("compose_path")
        image_ref = discovery.custom.get("image_ref")
        platform = discovery.custom.get("platform")
        if git_repo_path:
            if compose_path and not os.path.isabs(git_repo_path):
                full_repo_path = os.path.join(compose_path, git_repo_path)
            else:
                full_repo_path = git_repo_path
            if git_check_update_available(full_repo_path):
                git_pull(full_repo_path)
            self.build(discovery, compose_path)
        elif image_ref:
            log.info("Pulling", image_ref=image_ref, platform=platform)
            image = self.client.images.pull(image_ref, platform=platform)
            log.info("Pulled", image_id=image.id)

    def build(self, discovery: Discovery, compose_path: str):
        log = self.log.bind(container=discovery.name, action="build")
        log.info("Building")
        proc = subprocess.run("docker-compose build", shell=True, cwd=compose_path)
        if proc.returncode == 0:
            log.info("Build via compose successful")
            return True
        else:
            log.warn(
                "Build failed: %s",
                proc.returncode,
            )

    def restart(self, discovery: Discovery):
        log = self.log.bind(container=discovery.name, action="restart")
        compose_path = discovery.custom.get("compose_path")
        if compose_path:
            log.info("Restarting")
            proc = subprocess.run(
                "docker-compose up --detach", shell=True, cwd=compose_path
            )
            if proc.returncode == 0:
                log.info("Restart via compose successful")
                return True
            else:
                log.warn(
                    "Restart failed: %s",
                    proc.returncode,
                )

    def rescan(self, discovery: Discovery):
        log = self.log.bind(container=discovery.name, action="rescan")
        c = self.client.containers.get(discovery.name)
        if c:
            return self.analyze(c, discovery.session, original_discovery=discovery)
        else:
            log.warn("Unable to find container for rescan")

    def analyze(self, c: Container, session: str, original_discovery=None):
        log = self.log.bind(container=c.name, action="analyze")
        try:
            image_ref = c.image.tags[0]
            image_name = image_ref.split(":")[0]
        except:
            log.warn("No tags found")
            image_ref = None
            image_name = None
        try:
            local_versions = [ i.split("@")[1][7:19] for i in c.image.attrs["RepoDigests"] ]
        except Exception as e:
            log.warn("Cannot determine local version: %s", e)
            log.warn("RepoDigests=%s", c.image.attrs.get("RepoDigests"))
            local_versions = None

        relnotes_url = None
        picture_url = self.cfg.default_entity_picture_url

        for pkg in self.common_pkgs.values():
            if (
                pkg.docker is not None
                and pkg.docker.image_name is not None
                and pkg.docker.image_name == image_name
            ):
                picture_url = pkg.logo_url
                relnotes_url = pkg.release_notes_url

        env_override = (
            lambda env_var, default: default
            if c_env.get(env_var) is None
            else c_env.get(env_var)
        )
        try:
            env_str = c.attrs["Config"]["Env"]
            c_env = dict(env.split("=") for env in env_str if "==" not in env)
            picture_url = env_override("REL2MQTT_PICTURE", picture_url)
            relnotes_url = env_override("REL2MQTT_RELNOTES", relnotes_url)

            platform = "/".join(
                filter(
                    None,
                    [
                        c.image.attrs["Os"],
                        c.image.attrs["Architecture"],
                        c.image.attrs.get("Variant"),
                    ],
                )
            )

            reg_data = None
            latest_version = local_version = 'Unknown'
            
            if image_ref and local_versions:
                retries_left = 3
                while reg_data is None and retries_left > 0:
                    try:
                        reg_data = self.client.images.get_registry_data(image_ref)
                        latest_version = reg_data and reg_data.short_id[7:]
                    except Exception as e:
                        retries_left -= 1
                        if retries_left == 0:
                            log.warn("Failed to fetch registry data")
                        else:
                            log.debug("Failed to fetch registry data, retrying")

            if local_versions:
                # might be multiple RepoDigests if image has been pulled multiple times with diff manifests
                if latest_version in local_versions:
                    local_version = latest_version
                else:
                    local_version = local_versions[0]
                    
            image_ref = image_ref or ""
            compose_path = c.labels.get("com.docker.compose.project.working_dir")

            custom = {}
            custom["platform"] = platform
            custom["image_ref"] = image_ref
            custom["compose_path"] = compose_path
            custom["compose_version"] = c.labels.get("com.docker.compose.version")
            custom["git_repo_path"] = c_env.get("REL2MQTT_GIT_REPO_PATH")
            custom["apt_pkgs"] = c_env.get("REL2MQTT_APT_PKGS")

            if c_env.get("REL2MQTT_UPDATE") == "AUTO":
                log.debug("Auto update policy detected")
                update_policy = "Auto"
            else:
                update_policy = "Passive"

            if custom["git_repo_path"]:
                full_repo_path = os.path.join(compose_path, custom["git_repo_path"])
                git_trust(full_repo_path)
                custom["git_local_timestamp"] = git_timestamp(full_repo_path)
            can_update = (
                (self.cfg.allow_pull and image_ref)
                or (self.cfg.allow_restart and compose_path)
                or (self.cfg.allow_build and custom["git_repo_path"])
            )
            return Discovery(
                self,
                c.name,
                session,
                entity_picture_url=picture_url,
                release_url=relnotes_url,
                current_version=local_version,
                update_policy=update_policy,
                update_last_attempt=original_discovery and original_discovery.update_last_attempt or None,
                latest_version=latest_version if latest_version !='Unknown' else local_version,
                title_template="Docker image update for {name} on {node}",
                device_icon=self.cfg.device_icon,
                can_update=can_update,
                status=c.status == "running" and "on" or "off",
                custom=custom,
            )
        except Exception as e:
            log.error("ERROR %s", e, exc_info=1, container_attrs=c.attrs)

    async def scan(self, session: str):
        log = self.log.bind(session=session, action="scan")
        c=r=0
        for c in self.client.containers.list():
            c=c+1
            result = self.analyze(c, session)
            if result:
                self.discoveries[result.name] = result
                r=r+1
                yield result
        log.info('Completed',container_count=c,result_count=r)

    def command(self, discovery_name, command, on_update_start, on_update_end):
        log = self.log.bind(container=discovery_name, action="command", command=command)
        log.info("Executing")
        updated = False
        try:
            discovery = self.discoveries.get(discovery_name)
            if not discovery:
                log.warn("Unknown entity",entity=discovery_name)
            elif command != "install":
                log.warn("Unknown command")
            else:
                if discovery.can_update:
                    log.info("Starting update ...")
                    on_update_start(discovery)
                    if self.update(discovery):
                        log.info("Rescanning ...")
                        updated = self.rescan(discovery)
                        log.info("Rescanned %s", updated)
                    else:
                        log.info("Rescan with no result")
                        on_update_end(discovery)
        except Exception as e:
            log.error("Failed to handle: %s", e, exc_info=1)
            if discovery:
                on_update_end(discovery)
        return updated

    def hass_state_format(self, discovery):
        return {
            "docker_image_ref": discovery.custom.get("image_ref"),
            "last_update_attempt": safe_json_dt(discovery.update_last_attempt),
        }
