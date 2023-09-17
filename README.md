# release2mqtt

Publish new release version info to MQTT, with support for HomeAssistant auto discovery

## Install

### Manual
```
pip install -r requirements.txt
```
### Docker
See ``examples`` directory for a working ``docker-compose.yaml`` which presumes that ``release2mqtt`` has been checked out inside a ``build`` subdirectory of the docker-compose directory.

## Configuration

Create file `config.yaml` in `conf` directory. If the file is not present, a default file will be generated.

Example use of environment variables, e.g. for secrets:

```
mqtt:
    password: ${oc.env:MQTT_PASS}
```

Individual docker containers can have customized entity pictures or release notes, using env variables:

```
    environment:
      - REL2MQTT_PICTURE=https://frigate.video/images/logo.svg
      - REL2MQTT_RELNOTES=https://github.com/blakeblackshear/frigate/releases
```

### Custom docker builds

If the image is locally built from a checked out git repo, package update can be driven
by the availability of repo changes to pull rather than a new image on a Docker registry.

Declare the git path using the env var in ``REL2MQTT_GIT_REPO_PATH`` in docker compose ( directly or via an ``.env`` file).
The git repo at this path will be used as the source of timestamps, and an update command will carry out a 
``git pull`` and ``docker-compose build`` rather than pulling an image.

Note that the release2mqtt docker container needs access to this path declared in its volumes, and that has to
be read/write if automated install required.


# Release Support

| Ecosystem | Support     | Comments |
| --------- | ----------- | -------- |
| Docker    | Scan. Fetch | Fetch is ``docker pull`` only. Restart support only for ``docker-compose`` image based containers.|
  
  
# HomeAssistant integration

Any updates that have support for automated install will automatically show in the
Home Assistant settings page:

![Example Home Assistant settings page](docs/images/hass_update_page.png "Home Assistant Updates")

If the package supports automated update, then *Skip* and *Install* buttons will appear on the Home Assistant
interface, and the package can be remotely fetched and the component restarted.
