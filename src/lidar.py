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

        self.points = deque(maxlen=MAX_POINTS)
        self.current_scan = []
        self.last_angle = None

        self.lidar = RPLidar(PORT_NAME, baudrate=BAUDRATE)
        self.background = BackgroundModel(
            learning_seconds=10.0,
            angle_bin_size=5,
            threshold_mm=1200,
        )

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
                    self.current_scan.append(lidar_point)
                    progress = self.background.progress(now) * 100
                    self.status.background_state = f"Learning {progress:.0f}%"

                elif self.background.is_ready:
                    self.status.background_state = "Learned ✓"

                    if foreground_point is not None:
                        self.current_scan.append(foreground_point)

                # New revolution: replace display with this scan only
                if self.last_angle is not None and self.last_angle > 330 and angle < 30:
                    self.points.clear()
                    self.points.extend(self.current_scan)
                    self.current_scan = []
                    self.status.tick_scan()

                self.last_angle = angle

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