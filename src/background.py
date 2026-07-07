from collections import defaultdict
import numpy as np


class BackgroundModel:
    def __init__(self, learning_seconds=10.0, angle_bin_size=1, threshold_mm=100):
        self.learning_seconds = learning_seconds
        self.angle_bin_size = angle_bin_size
        self.threshold_mm = threshold_mm

        self.samples = defaultdict(list)
        self.background = {}
        self.is_learning = True
        self.is_ready = False
        self.start_time = None

    def _angle_bin(self, angle):
        return int(angle // self.angle_bin_size)

    def process_point(self, point, now):
        if self.start_time is None:
            self.start_time = now

        elapsed = now - self.start_time

        if self.is_learning:
            bin_id = self._angle_bin(point.angle)
            self.samples[bin_id].append(point.distance)

            if elapsed >= self.learning_seconds:
                self._finish_learning()

            return None

        bin_id = self._angle_bin(point.angle)

        if bin_id not in self.background:
            return point

        background_distance = self.background[bin_id]
        difference = abs(point.distance - background_distance)

        if difference > self.threshold_mm:
            return point

        return None

    def _finish_learning(self):
        for bin_id, distances in self.samples.items():
            if distances:
                self.background[bin_id] = float(np.median(distances))

        self.is_learning = False
        self.is_ready = True

    def progress(self, now):
        if self.start_time is None:
            return 0.0

        elapsed = now - self.start_time
        return min(elapsed / self.learning_seconds, 1.0)