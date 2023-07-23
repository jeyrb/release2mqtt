

**Configuration**

Create file `config.yaml` in `conf` directory. If the file is not present, a default file will be generated.

Example use of environment variables, e.g. for secrets:

```
mqtt:
    password: ${oc.env:MQTT_PASS}
```
