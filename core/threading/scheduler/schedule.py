"""Core implementation for `schedule` in the Aura assistant project."""

import time
from typing import Callable, Optional


class Schedule:
    """
    Represents a scheduled job within the Aura system.

    A Schedule defines when a function should be executed and
    optionally how often it should repeat.

    Schedules are managed and executed by the Scheduler.
    """

    def __init__(
        self,
        name: str,
        target: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        interval: Optional[float] = None,
        run_at: Optional[float] = None,
    ):
        """
        Initialize a new schedule.

        Args:
            name (str):
                Unique schedule name.

            target (Callable):
                Function to execute.

            args (tuple):
                Positional arguments passed to the function.

            kwargs (dict | None):
                Keyword arguments passed to the function.

            interval (float | None):
                Repeat interval in seconds.

            run_at (float | None):
                Unix timestamp indicating when to run once.
        """

        self.name = name
        """Name of the schedule."""

        self.target = target
        """Function that will be executed."""

        self.args = args
        """Positional arguments for the target function."""

        self.kwargs = kwargs or {}
        """Keyword arguments for the target function."""

        self.interval = interval
        """Repeat interval in seconds."""

        self.run_at = run_at
        """Unix timestamp for single execution."""

        self.last_run = None
        """Timestamp of the last execution."""

        self.enabled = True
        """Whether this schedule is active."""

    # --------------------------------------------------
    # Execution Logic
    # --------------------------------------------------

    def shouldRun(self) -> bool:
        """
        Determine whether the schedule should execute.

        Returns:
            bool
        """

        if not self.enabled:
            return False

        now = time.time()

        # One-time schedule
        if self.run_at is not None:
            if self.last_run is None and now >= self.run_at:
                return True

        # Repeating schedule
        if self.interval is not None:
            if self.last_run is None:
                return True

            if now - self.last_run >= self.interval:
                return True

        return False

    def markRan(self):
        """
        Record the current time as the last execution.
        """

        self.last_run = time.time()

    # --------------------------------------------------
    # Debug Helpers
    # --------------------------------------------------

    def __repr__(self):
        """
        Return a debug-friendly representation of the schedule.
        """

        return f"Schedule(name={self.name}, enabled={self.enabled})"
