"""SQLite persistence for Aura weather data."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any


class SQLiteWeatherStore:
    """Persist weather cache, locations, thresholds, alerts, and sensor mappings."""

    def __init__(self, databasePath: str = "aura_weather.sqlite3"):
        self.databasePath = Path(databasePath).expanduser()
        self._lock = RLock()
        self._connection: sqlite3.Connection | None = None

    def initialize(self):
        """Create the database connection and schema."""

        self.databasePath.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.databasePath), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._createSchema()
        return self

    def close(self):
        """Close the database connection."""

        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def upsertCache(self, cacheKey: str, payload: dict[str, Any], source: str, itemType: str, location: str = "", expiresAt: str = ""):
        with self._lock:
            self._execute(
                """
                INSERT INTO weather_cache(cache_key, item_type, location, source, payload, created_at, updated_at, expires_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    item_type=excluded.item_type,
                    location=excluded.location,
                    source=excluded.source,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at,
                    expires_at=excluded.expires_at
                """,
                (
                    cacheKey,
                    itemType,
                    location,
                    source,
                    self._encode(payload),
                    self._now(),
                    self._now(),
                    expiresAt,
                ),
            )

    def getCache(self, cacheKey: str) -> dict[str, Any] | None:
        row = self._fetchOne("SELECT * FROM weather_cache WHERE cache_key = ?", (cacheKey,))
        if row is None:
            return None
        return self._decodeRow(row)

    def listCache(self) -> list[dict[str, Any]]:
        return [self._decodeRow(row) for row in self._fetchAll("SELECT * FROM weather_cache ORDER BY updated_at DESC")]

    def deleteCache(self, cacheKey: str):
        self._execute("DELETE FROM weather_cache WHERE cache_key = ?", (cacheKey,))

    def upsertLocation(self, location: dict[str, Any]):
        self._execute(
            """
            INSERT INTO weather_locations(location_id, name, payload, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(location_id) DO UPDATE SET
                name=excluded.name,
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            (
                str(location.get("locationId") or location.get("location_id") or location.get("name") or ""),
                str(location.get("name") or location.get("label") or ""),
                self._encode(location),
                self._now(),
                self._now(),
            ),
        )

    def listLocations(self) -> list[dict[str, Any]]:
        return [self._decodeRow(row) for row in self._fetchAll("SELECT * FROM weather_locations ORDER BY updated_at DESC")]

    def upsertThreshold(self, threshold: dict[str, Any]):
        self._execute(
            """
            INSERT INTO weather_thresholds(threshold_id, location, metric, payload, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(threshold_id) DO UPDATE SET
                location=excluded.location,
                metric=excluded.metric,
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            (
                str(threshold.get("thresholdId") or threshold.get("id") or ""),
                str(threshold.get("location") or ""),
                str(threshold.get("metric") or ""),
                self._encode(threshold),
                self._now(),
                self._now(),
            ),
        )

    def deleteThreshold(self, thresholdId: str):
        self._execute("DELETE FROM weather_thresholds WHERE threshold_id = ?", (str(thresholdId),))

    def listThresholds(self) -> list[dict[str, Any]]:
        return [self._decodeRow(row) for row in self._fetchAll("SELECT * FROM weather_thresholds ORDER BY updated_at DESC")]

    def recordAlert(self, alert: dict[str, Any]):
        self._execute(
            """
            INSERT INTO weather_alerts(alert_id, severity, payload, created_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(alert_id) DO UPDATE SET
                severity=excluded.severity,
                payload=excluded.payload
            """,
            (
                str(alert.get("alertId") or alert.get("id") or ""),
                str(alert.get("severity") or "LOW"),
                self._encode(alert),
                self._now(),
            ),
        )

    def listAlerts(self) -> list[dict[str, Any]]:
        return [self._decodeRow(row) for row in self._fetchAll("SELECT * FROM weather_alerts ORDER BY created_at DESC")]

    def upsertSensorMapping(self, mapping: dict[str, Any]):
        self._execute(
            """
            INSERT INTO weather_sensor_mappings(sensor_id, sensor_type, location, payload, updated_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(sensor_id) DO UPDATE SET
                sensor_type=excluded.sensor_type,
                location=excluded.location,
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            (
                str(mapping.get("sensorId") or mapping.get("sensor_id") or ""),
                str(mapping.get("sensorType") or mapping.get("sensor_type") or ""),
                str(mapping.get("location") or ""),
                self._encode(mapping),
                self._now(),
            ),
        )

    def listSensorMappings(self) -> list[dict[str, Any]]:
        return [self._decodeRow(row) for row in self._fetchAll("SELECT * FROM weather_sensor_mappings ORDER BY updated_at DESC")]

    def _createSchema(self):
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS weather_cache (
                cache_key TEXT PRIMARY KEY,
                item_type TEXT NOT NULL,
                location TEXT NOT NULL,
                source TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS weather_locations (
                location_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS weather_thresholds (
                threshold_id TEXT PRIMARY KEY,
                location TEXT NOT NULL,
                metric TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS weather_alerts (
                alert_id TEXT PRIMARY KEY,
                severity TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS weather_sensor_mappings (
                sensor_id TEXT PRIMARY KEY,
                sensor_type TEXT NOT NULL,
                location TEXT NOT NULL,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

    def _execute(self, sql: str, params: tuple[Any, ...] = ()):
        connection = self._requireConnection()
        with self._lock:
            connection.execute(sql, params)
            connection.commit()

    def _fetchOne(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        connection = self._requireConnection()
        with self._lock:
            row = connection.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def _fetchAll(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        connection = self._requireConnection()
        with self._lock:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def _requireConnection(self) -> sqlite3.Connection:
        if self._connection is None:
            return self.initialize()._connection  # type: ignore[return-value]
        return self._connection

    @staticmethod
    def _encode(value: dict[str, Any]) -> str:
        return json.dumps(value or {}, ensure_ascii=True, sort_keys=True)

    @staticmethod
    def _decodeRow(row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row or {})
        raw = payload.get("payload")
        if isinstance(raw, str):
            try:
                payload.update(json.loads(raw or "{}"))
            except Exception:
                payload["payload"] = {}
        return payload

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
