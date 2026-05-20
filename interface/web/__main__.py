"""Run the Aura web interface directly."""

from main import buildRuntimeContext, shutdown, startup
from interface.web import AuraWebApp


def main():
    context = buildRuntimeContext()
    startup(context)
    app = AuraWebApp(context)
    try:
        app.serve_forever()
    finally:
        shutdown(context)
        if context.logger:
            context.logger.close()


if __name__ == "__main__":
    main()
