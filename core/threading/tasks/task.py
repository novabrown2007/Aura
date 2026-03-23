"""Core implementation for `task` in the Aura assistant project."""

from typing import Callable, Optional


class Task:
    """
    Represents a unit of work within the Aura system.

    Tasks are used by the TaskManager to execute background operations
    such as API calls, automation jobs, data processing, or other
    asynchronous work.

    Each task contains a callable target function along with optional
    arguments and metadata.

    Example:
        task = Task(
            name="FetchWeather",
            target=weather_module.fetch_weather,
            args=("Hamilton",)
        )
    """

    def __init__(
        self,
        name: str,
        target: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
    ):
        """
        Initialize a new task.

        Args:
            name (str):
                Human-readable task name.

            target (Callable):
                Function to execute when the task runs.

            args (tuple):
                Positional arguments for the target function.

            kwargs (dict | None):
                Keyword arguments for the target function.
        """

        self.name = name
        """Name of the task."""

        self.target = target
        """Function that will be executed."""

        self.args = args
        """Positional arguments for the target."""

        self.kwargs = kwargs or {}
        """Keyword arguments for the target."""

        self.completed = False
        """Indicates whether the task has completed."""

        self.result = None
        """Stores the result of the task if applicable."""

        self.error = None
        """Stores any exception raised during execution."""

    # --------------------------------------------------
    # Execution
    # --------------------------------------------------

    def run(self):
        """
        Execute the task.

        The target function will be called with the provided
        arguments and keyword arguments.

        Any raised exception will be captured and stored.
        """

        try:
            self.result = self.target(*self.args, **self.kwargs)
            self.completed = True
        except Exception as e:
            self.error = e
            self.completed = True

    # --------------------------------------------------
    # Debug Helpers
    # --------------------------------------------------

    def __repr__(self):
        """
        Return a debug-friendly representation of the task.
        """

        status = "completed" if self.completed else "pending"

        return f"Task(name={self.name}, status={status})"
