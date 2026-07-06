import asyncio
import signal

from src.lidar import LidarReader
from src.viewer import Viewer


class InstallationApp:
    def __init__(self):
        self.lidar = LidarReader()
        self.viewer = Viewer(self.lidar)

    async def run(self):
        lidar_task = asyncio.create_task(self.lidar.run())
        viewer_task = asyncio.create_task(self.viewer.run())

        await asyncio.gather(lidar_task, viewer_task)

    def stop(self):
        print("Stopping app...")
        self.viewer.stop()
        self.lidar.stop()

    def shutdown(self):
        self.lidar.shutdown()


async def main():
    app = InstallationApp()

    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, app.stop)

    try:
        await app.run()
    finally:
        app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
