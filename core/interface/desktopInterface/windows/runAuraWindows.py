"""Executable entrypoint for Aura Windows desktop application.

This module boots Aura's runtime context for the Windows interface and
launches the Tkinter GUI. It is intended to be the target script when
building `aura.exe`.
"""

import os
import traceback

from tkinter import Tk, messagebox, simpledialog

from core.interface.desktopInterface.windows.auraWindowsApp import AuraWindowsApp
from core.interface.desktopInterface.windows.errorDialog import showStandaloneErrorPopup
from core.interface.desktopInterface.windows.windowsRuntimeBootstrap import (
    ENV_KEY_MAP,
    createRuntimeContext,
    shutdown,
    startup,
)

CONFIG_PROMPT_LABELS = {
    "database.host": "Database Host",
    "database.port": "Database Port",
    "database.name": "Database Name",
    "database.user": "Database User",
    "database.password": "Database Password",
    "llm.endpoint": "LLM Endpoint",
    "llm.model": "LLM Model",
}


def _promptForMissingConfigValues(missing_keys: list[str]):
    """Prompt the user for missing config values via text-box dialogs.

    Args:
        missing_keys (list[str]):
            Required config keys that are missing from current runtime config.

    Returns:
        dict[str, str] | None:
            Dictionary of key->value if all prompts were completed, or `None`
            if the user canceled.
    """

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    entered_values = {}
    for key in missing_keys:
        label = CONFIG_PROMPT_LABELS.get(key, key)
        is_secret = key.endswith("password")
        value = simpledialog.askstring(
            "Aura Setup",
            f'Missing configuration: {label}\nEnter a value for "{key}":',
            parent=root,
            show="*" if is_secret else None,
        )

        if value is None:
            messagebox.showwarning(
                "Aura Setup",
                "Startup canceled because required config values were not provided.",
                parent=root,
            )
            root.destroy()
            return None

        entered_values[key] = value.strip()

    messagebox.showinfo(
        "Aura Setup",
        "Configuration values captured. Aura will relaunch now.",
        parent=root,
    )
    root.destroy()
    return entered_values


def _applyConfigOverridesToEnv(overrides: dict[str, str]):
    """Apply runtime config overrides as environment variables.

    Args:
        overrides (dict[str, str]):
            Key/value map using dot-path config keys.
    """

    for key, value in overrides.items():
        env_key = ENV_KEY_MAP.get(key)
        if env_key:
            os.environ[env_key] = str(value)


def main():
    """Initialize runtime dependencies and start the Windows GUI app.

    If required config keys are missing, this function prompts for values
    and retries startup automatically.
    """

    while True:
        context = None
        startup_completed = False
        try:
            context = createRuntimeContext()
            missing_keys = list(getattr(context, "missingConfigKeys", []))

            if missing_keys:
                overrides = _promptForMissingConfigValues(missing_keys)
                if not overrides:
                    return
                _applyConfigOverridesToEnv(overrides)
                continue

            startup(context)
            startup_completed = True
            try:
                app = AuraWindowsApp(context)
                app.run()
            finally:
                startup_completed = False
                shutdown(context)
            return
        except Exception as error:
            details = (
                f"{error}\n\n"
                "Traceback:\n"
                f"{traceback.format_exc()}"
            )
            showStandaloneErrorPopup(details)
            if context is not None and startup_completed:
                try:
                    shutdown(context)
                except Exception:
                    pass
            return


if __name__ == "__main__":
    main()
