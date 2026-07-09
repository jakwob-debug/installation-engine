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
    ACTIVATION_MIN_DISTANCE_MM,
    ACTIVATION_MAX_DISTANCE_MM,
    MOVEMENT_THRESHOLD_MM,
    MOVEMENT_ANGLE_BIN_SIZE,
)
from src.models import Point


class LidarReader:
    def __init__(self, status, osc):
        self.status = status
        self.running = True
        self.osc = osc

        self.points = deque(maxlen=MAX_POINTS)
        self.moving_points = deque(maxlen=MAX_POINTS)

        self.measurement_scan = []
        self.display_scan = []
        self.previous_scan_by_bin = {}

        self.last_angle = None

        self.smoothed_presence = 0.0
        self.smoothed_activity = 0.0
        self.smoothed_distance_mm = 0.0
        self.smoothing_amount = 0.15

        self.lidar = RPLidar(PORT_NAME, baudrate=BAUDRATE)

    async def run(self):
        print("Starting lidar scan...")
        self.status.lidar_running = True
        self.status.background_state = "Off"

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

                self.measurement_scan.append(lidar_point)
                self.display_scan.append(lidar_point)

                if self.last_angle is not None and self.last_angle > 330 and angle < 30:
                    self.update_pillar_values()
                    self.update_movement_points()

                    self.points.clear()
                    self.points.extend(self.display_scan)

                    self.measurement_scan = []
                    self.display_scan = []
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

    def update_movement_points(self):
        current_scan_by_bin = {}
        moving = []

        for point in self.display_scan:
            angle_bin = int(point.angle // MOVEMENT_ANGLE_BIN_SIZE)

            previous_distance = self.previous_scan_by_bin.get(angle_bin)

            if previous_distance is not None:
                distance_change = abs(point.distance - previous_distance)

                if distance_change > MOVEMENT_THRESHOLD_MM:
                    moving.append(point)

            current_scan_by_bin[angle_bin] = point.distance

        self.previous_scan_by_bin = current_scan_by_bin

        self.moving_points.clear()
        self.moving_points.extend(moving)

    def update_pillar_values(self):
        if not self.measurement_scan:
            self.status.pillar_presence = 0.0
            self.status.pillar_distance_mm = 0.0
            self.status.pillar_activity = 0.0
            return

        distances = [
            p.distance
            for p in self.measurement_scan
            if p.distance is not None
        ]

        if not distances:
            self.status.pillar_presence = 0.0
            self.status.pillar_distance_mm = 0.0
            self.status.pillar_activity = 0.0
            return

        nearest = min(distances)

        min_distance = ACTIVATION_MIN_DISTANCE_MM
        max_distance = ACTIVATION_MAX_DISTANCE_MM

        presence = 1.0 - ((nearest - min_distance) / (max_distance - min_distance))
        presence = max(0.0, min(1.0, presence))

        activity = min(len(distances) / 250.0, 1.0)

        alpha = self.smoothing_amount

        self.smoothed_presence = (
            alpha * presence
            + (1.0 - alpha) * self.smoothed_presence
        )

        self.smoothed_activity = (
            alpha * activity
            + (1.0 - alpha) * self.smoothed_activity
        )

        if self.smoothed_distance_mm == 0:
            self.smoothed_distance_mm = nearest
        else:
            self.smoothed_distance_mm = (
                alpha * nearest
                + (1.0 - alpha) * self.smoothed_distance_mm
            )

        self.status.pillar_presence = self.smoothed_presence
        self.status.pillar_distance_mm = self.smoothed_distance_mm
        self.status.pillar_activity = self.smoothed_activity

        self.osc.send_pillar(
            self.status.pillar_presence,
            self.status.pillar_distance_mm,
            self.status.pillar_activity,
        )

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