# release2mqtt

Publish new release version info to MQTT, with support for HomeAssistant auto discovery

## Configuration

Create file `config.yaml` in `conf` directory. If the file is not present, a default file will be generated.

Example use of environment variables, e.g. for secrets:

```
mqtt:
    password: ${oc.env:MQTT_PASS}
```

# HomeAssistant integration

Any updates that have support for automated install will automatically show in the
Home Assistant settings page:

![Example Home Assistant settings page](docs/images/hass_update_page.png "Home Assistant Updates")
