"""
Aura Module Loader

This component automatically discovers and loads modules
from the `modules/` directory at runtime.

Modules can register themselves with the system by exposing
a `register(context)` function.

This allows Aura to support a plugin-style architecture
where new features can be added simply by placing new
modules in the modules directory.
"""

import importlib
import pkgutil


class ModuleLoader:
    """
    Automatically loads Aura modules.

    The ModuleLoader scans the `modules` package for available
    submodules and imports them dynamically. If a module exposes
    a `register()` function, it will be executed to allow the
    module to register itself with the RuntimeContext.
    """

    def __init__(self, context):
        """
        Initialize the module loader.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        self.context = context
        self.logger = context.logger.getChild("ModuleLoader") if context.logger else None

        if self.logger:
            self.logger.info("Initialized")

    # --------------------------------------------------
    # Module Discovery
    # --------------------------------------------------

    def loadModules(self):
        """
        Discover and load modules from the `modules` package.

        Each discovered module is imported dynamically. If the
        module provides a `register(context)` function, it will
        be executed to allow the module to register itself with
        the runtime system.
        """

        if self.logger:
            self.logger.info("Loading modules")

        import modules

        # Iterate through all modules in the modules package
        for module_info in pkgutil.iter_modules(modules.__path__):

            module_name = module_info.name

            # Skip base module directory
            if module_name == "base":
                continue

            try:

                # Dynamically import module
                module = importlib.import_module(f"modules.{module_name}")

                # Allow module to register itself
                if hasattr(module, "register"):

                    module.register(self.context)

                    if self.logger:
                        self.logger.info(f"Loaded module: {module_name}")

            except Exception as error:

                if self.logger:
                    self.logger.error(
                        f"Failed to load module '{module_name}': {error}"
                    )
