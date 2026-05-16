"""Database selection helpers for Aura runtime startup."""

from modules.database.mysql.mysqlDatabase import MySQLDatabase
from modules.database.sqlite.sqliteDatabase import SQLiteDatabase


def createDatabaseWithFallback(context):
    """
    Create and initialize the configured database, falling back to SQLite.

    MySQL remains the preferred database. SQLite is used only when MySQL cannot
    connect or initialize, allowing local interfaces to open for development.
    """

    logger = context.logger.getChild("DatabaseFactory") if context.logger else None

    try:
        database = MySQLDatabase(context)
        database.connect()
        database.initialize()
        return database
    except Exception as error:
        if logger:
            logger.error(f"MySQL unavailable; falling back to SQLite: {error}")

    database = SQLiteDatabase(context)
    database.connect()
    database.initialize()
    return database
