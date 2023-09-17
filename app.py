import asyncio
import logging
from config import load_app_config, load_package_info
from integrations.docker import DockerProvider
from mqtt import MqttClient
import uuid
import structlog
import time

log = structlog.get_logger()

CONF_FILE = "conf/config.yaml"
PKG_INFO_FILE = "common_packages.yaml"
UPDATE_INTERVAL=60*60*4

# #TODO
# Set install in progress
# Support apt
# Retry on registry fetch fail
# Fetcher in subproc or thread
# Clear command message after install
# use git hash as alt to img ref for builds, or daily builds


class App:
    def __init__(self):
        self.cfg = load_app_config(CONF_FILE)
        self.common_pkg = load_package_info(PKG_INFO_FILE)
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.getLevelName(self.cfg.log.level)
            )
        )

        self.publisher = MqttClient(
            self.cfg.mqtt, self.cfg.node, self.cfg.homeassistant
        )

        self.scanners = []
        if self.cfg.docker.enabled:
            self.scanners.append(DockerProvider(self.cfg.docker, self.common_pkg))
        log.info(
            "App configured",
            node=self.cfg.node.name,
            scan_interval=self.cfg.scan_interval,
        )

    async def scan(self):
        for scanner in self.scanners:
            log.info("Starting scan", source_type=scanner.source_type)
            session = uuid.uuid4().hex
            log.info("Scanning", source=scanner.source_type, session=session)
            async for discovery in scanner.scan(session):
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.on_discovery(discovery))
            await self.publisher.clean_topics(scanner, session)

            log.info("Scan complete", source_type=scanner.source_type)

    async def run(self):
        self.publisher.start()
        for scanner in self.scanners:
            self.publisher.subscribe_hass_command(scanner)
        while True:
            await self.scan()
            await asyncio.sleep(self.cfg.scan_interval)

    async def on_discovery(self, discovery):
        dlog = log.bind(name=discovery.name)
        if self.cfg.homeassistant.discovery.enabled:
            self.publisher.publish_hass_config(discovery)

        self.publisher.publish_hass_state(discovery)
        if discovery.update_policy == "Auto":
            if discovery.update_last_attempt is None or time.time()-discovery.update_last_attempt > UPDATE_INTERVAL:
                dlog.info("Initiate auto update")
                self.publisher.local_message(discovery, "install")
            else:
                dlog.info("Skipping auto update")


if __name__ == "__main__":
    app = App()
    asyncio.run(app.run())
