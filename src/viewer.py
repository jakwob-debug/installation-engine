import asyncio

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

from src.config import (
    MAX_DISTANCE_MM,
    DISPLAY_UPDATE_MS,
    ACTIVATION_MAX_DISTANCE_MM,
)


class Viewer:
    def __init__(self, lidar_reader, status):
        self.running = True
        self.lidar_reader = lidar_reader
        self.status = status

        self.qt_app = QtWidgets.QApplication([])

        self.window = pg.GraphicsLayoutWidget(
            show=True,
            title="RPLIDAR C1 Installation Viewer",
        )
        self.window.resize(1100, 900)

        self.plot = self.window.addPlot(row=0, col=0)
        self.plot.setAspectLocked(True)
        self.plot.showGrid(x=True, y=True)
        self.plot.setXRange(-MAX_DISTANCE_MM, MAX_DISTANCE_MM)
        self.plot.setYRange(-MAX_DISTANCE_MM, MAX_DISTANCE_MM)

        # Activation zone circle
        self.activation_circle = self.plot.plot(
            [],
            [],
            pen=pg.mkPen(width=2),
        )

        # Normal LiDAR points
        self.scatter = pg.ScatterPlotItem(
            size=4,
            pen=None,
            brush="w",
        )
        self.plot.addItem(self.scatter)

        # Moving LiDAR points
        self.moving_scatter = pg.ScatterPlotItem(
            size=7,
            pen=None,
            brush="y",
        )
        self.plot.addItem(self.moving_scatter)

        # Centre point / pillar position
        self.origin = pg.ScatterPlotItem(
            x=[0],
            y=[0],
            size=14,
            brush="r",
        )
        self.plot.addItem(self.origin)

        # Status text
        self.status_label = pg.LabelItem(justify="left")
        self.window.addItem(self.status_label, row=0, col=1)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(DISPLAY_UPDATE_MS)

        self.window.closeEvent = self.close_event

    def draw_activation_circle(self):
        angles = np.linspace(0, 2 * np.pi, 200)

        radius = ACTIVATION_MAX_DISTANCE_MM

        x = radius * np.cos(angles)
        y = radius * np.sin(angles)

        self.activation_circle.setData(x, y)

    def update_display(self):
        self.draw_activation_circle()

        # Normal scan points
        points = self.lidar_reader.points
        self.status.point_count = len(points)
        self.status.tick_display()

        if points:
            arr = np.array([(p.x, p.y) for p in points], dtype=float)

            if arr.ndim == 2 and arr.shape[1] == 2:
                # X-axis inverted for display
                self.scatter.setData(-arr[:, 0], arr[:, 1])
            else:
                self.scatter.setData([], [])
        else:
            self.scatter.setData([], [])

        # Moving scan points
        moving_points = self.lidar_reader.moving_points

        if moving_points:
            moving_arr = np.array(
                [(p.x, p.y) for p in moving_points],
                dtype=float,
            )

            if moving_arr.ndim == 2 and moving_arr.shape[1] == 2:
                # X-axis inverted for display
                self.moving_scatter.setData(-moving_arr[:, 0], moving_arr[:, 1])
            else:
                self.moving_scatter.setData([], [])
        else:
            self.moving_scatter.setData([], [])

        self.status_label.setText(
            f"""
            <div style="font-size: 14px;">
            <b>Installation Engine</b><br><br>

            FPS: {self.status.fps:.1f}<br>
            Lidar Hz: {self.status.scan_hz:.1f}<br>
            Points: {self.status.point_count}<br><br>

            Lidar: {"Running" if self.status.lidar_running else "Stopped"}<br>
            Background: {self.status.background_state}<br>
            People: {self.status.people_count}<br><br>

            <b>Pillar</b><br>
            Presence: {self.status.pillar_presence:.2f}<br>
            Distance: {self.status.pillar_distance_mm:.0f} mm<br>
            Activity: {self.status.pillar_activity:.2f}<br><br>

            Activation Zone: {ACTIVATION_MAX_DISTANCE_MM:.0f} mm<br>
            Moving Points: {len(moving_points)}<br>
            OSC: {self.status.osc_state}<br>
            </div>
            """
        )

    def close_event(self, event):
        print("Window closed.")
        self.stop()
        event.accept()

    def stop(self):
        self.running = False
        self.status.app_running = False
        self.lidar_reader.stop()

    async def run(self):
        while self.running:
            self.qt_app.processEvents()
            await asyncio.sleep(0.005)