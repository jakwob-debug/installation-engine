import asyncio
import math
import time
from collections import deque

from rplidarc1 import RPLidar

from src.background import BackgroundModel
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

        # This is the only buffer the viewer draws.
        self.points = deque(maxlen=MAX_POINTS)

        self.lidar = RPLidar(PORT_NAME, baudrate=BAUDRATE)
        self.background = BackgroundModel(
            learning_seconds=10.0,
            angle_bin_size=5,
            threshold_mm=300,
        )

        self.display_cleared_after_learning = False
        self.foreground_count = 0

    async def run(self):
        print("Starting lidar scan...")
        self.status.lidar_running = True

        scan_task = asyncio.create_task(self.lidar.simple_scan())

        try:
            while self.running:
                raw_point = await self.lidar.output_queue.get()

                angle = raw_point["a_deg"]
                distance = raw_point["d_mm"]
                quality = raw_point["q"]

                if distance is None:
                    continue
                if quality < MIN_QUALITY:
                    continue
                if distance < MIN_DISTANCE_MM or distance > MAX_DISTANCE_MM:
                    continue

                radians = math.radians(angle)
                x = distance * math.cos(radians)
                y = distance * math.sin(radians)

                lidar_point = Point(
                    x=x,
                    y=y,
                    angle=angle,
                    distance=distance,
                    quality=quality,
                )

                now = time.time()
                foreground_point = self.background.process_point(lidar_point, now)

                if self.background.is_learning:
                    self.points.append(lidar_point)
                    progress = self.background.progress(now) * 100
                    self.status.background_state = f"Learning {progress:.0f}%"

                elif self.background.is_ready:
                    if not self.display_cleared_after_learning:
                        self.points.clear()
                        self.display_cleared_after_learning = True
                        print("Background learned. Display cleared.")

                    self.status.background_state = f"Learned ✓ | FG: {self.foreground_count}"

                    if foreground_point is not None:
                        self.points.append(foreground_point)
                        self.foreground_count += 1

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