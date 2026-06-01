"""SQLite cache for Spotify module state and search results."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class SpotifyCacheStore:
    """Persist cached Spotify data locally."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or "spotify_cache.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensureSchema()

    def _connect(self):
        return sqlite3.connect(str(self.path))

    def _ensureSchema(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS playback_snapshots (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS playlists (
                    playlist_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS recent_tracks (
                    track_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS album_art (
                    art_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )

    def savePlaybackSnapshot(self, key: str, payload: dict[str, object]):
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO playback_snapshots (cache_key, payload) VALUES (?, ?)",
                (str(key), json.dumps(payload or {})),
            )

    def loadPlaybackSnapshot(self, key: str):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM playback_snapshots WHERE cache_key = ?",
                (str(key),),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def saveSearchResult(self, key: str, payload: dict[str, object]):
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO search_cache (cache_key, payload) VALUES (?, ?)",
                (str(key), json.dumps(payload or {})),
            )

    def loadSearchResult(self, key: str):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM search_cache WHERE cache_key = ?",
                (str(key),),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def savePlaylists(self, playlists: list[dict[str, object]]):
        with self._connect() as connection:
            for playlist in playlists or []:
                playlist_id = str(playlist.get("playlistId") or playlist.get("id") or "")
                if not playlist_id:
                    continue
                connection.execute(
                    "INSERT OR REPLACE INTO playlists (playlist_id, payload) VALUES (?, ?)",
                    (playlist_id, json.dumps(playlist)),
                )

    def loadPlaylists(self):
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM playlists ORDER BY playlist_id ASC").fetchall()
        return [json.loads(row[0]) for row in rows]

    def saveRecentTrack(self, trackId: str, payload: dict[str, object]):
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO recent_tracks (track_id, payload) VALUES (?, ?)",
                (str(trackId), json.dumps(payload or {})),
            )

    def loadRecentTracks(self):
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM recent_tracks ORDER BY track_id DESC").fetchall()
        return [json.loads(row[0]) for row in rows]

    def saveAlbumArtReference(self, key: str, payload: dict[str, object]):
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO album_art (art_key, payload) VALUES (?, ?)",
                (str(key), json.dumps(payload or {})),
            )

    def loadAlbumArtReference(self, key: str):
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM album_art WHERE art_key = ?", (str(key),)).fetchone()
        return json.loads(row[0]) if row else None
