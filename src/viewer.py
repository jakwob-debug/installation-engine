import asyncio

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

from src.config import MAX_DISTANCE_MM, DISPLAY_UPDATE_MS


class Viewer:
    def __init__(self, lidar_reader):
        self.running = True
        self.lidar_reader = lidar_reader

        self.qt_app = QtWidgets.QApplication([])

        self.window = pg.GraphicsLayoutWidget(
            show=True,
            title="RPLIDAR C1 Installation Viewer"
        )
        self.window.resize(900, 900)

        self.plot = self.window.addPlot()
        self.plot.setAspectLocked(True)
        self.plot.showGrid(x=True, y=True)
        self.plot.setXRange(-MAX_DISTANCE_MM, MAX_DISTANCE_MM)
        self.plot.setYRange(-MAX_DISTANCE_MM, MAX_DISTANCE_MM)

        self.scatter = pg.ScatterPlotItem(size=4, pen=None, brush="w")
        self.plot.addItem(self.scatter)

        self.origin = pg.ScatterPlotItem(x=[0], y=[0], size=14, brush="r")
        self.plot.addItem(self.origin)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(DISPLAY_UPDATE_MS)

        self.window.closeEvent = self.close_event

    def update_display(self):
        points = self.lidar_reader.points

        if not points:
            return

        arr = np.array(points, dtype=float)

        if arr.ndim == 2 and arr.shape[1] == 2:
            self.scatter.setData(arr[:, 0], arr[:, 1])

    def close_event(self, event):
        print("Window closed.")
        self.stop()
        event.accept()

    def stop(self):
        self.running = False
        self.lidar_reader.stop()

    async def run(self):
        while self.running:
            self.qt_app.processEvents()
            await asyncio.sleep(0.005)
