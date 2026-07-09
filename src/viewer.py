import asyncio

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

from src.config import MAX_DISTANCE_MM, DISPLAY_UPDATE_MS


class Viewer:
    def __init__(self, lidar_reader, status):
        self.running = True
        self.lidar_reader = lidar_reader
        self.status = status

        self.qt_app = QtWidgets.QApplication([])

        self.window = pg.GraphicsLayoutWidget(
            show=True,
            title="RPLIDAR C1 Installation Viewer"
        )
        self.window.resize(1100, 900)

        self.plot = self.window.addPlot(row=0, col=0)
        self.plot.setAspectLocked(True)
        self.plot.showGrid(x=True, y=True)
        self.plot.setXRange(-MAX_DISTANCE_MM, MAX_DISTANCE_MM)
        self.plot.setYRange(-MAX_DISTANCE_MM, MAX_DISTANCE_MM)

        self.scatter = pg.ScatterPlotItem(size=4, pen=None, brush="w")
        self.plot.addItem(self.scatter)

        self.origin = pg.ScatterPlotItem(x=[0], y=[0], size=14, brush="r")
        self.plot.addItem(self.origin)

        self.status_label = pg.LabelItem(justify="left")
        self.window.addItem(self.status_label, row=0, col=1)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(DISPLAY_UPDATE_MS)

        self.window.closeEvent = self.close_event

    def update_display(self):
        points = self.lidar_reader.points
        self.status.point_count = len(points)
        self.status.tick_display()

        if points:
            arr = np.array([(p.x, p.y) for p in points], dtype=float)

            if arr.ndim == 2 and arr.shape[1] == 2:
                self.scatter.setData(arr[:, 0], arr[:, 1])
        else:
            self.scatter.setData([], [])

        self.status_label.setText(
            f"""
            <div style="font-size: 14px;">
            <b>Installation Engine</b><br><br>

            FPS: {self.status.fps:.1f}<br>
            Lidar Hz: {self.status.scan_hz:.1f}<br>
            Points: {self.status.point_count}<br><br>

            Lidar: {"Running" if self.status.lidar_running else "Stopped"}<br>
            Background: {self.status.background_state}<br>
            People: {self.status.people_count}<br>
            Pillar Presence: {self.status.pillar_presence:.2f}<br>
Pillar Distance: {self.status.pillar_distance_mm:.0f} mm<br>
Pillar Activity: {self.status.pillar_activity:.2f}<br>
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