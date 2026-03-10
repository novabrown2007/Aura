import time
from typing import Dict, Optional
from .schedule import Schedule
from core.threading.tasks.task import Task


class Scheduler:
    """
    Scheduler engine responsible for executing scheduled jobs.

    The Scheduler maintains a collection of Schedule objects and
    periodically checks whether they should run.

    When a schedule becomes due, the scheduler submits the task
    to the TaskManager for execution.
    """

    def __init__(self, context, tick_interval: float = 1.0):
        """
        Initialize the scheduler.

        Args:
            context (RuntimeContext):
                Global runtime context.

            tick_interval (float):
                Time in seconds between scheduler checks.
        """

        self.context = context
        self.tick_interval = tick_interval

        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Scheduler")

        self.schedules: Dict[str, Schedule] = {}
        """Dictionary of schedules indexed by name."""

        self.running = False

        if self.logger:
            self.logger.info(f"scheduler.py has been initialized.")

    # --------------------------------------------------
    # Schedule Management
    # --------------------------------------------------

    def addSchedule(self, schedule: Schedule):
        """
        Register a schedule.

        Args:
            schedule (Schedule)
        """

        if schedule.name in self.schedules:
            raise RuntimeError(f"Schedule '{schedule.name}' already exists.")

        self.schedules[schedule.name] = schedule

        if self.logger:
            self.logger.debug(f"Schedule added: {schedule.name}")

    def removeSchedule(self, name: str):
        """
        Remove a schedule.

        Args:
            name (str)
        """

        if name in self.schedules:
            del self.schedules[name]

            if self.logger:
                self.logger.debug(f"Schedule removed: {name}")

    def getSchedule(self, name: str) -> Optional[Schedule]:
        """
        Retrieve a schedule by name.
        """

        return self.schedules.get(name)

    def listSchedules(self):
        """
        List all schedules.
        """

        return list(self.schedules.keys())

    # --------------------------------------------------
    # Scheduler Loop
    # --------------------------------------------------

    def start(self):
        """
        Start the scheduler loop in a background thread.
        """

        if self.running:
            return

        self.running = True

        thread = self.context.threader.createThread(
            name="Scheduler",
            target=self._runLoop,
            daemon=True
        )

        thread.start()

        if self.logger:
            self.logger.info("Scheduler started")

    def stop(self):
        """
        Stop the scheduler loop.
        """

        self.running = False

        if self.logger:
            self.logger.info("Scheduler stopped")

    def _runLoop(self, threadControl=None):
        """
        Main scheduler loop.
        """

        while self.running:

            if threadControl:
                if threadControl.should_stop():
                    break

                threadControl.wait_if_paused()

            self._tick()

            time.sleep(self.tick_interval)

    # --------------------------------------------------
    # Tick Execution
    # --------------------------------------------------

    def _tick(self):
        """
        Check schedules and execute those that are due.
        """

        for schedule in self.schedules.values():

            if schedule.should_run():

                if self.logger:
                    self.logger.debug(f"Running schedule: {schedule.name}")

                task = Task(
                    name=f"schedule_{schedule.name}",
                    target=schedule.target,
                    args=schedule.args,
                    kwargs=schedule.kwargs
                )

                self.context.taskManager.submitTask(task)

                schedule.mark_ran()
