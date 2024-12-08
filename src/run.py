import asyncio

from release2mqtt.app import App

app = App()
asyncio.run(app.run())
