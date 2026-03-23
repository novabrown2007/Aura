"""Core implementation for `threadingManager` in the Aura assistant project."""

import threading
from typing import Callable, Optional


class ThreadControl:
    """
    Control object associated with a managed thread.

    Provides pause, resume, and stop signals that the thread
    can check during execution.
    """

    def __init__(self):
        """Initialize `ThreadControl` with required dependencies and internal state."""
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()

        # Start unpaused
        self.pause_event.set()

    def wait_if_paused(self):
        """Block execution while the thread is paused."""
        self.pause_event.wait()

    def should_stop(self) -> bool:
        """Check whether the thread should terminate."""
        return self.stop_event.is_set()


class ThreadingManager:
    """
    Manages all threads within the Aura assistant.

    The ThreadingManager provides centralized control over thread
    creation, lifecycle management, and thread coordination.

    Threads created through this manager support pause, resume,
    and stop signals through a cooperative control object.
    """

    def __init__(self, context):
        """
        Initialize the threading manager.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        self.context = context
        self.logger = None

        if context.logger:
            self.logger = context.logger.getChild("Threading")

        self.threads: dict[str, threading.Thread] = {}
        self.controls: dict[str, ThreadControl] = {}

        if self.logger:
            self.logger.info(f"Initialized.")

    # --------------------------------------------------
    # Thread Creation
    # --------------------------------------------------

    def createThread(
        self,
        name: str,
        target: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        daemon: bool = True,
    ) -> threading.Thread:
        """
        Create and register a managed thread.

        Args:
            name (str):
                Unique thread name.

            target (Callable):
                Function executed by the thread.

            args (tuple):
                Positional arguments for the target.

            kwargs (dict | None):
                Keyword arguments for the target.

            daemon (bool):
                Whether the thread runs as a daemon.

        Returns:
            threading.Thread
        """

        if name in self.threads:
            raise RuntimeError(f"Thread '{name}' already exists.")

        kwargs = kwargs or {}

        control = ThreadControl()
        self.controls[name] = control

        # Inject control into thread kwargs
        kwargs["threadControl"] = control

        thread = threading.Thread(
            name=name,
            target=target,
            args=args,
            kwargs=kwargs,
            daemon=daemon,
        )

        self.threads[name] = thread

        if self.logger:
            self.logger.debug(f"Thread created: {name}")

        return thread

    # --------------------------------------------------
    # Thread Access
    # --------------------------------------------------

    def listThreads(self) -> list[str]:
        """
        List all registered threads.

        Returns:
            list[str]
        """
        return list(self.threads.keys())

    def getThread(self, name: str) -> Optional[threading.Thread]:
        """
        Retrieve a thread by name.

        Args:
            name (str)

        Returns:
            threading.Thread | None
        """
        return self.threads.get(name)

    # --------------------------------------------------
    # Thread Control
    # --------------------------------------------------

    def pauseThread(self, name: str):
        """
        Pause a running thread.

        The thread must cooperatively call `wait_if_paused()` to respond.
        """

        control = self.controls.get(name)

        if control is None:
            raise RuntimeError(f"Thread '{name}' does not exist.")

        control.pause_event.clear()

        if self.logger:
            self.logger.info(f"Thread paused: {name}")

    def resumeThread(self, name: str):
        """
        Resume a paused thread.
        """

        control = self.controls.get(name)

        if control is None:
            raise RuntimeError(f"Thread '{name}' does not exist.")

        control.pause_event.set()

        if self.logger:
            self.logger.info(f"Thread resumed: {name}")

    def stopThread(self, name: str):
        """
        Signal a thread to stop execution.
        """

        control = self.controls.get(name)

        if control is None:
            raise RuntimeError(f"Thread '{name}' does not exist.")

        control.stop_event.set()

        if self.logger:
            self.logger.info(f"Thread stop requested: {name}")

    # --------------------------------------------------
    # Shutdown
    # --------------------------------------------------

    def stopAllThreads(self):
        """
        Signal all threads to stop.
        """

        for name in self.controls:
            self.stopThread(name)

    def joinAll(self):
        """
        Wait for all threads to finish.
        """

        for name, thread in self.threads.items():
            if self.logger:
                self.logger.debug(f"Joining thread: {name}")

            thread.join()
