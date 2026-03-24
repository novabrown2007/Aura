"""System module registration for Aura."""

from modules.system.system import System


def register(context):
    """
    Register the system lifecycle module with the runtime context.

    Interfaces and future command layers can call into this module to request
    shutdown, restart, or config reload behavior without depending on `main.py`
    details directly.
    """

    context.system = System(context)
