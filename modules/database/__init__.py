"""Database adapter package metadata for Aura."""

from modules.database.sqlite.sqliteDatabase import SQLiteDatabase

try:
    from modules.database.mysql.mysqlDatabase import MySQLDatabase
except ModuleNotFoundError:  # pragma: no cover - optional MySQL dependency
    MySQLDatabase = None

MODULE_METADATA = {
    "name": "database",
    "version": "1.1.0",
    "description": "Database adapter package for Aura persistence.",
    "permissions": ("database:connect", "database:read", "database:write"),
    "capabilities": ("database", "mysql", "sqlite"),
}

__all__ = ["MySQLDatabase", "SQLiteDatabase"]

