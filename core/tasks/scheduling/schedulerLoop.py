"""Background scheduler loop for Aura tasks."""

from __future__ import annotations

import time


class SchedulerLoop:
    """Poll the task queue on a fixed cadence."""

    def __init__(self, taskManager=None, tickIntervalSeconds: float = 0.5):
        self.taskManager = taskManager
        self.tickIntervalSeconds = float(tickIntervalSeconds or 0.5)
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def run(self, threadControl=None):
        self.running = True
        while self.running:
            if threadControl is not None:
                if threadControl.should_stop():
                    break
                threadControl.wait_if_paused()
            if self.taskManager is not None:
                self.taskManager.tick()
            time.sleep(self.tickIntervalSeconds)
