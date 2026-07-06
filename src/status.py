import time
from dataclasses import dataclass, field


@dataclass
class Status:
    app_running: bool = True
    lidar_running: bool = False

    point_count: int = 0
    fps: float = 0.0
    scan_hz: float = 0.0

    background_state: str = "Not started"
    people_count: int = 0
    osc_state: str = "Off"

    _last_display_time: float = field(default_factory=time.time)
    _display_frames: int = 0

    _last_scan_time: float = field(default_factory=time.time)
    _scan_frames: int = 0

    def tick_display(self):
        self._display_frames += 1
        now = time.time()
        elapsed = now - self._last_display_time

        if elapsed >= 1.0:
            self.fps = self._display_frames / elapsed
            self._display_frames = 0
            self._last_display_time = now

    def tick_scan(self):
        self._scan_frames += 1
        now = time.time()
        elapsed = now - self._last_scan_time

        if elapsed >= 1.0:
            self.scan_hz = self._scan_frames / elapsed
            self._scan_frames = 0
            self._last_scan_time = now