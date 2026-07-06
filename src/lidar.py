import asyncio
import math
from collections import deque

from rplidarc1 import RPLidar

from src.config import (
    PORT_NAME,
    BAUDRATE,
    MAX_POINTS,
    MAX_DISTANCE_MM,
    MIN_DISTANCE_MM,
    MIN_QUALITY,
)
from src.models import Point


class LidarReader:
    def __init__(self, status):
        self.status = status
        self.running = True
        self.points = deque(maxlen=MAX_POINTS)
        self.lidar = RPLidar(PORT_NAME, baudrate=BAUDRATE)

    async def run(self):
        print("Starting lidar scan...")
        self.status.lidar_running = True

        scan_task = asyncio.create_task(self.lidar.simple_scan())

        try:
            while self.running:
                point = await self.lidar.output_queue.get()

                angle = point["a_deg"]
                distance = point["d_mm"]
                quality = point["q"]

                if distance is None:
                    continue

                if quality < MIN_QUALITY:
                    continue

                if distance < MIN_DISTANCE_MM or distance > MAX_DISTANCE_MM:
                    continue

                radians = math.radians(angle)
                x = distance * math.cos(radians)
                y = distance * math.sin(radians)

                self.points.append(
                    Point(
                        x=x,
                        y=y,
                        angle=angle,
                        distance=distance,
                        quality=quality,
                    )
                )

                self.status.tick_scan()

        finally:
            print("Stopping lidar scan...")
            self.status.lidar_running = False

            try:
                self.lidar.stop_event.set()
            except Exception:
                pass

            try:
                scan_task.cancel()
                await scan_task
            except BaseException:
                pass

            self.shutdown()

    def stop(self):
        self.running = False
        self.status.lidar_running = False

    def shutdown(self):
        print("Sending lidar shutdown/reset...")

        try:
            self.lidar.stop_event.set()
        except Exception:
            pass

        try:
            self.lidar.reset()
        except Exception:
            pass

        try:
            self.lidar.shutdown()
        except Exception:
            pass