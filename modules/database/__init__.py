"""Database adapter package metadata for Aura."""

from modules.database.mysql.mysqlDatabase import MySQLDatabase
from modules.database.sqlite.sqliteDatabase import SQLiteDatabase

MODULE_METADATA = {
    "name": "database",
    "version": "1.0.0",
    "description": "Database adapter package for Aura persistence.",
    "permissions": ("database:connect", "database:read", "database:write"),
    "capabilities": ("database", "mysql", "sqlite"),
}

__all__ = ["MySQLDatabase", "SQLiteDatabase"]

