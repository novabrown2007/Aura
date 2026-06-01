"""Compatibility package for Aura task orchestration."""

from core.tasks.taskManager import TaskManager
from .task import Task

__all__ = ["Task", "TaskManager"]

