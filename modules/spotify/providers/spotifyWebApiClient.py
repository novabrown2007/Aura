"""Spotify Web API client with PKCE authentication."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


@dataclass
class SpotifyTokens:
    """Persisted Spotify token state."""

    access_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0.0
    token_type: str = "Bearer"
    scope: str = ""

    def is_valid(self) -> bool:
        return bool(self.access_token) and time.time() < max(0.0, float(self.expires_at) - 60.0)

    def asDict(self) -> dict[str, object]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": float(self.expires_at),
            "token_type": self.token_type,
            "scope": self.scope,
        }

    @classmethod
    def fromDict(cls, payload: dict[str, Any] | None):
        payload = dict(payload or {})
        return cls(
            access_token=str(payload.get("access_token") or ""),
            refresh_token=str(payload.get("refresh_token") or ""),
            expires_at=float(payload.get("expires_at") or 0.0),
            token_type=str(payload.get("token_type") or "Bearer"),
            scope=str(payload.get("scope") or ""),
        )


class SpotifyWebApiClient:
    """Minimal Spotify Web API client for desktop PKCE auth."""

    AUTHORIZATION_URL = "https://accounts.spotify.com/authorize"
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    API_BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, context=None):
        self.context = context
        self.client_id = ""
        self.redirect_uri = "http://127.0.0.1:53682/callback"
        self.scopes = [
            "user-read-playback-state",
            "user-modify-playback-state",
            "playlist-read-private",
            "playlist-modify-private",
            "playlist-modify-public",
            "user-read-private",
        ]
        self.token_cache_path = Path("spotify_auth.json")
        self.auto_authorize = False
        self.open_browser = True
        self.tokens = SpotifyTokens()
        self.profile: dict[str, Any] = {}

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        self.client_id = str(self._readConfig("spotify.api.clientId", "") or self._readConfig("spotify.clientId", "") or "").strip()
        self.redirect_uri = str(self._readConfig("spotify.api.redirectUri", self.redirect_uri) or self.redirect_uri).strip()
        self.scopes = self._readScopes(self._readConfig("spotify.api.scopes", self.scopes))
        self.token_cache_path = Path(str(self._readConfig("spotify.api.tokenCachePath", self.token_cache_path) or self.token_cache_path))
        self.auto_authorize = bool(self._readConfig("spotify.api.autoAuthorize", False))
        self.open_browser = bool(self._readConfig("spotify.api.openBrowser", True))
        self.tokens = self._loadTokens()
        if not self.tokens.is_valid():
            self._refreshOrAuthorize(interactive=False)
        return self

    def isConfigured(self) -> bool:
        return bool(self.client_id and self.redirect_uri)

    def isAvailable(self) -> bool:
        return bool(self.client_id) and (self.tokens.is_valid() or bool(self.tokens.refresh_token))

    def connect(self, interactive: bool | None = None):
        if not self.client_id:
            raise RuntimeError("Spotify client ID is not configured.")
        interactive = self.auto_authorize if interactive is None else bool(interactive)
        if self.tokens.is_valid():
            self._loadProfile()
            return self._buildConnectionState("CONNECTED")
        if self.tokens.refresh_token:
            self._refreshAccessToken()
            self._loadProfile()
            return self._buildConnectionState("CONNECTED")
        if interactive:
            self._authorizeInteractive()
            self._loadProfile()
            return self._buildConnectionState("CONNECTED")
        self.profile = {}
        return self._buildConnectionState("DISCONNECTED", "Spotify is not authenticated.")

    def disconnect(self, reason: str = ""):
        self.tokens = SpotifyTokens()
        self.profile = {}
        self._saveTokens(self.tokens)
        return self._buildConnectionState("DISCONNECTED", reason or "Disconnected")

    def refreshToken(self):
        self._refreshAccessToken()
        self._loadProfile()
        return self._buildConnectionState("CONNECTED")

    def getConnectionState(self):
        state = self._buildConnectionState("CONNECTED" if self.tokens.is_valid() else "DISCONNECTED")
        if self.profile:
            state["metadata"]["profile"] = dict(self.profile)
        return state

    def getCurrentPlayback(self):
        payload = self._request("GET", "/me/player")
        return self._normalizePlayback(payload)

    def getNowPlaying(self):
        return self.getCurrentPlayback()

    def searchTracks(self, query: str):
        payload = self._request("GET", "/search", params={"q": query, "type": "track", "limit": 10})
        return self._normalizeSearch(query, payload, kind="tracks")

    def searchPlaylists(self, query: str):
        payload = self._request("GET", "/search", params={"q": query, "type": "playlist", "limit": 10})
        return self._normalizeSearch(query, payload, kind="playlists")

    def searchArtists(self, query: str):
        payload = self._request("GET", "/search", params={"q": query, "type": "artist", "limit": 10})
        return self._normalizeSearch(query, payload, kind="artists")

    def searchAlbums(self, query: str):
        payload = self._request("GET", "/search", params={"q": query, "type": "album", "limit": 10})
        return self._normalizeSearch(query, payload, kind="albums")

    def listPlaylists(self):
        payload = self._request("GET", "/me/playlists", params={"limit": 50})
        items = []
        for playlist in payload.get("items", []) or []:
            items.append(self._normalizePlaylist(playlist))
        return items

    def listDevices(self):
        payload = self._request("GET", "/me/player/devices")
        items = []
        for device in payload.get("devices", []) or []:
            items.append(self._normalizeDevice(device))
        return items

    def playTrack(self, trackId: str = "", query: str = "", playlistId: str = "", artist: str = "", playNow: bool = True):
        track = self._resolveTrack(trackId=trackId, query=query, playlistId=playlistId)
        if track is None:
            payload = {}
            if trackId:
                payload = {"uris": [self._normalizeTrackUri(trackId)]}
            elif query:
                search = self.searchTracks(query)
                tracks = search.get("tracks") or []
                if tracks:
                    payload = {"uris": [tracks[0].get("uri") or self._normalizeTrackUri(tracks[0].get("trackId") or query)]}
            if playlistId and not payload:
                playlist = self._resolvePlaylist(playlistId=playlistId, query=query)
                if playlist:
                    payload = {"context_uri": playlist.get("uri") or self._playlistUri(playlist.get("playlistId") or playlistId)}
            if not payload:
                raise RuntimeError("No matching Spotify track found.")
            self._request("PUT", "/me/player/play", json_body=payload)
            return self.getCurrentPlayback()

        payload = {"uris": [track["uri"]]}
        self._request("PUT", "/me/player/play", json_body=payload)
        return self.getCurrentPlayback()

    def playPlaylist(self, playlistId: str = "", query: str = "", shuffle: bool = False):
        playlist = self._resolvePlaylist(playlistId=playlistId, query=query)
        if playlist is None:
            raise RuntimeError("No matching Spotify playlist found.")
        self._request("PUT", "/me/player/play", json_body={"context_uri": playlist.get("uri") or self._playlistUri(playlist.get("playlistId") or playlistId)})
        if shuffle:
            self._request("PUT", "/me/player/shuffle", params={"state": "true"})
        return self.getCurrentPlayback()

    def pause(self):
        self._request("PUT", "/me/player/pause")
        return self.getCurrentPlayback()

    def resume(self):
        self._request("PUT", "/me/player/play")
        return self.getCurrentPlayback()

    def nextTrack(self):
        self._request("POST", "/me/player/next")
        return self.getCurrentPlayback()

    def previousTrack(self):
        self._request("POST", "/me/player/previous")
        return self.getCurrentPlayback()

    def seek(self, positionMs: int):
        self._request("PUT", "/me/player/seek", params={"position_ms": int(positionMs or 0)})
        return self.getCurrentPlayback()

    def seekBy(self, deltaMs: int):
        playback = self.getCurrentPlayback()
        return self.seek(int(playback.get("progress") or 0) + int(deltaMs or 0))

    def setVolume(self, volume: int):
        self._request("PUT", "/me/player/volume", params={"volume_percent": max(0, min(100, int(volume or 0)))})
        return self.getCurrentPlayback()

    def setPlaybackSpeed(self, speed: float):
        raise NotImplementedError("Spotify Web API does not expose playback speed control.")

    def transferPlayback(self, deviceId: str):
        self._request("PUT", "/me/player", json_body={"device_ids": [str(deviceId)], "play": True})
        return self.getCurrentPlayback()

    def snapshot(self):
        return {
            "connection": self.getConnectionState(),
            "playback": self.getCurrentPlayback(),
            "devices": self.listDevices(),
            "playlists": self.listPlaylists(),
        }

    def shutdown(self):
        return None

    def _authorizeInteractive(self):
        verifier = self._generateVerifier()
        challenge = self._codeChallenge(verifier)
        state = secrets.token_urlsafe(16)
        callback_result = {}

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self_inner):
                nonlocal callback_result
                parsed = urllib.parse.urlparse(self_inner.path)
                if parsed.path != urllib.parse.urlparse(self.redirect_uri).path:
                    self_inner.send_response(404)
                    self_inner.end_headers()
                    return
                params = urllib.parse.parse_qs(parsed.query)
                if "error" in params:
                    callback_result = {"error": params.get("error", ["authorization_failed"])[0]}
                else:
                    callback_result = {
                        "code": params.get("code", [""])[0],
                        "state": params.get("state", [""])[0],
                    }
                self_inner.send_response(200)
                self_inner.send_header("Content-Type", "text/html; charset=utf-8")
                self_inner.end_headers()
                self_inner.wfile.write(b"<html><body><h3>Spotify authorization complete.</h3>You can close this tab and return to Aura.</body></html>")

            def log_message(self_inner, *_args):  # pragma: no cover
                return None

        server = ThreadingHTTPServer(("127.0.0.1", urllib.parse.urlparse(self.redirect_uri).port), CallbackHandler)
        server.timeout = 1.0
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        auth_url = self._buildAuthUrl(challenge, state)
        if self.open_browser:
            webbrowser.open(auth_url)
        try:
            deadline = time.time() + 180.0
            while time.time() < deadline:
                if callback_result:
                    break
                server.handle_request()
            if "error" in callback_result:
                raise RuntimeError(f"Spotify authorization failed: {callback_result['error']}")
            code = callback_result.get("code")
            returned_state = callback_result.get("state")
            if not code or returned_state != state:
                raise RuntimeError("Spotify authorization did not return a valid code.")
            self._exchangeAuthorizationCode(code, verifier)
        finally:
            try:
                server.shutdown()
            except Exception:
                pass

    def _exchangeAuthorizationCode(self, code: str, verifier: str):
        payload = {
            "client_id": self.client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": verifier,
        }
        response = self._tokenRequest(payload)
        self._updateTokens(response)

    def _refreshAccessToken(self):
        if not self.tokens.refresh_token:
            raise RuntimeError("Spotify refresh token is not available.")
        payload = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": self.tokens.refresh_token,
        }
        response = self._tokenRequest(payload)
        self._updateTokens(response)

    def _tokenRequest(self, payload: dict[str, Any]):
        body = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(
            self.TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read().decode("utf-8")
        return json.loads(data or "{}")

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None):
        if not self.tokens.is_valid():
            if self.tokens.refresh_token:
                self._refreshAccessToken()
            elif self.auto_authorize and self.client_id:
                self._authorizeInteractive()
            else:
                raise RuntimeError("Spotify is not authenticated.")
        params = dict(params or {})
        url = self.API_BASE_URL + path
        if params:
            url += "?" + urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
        data = None
        headers = {"Authorization": f"Bearer {self.tokens.access_token}"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read().decode("utf-8")
                if not content:
                    return {}
                return json.loads(content)
        except urllib.error.HTTPError as error:
            if error.code == 204:
                return {}
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Spotify API request failed ({method} {path}): {error.code} {body}") from error

    def _updateTokens(self, payload: dict[str, Any]):
        self.tokens.access_token = str(payload.get("access_token") or self.tokens.access_token)
        self.tokens.refresh_token = str(payload.get("refresh_token") or self.tokens.refresh_token)
        self.tokens.expires_at = time.time() + float(payload.get("expires_in") or 3600)
        self.tokens.token_type = str(payload.get("token_type") or "Bearer")
        self.tokens.scope = str(payload.get("scope") or self.tokens.scope)
        self._saveTokens(self.tokens)

    def _loadProfile(self):
        try:
            self.profile = dict(self._request("GET", "/me") or {})
        except Exception:
            self.profile = {}

    def _loadTokens(self):
        if not self.token_cache_path.exists():
            return SpotifyTokens(
                access_token=str(self._readConfig("spotify.api.accessToken", "") or self._readConfig("spotify.accessToken", "") or ""),
                refresh_token=str(self._readConfig("spotify.api.refreshToken", "") or self._readConfig("spotify.refreshToken", "") or ""),
                expires_at=float(self._readConfig("spotify.api.expiresAt", 0) or 0),
            )
        try:
            with self.token_cache_path.open("r", encoding="utf-8") as handle:
                return SpotifyTokens.fromDict(json.load(handle))
        except Exception:
            return SpotifyTokens()

    def _saveTokens(self, tokens: SpotifyTokens):
        try:
            self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.token_cache_path.open("w", encoding="utf-8") as handle:
                json.dump(tokens.asDict(), handle, indent=2)
        except Exception:
            pass

    def _refreshOrAuthorize(self, interactive: bool):
        if self.tokens.refresh_token:
            try:
                self._refreshAccessToken()
                return
            except Exception:
                pass
        if interactive and self.auto_authorize and self.client_id:
            self._authorizeInteractive()

    def _buildConnectionState(self, status: str, lastError: str = ""):
        return {
            "status": status,
            "accessToken": self.tokens.access_token,
            "refreshToken": self.tokens.refresh_token,
            "expiresAt": str(int(self.tokens.expires_at)) if self.tokens.expires_at else "",
            "connectedAt": "",
            "lastError": lastError,
            "userName": self.profile.get("display_name", "") if self.profile else "",
            "deviceName": "",
            "metadata": {"mode": "webapi", "scopes": list(self.scopes)},
        }

    def _buildAuthUrl(self, code_challenge: str, state: str):
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
            "state": state,
        }
        return f"{self.AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"

    def _readConfig(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

    @staticmethod
    def _readScopes(value):
        if isinstance(value, str):
            return [part for part in value.split() if part.strip()]
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @staticmethod
    def _generateVerifier():
        return secrets.token_urlsafe(96)

    @staticmethod
    def _codeChallenge(verifier: str):
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    @staticmethod
    def _normalizeTrackUri(track_id: str):
        if str(track_id).startswith("spotify:"):
            return str(track_id)
        return f"spotify:track:{track_id}"

    @staticmethod
    def _playlistUri(playlist_id: str):
        if str(playlist_id).startswith("spotify:"):
            return str(playlist_id)
        return f"spotify:playlist:{playlist_id}"

    @staticmethod
    def _normalizePlayback(payload: dict[str, Any] | None):
        payload = dict(payload or {})
        item = dict(payload.get("item") or {})
        artists = item.get("artists") or []
        artist_names = ", ".join(str(artist.get("name") or "") for artist in artists if isinstance(artist, dict) and artist.get("name"))
        device = dict(payload.get("device") or {})
        return {
            "track": str(item.get("name") or ""),
            "artist": artist_names,
            "album": str((item.get("album") or {}).get("name") if isinstance(item.get("album"), dict) else item.get("album") or ""),
            "duration": int(item.get("duration_ms") or 0),
            "progress": int(payload.get("progress_ms") or 0),
            "isPlaying": bool(payload.get("is_playing")),
            "volume": int(device.get("volume_percent") or 0),
            "playbackSpeed": 1.0,
            "shuffleEnabled": bool(payload.get("shuffle_state")),
            "repeatMode": str(payload.get("repeat_state") or "off"),
            "activeDevice": str(device.get("name") or ""),
            "playlist": str((payload.get("context") or {}).get("uri") or ""),
            "timestamp": str(payload.get("timestamp") or ""),
            "source": "spotify",
            "metadata": {"spotify": payload},
        }

    @staticmethod
    def _normalizeSearch(query: str, payload: dict[str, Any], kind: str):
        payload = dict(payload or {})
        result = {
            "query": query,
            "tracks": [],
            "playlists": [],
            "artists": [],
            "albums": [],
            "source": "spotify",
            "timestamp": int(time.time() * 1000),
            "metadata": {"kind": kind},
        }
        if kind == "tracks":
            for item in payload.get("tracks", {}).get("items", []) or []:
                result["tracks"].append(SpotifyWebApiClient._normalizeTrack(item))
        elif kind == "playlists":
            for item in payload.get("playlists", {}).get("items", []) or []:
                result["playlists"].append(SpotifyWebApiClient._normalizePlaylist(item))
        elif kind == "artists":
            for item in payload.get("artists", {}).get("items", []) or []:
                result["artists"].append({"artistId": item.get("id"), "name": item.get("name"), "uri": item.get("uri"), "externalUrls": item.get("external_urls", {})})
        elif kind == "albums":
            for item in payload.get("albums", {}).get("items", []) or []:
                result["albums"].append({"albumId": item.get("id"), "name": item.get("name"), "uri": item.get("uri"), "artists": item.get("artists", [])})
        return result

    @staticmethod
    def _normalizeTrack(item: dict[str, Any]):
        artists = item.get("artists") or []
        return {
            "trackId": item.get("id") or "",
            "title": item.get("name") or "",
            "artist": ", ".join(str(artist.get("name") or "") for artist in artists if isinstance(artist, dict) and artist.get("name")),
            "album": (item.get("album") or {}).get("name") if isinstance(item.get("album"), dict) else item.get("album") or "",
            "durationMs": int(item.get("duration_ms") or 0),
            "uri": item.get("uri") or "",
            "albumArtUrl": ((item.get("album") or {}).get("images") or [{}])[0].get("url", "") if isinstance(item.get("album"), dict) else "",
            "explicit": bool(item.get("explicit")),
            "metadata": {"source": "spotify", "externalUrls": item.get("external_urls", {})},
        }

    @staticmethod
    def _normalizePlaylist(item: dict[str, Any]):
        return {
            "playlistId": item.get("id") or "",
            "name": item.get("name") or "",
            "description": item.get("description") or "",
            "tracks": [],
            "uri": item.get("uri") or "",
            "isUserOwned": bool(item.get("owner", {}).get("id")),
            "isFavorite": False,
            "metadata": {"snapshot": item},
        }

    @staticmethod
    def _normalizeDevice(item: dict[str, Any]):
        return {
            "deviceId": item.get("id") or "",
            "name": item.get("name") or "",
            "isActive": bool(item.get("is_active")),
            "isPrivateSession": bool(item.get("is_private_session")),
            "isRestricted": bool(item.get("is_restricted")),
            "volumePercent": int(item.get("volume_percent") or 0),
            "type": item.get("type") or "",
        }

    def _resolveTrack(self, trackId: str = "", query: str = "", playlistId: str = ""):
        if trackId:
            if str(trackId).startswith("spotify:track:"):
                return {"trackId": trackId.split(":")[-1], "uri": trackId, "title": "", "artist": "", "album": "", "durationMs": 0, "albumArtUrl": "", "explicit": False, "metadata": {}}
            search = self.searchTracks(trackId)
            tracks = search.get("tracks") or []
            if tracks:
                return tracks[0]
        if query:
            search = self.searchTracks(query)
            tracks = search.get("tracks") or []
            if tracks:
                return tracks[0]
        if playlistId:
            playlist = self._resolvePlaylist(playlistId=playlistId, query="")
            if playlist:
                return playlist
        return None

    def _resolvePlaylist(self, playlistId: str = "", query: str = ""):
        if playlistId:
            if str(playlistId).startswith("spotify:playlist:"):
                return {"playlistId": playlistId.split(":")[-1], "name": "", "uri": playlistId, "description": "", "tracks": []}
            playlists = self.listPlaylists()
            for playlist in playlists:
                if playlist.get("playlistId") == playlistId or playlist.get("uri") == playlistId:
                    return playlist
        if query:
            playlists = self.searchPlaylists(query).get("playlists") or []
            if playlists:
                return playlists[0]
        return None
