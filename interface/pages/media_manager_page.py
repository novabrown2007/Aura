"""Media Manager page for playback control and Spotify browsing."""

from __future__ import annotations

from .base import Page
from ..drawing import shadow_round_rect


class MediaManagerPage(Page):
    """Single-page media manager for local playback and Spotify browsing."""

    name = "media"

    def __init__(self, context=None):
        self.context = context
        self._spotify = None
        self._needs_refresh = True
        self._search_query = ""
        self._search_active = False
        self._status_text = "Use the search box to browse Spotify."
        self._scroll_offset = 0
        self._max_scroll = 0
        self._volume_dragging = False
        self._now_playing: dict[str, object] = {}
        self._saved_playlists: list[dict[str, object]] = []
        self._track_results: list[dict[str, object]] = []
        self._playlist_results: list[dict[str, object]] = []
        self._search_bounds = (0, 0, 0, 0)
        self._search_button_bounds = (0, 0, 0, 0)
        self._results_bounds = (0, 0, 0, 0)
        self._volume_bounds = (0, 0, 0, 0)
        self._volume_minus_bounds = (0, 0, 0, 0)
        self._volume_plus_bounds = (0, 0, 0, 0)
        self._play_button_bounds = (0, 0, 0, 0)
        self._pause_button_bounds = (0, 0, 0, 0)
        self._prev_button_bounds = (0, 0, 0, 0)
        self._next_button_bounds = (0, 0, 0, 0)
        self._track_hitboxes: list[tuple[tuple[int, int, int, int], dict[str, object]]] = []
        self._playlist_hitboxes: list[tuple[tuple[int, int, int, int], dict[str, object]]] = []

    def set_context(self, context=None):
        self.context = context
        self._spotify = None
        self._needs_refresh = True

    def render(self, canvas, width: int, height: int, theme, sidebar_visible: bool):
        self._spotify = self._resolve_spotify()
        self._refresh_state()

        bounds = self.content_bounds(width, height, sidebar_visible)
        left = bounds["left"] + 18
        right = bounds["right"] - 18
        top = bounds["top"] + 12
        bottom = bounds["bottom"] - 18

        canvas.create_text(left, top, anchor="nw", text="Media Manager", fill=theme.text, font=("Segoe UI", 18, "bold"))
        canvas.create_text(left, top + 28, anchor="nw", text="Playback controls, local state, and Spotify browsing", fill=theme.placeholder, font=("Segoe UI", 10))

        split_x = left + max(320, int((right - left) * 0.36))
        split_x = min(split_x, right - 340)
        left_panel_right = split_x - 14
        right_panel_left = split_x + 14

        self._draw_now_playing_panel(canvas, theme, left, top + 58, left_panel_right, bottom)
        self._draw_browse_panel(canvas, theme, right_panel_left, top + 58, right, bottom)

    def content_bounds(self, width: int, height: int, sidebar_visible: bool) -> dict[str, int]:
        left = 36
        right = width - 36
        top = 102
        bottom = height - 148
        if sidebar_visible:
            left = 24 + 210 + 28
        return {"left": left, "right": right, "top": top, "bottom": bottom}

    def handle_press(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if self._point_in_bounds(x, y, self._search_bounds):
            self._search_active = True
            return True
        if self._point_in_bounds(x, y, self._search_button_bounds):
            self._run_search()
            return True
        if self._point_in_bounds(x, y, self._prev_button_bounds):
            self._call_spotify("previousTrack")
            return True
        if self._point_in_bounds(x, y, self._next_button_bounds):
            self._call_spotify("nextTrack")
            return True
        if self._point_in_bounds(x, y, self._play_button_bounds):
            self._toggle_playback()
            return True
        if self._point_in_bounds(x, y, self._pause_button_bounds):
            self._toggle_playback()
            return True
        if self._point_in_bounds(x, y, self._volume_minus_bounds):
            self._adjust_volume(-5)
            return True
        if self._point_in_bounds(x, y, self._volume_plus_bounds):
            self._adjust_volume(5)
            return True
        if self._point_in_bounds(x, y, self._volume_bounds):
            self._volume_dragging = True
            self._set_volume_from_point(x)
            return True
        for bounds, item in self._track_hitboxes:
            if self._point_in_bounds(x, y, bounds):
                self._play_track(item)
                return True
        for bounds, item in self._playlist_hitboxes:
            if self._point_in_bounds(x, y, bounds):
                self._play_playlist(item)
                return True
        self._search_active = False
        return False

    def handle_drag(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if self._volume_dragging and self._point_in_bounds(x, y, self._volume_bounds):
            self._set_volume_from_point(x)
            return True
        return False

    def handle_release(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if self._volume_dragging:
            self._volume_dragging = False
            return True
        return False

    def handle_scroll(self, delta: int, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if not self._point_in_bounds(x, y, self._results_bounds):
            return False
        step = 42
        if delta > 0:
            self._scroll_offset = max(0, self._scroll_offset - step)
        else:
            self._scroll_offset = min(self._max_scroll, self._scroll_offset + step)
        return True

    def handle_keypress(self, event) -> bool:
        if not self._search_active:
            return False
        keysym = getattr(event, "keysym", "") or ""
        char = getattr(event, "char", "") or ""
        if keysym in {"Return", "KP_Enter"}:
            self._run_search()
            return True
        if keysym == "Escape":
            self._search_active = False
            return True
        if keysym == "BackSpace":
            self._search_query = self._search_query[:-1]
            self._needs_refresh = True
            return True
        if len(char) == 1 and char.isprintable():
            self._search_query += char
            self._needs_refresh = True
            return True
        return False

    def submit_prompt(self, prompt: str) -> bool:
        self._search_query = str(prompt or "").strip()
        if not self._search_query:
            return False
        self._search_active = False
        self._run_search()
        return True

    def _refresh_state(self):
        spotify = self._spotify
        if spotify is None:
            self._now_playing = self._fallback_playback()
            self._saved_playlists = []
            self._track_results = []
            self._playlist_results = []
            self._status_text = "Spotify is not available in this runtime."
            return

        try:
            state = spotify.getPlaybackState()
        except Exception:
            state = spotify.getNowPlaying() if hasattr(spotify, "getNowPlaying") else {}
        self._now_playing = dict(state or {})

        try:
            playlists = spotify.listPlaylists()
        except Exception:
            playlists = []
        self._saved_playlists = [dict(item or {}) for item in playlists or []]

        if self._needs_refresh and self._search_query.strip():
            self._run_search()
        elif self._needs_refresh:
            self._track_results = []
            self._playlist_results = []
            self._status_text = "Type in the search box and press Enter to browse Spotify."
            self._needs_refresh = False

    def _run_search(self):
        spotify = self._spotify
        query = self._search_query.strip()
        self._scroll_offset = 0
        if spotify is None:
            self._status_text = "Spotify is not available."
            self._track_results = []
            self._playlist_results = []
            self._needs_refresh = False
            return
        if not query:
            self._track_results = []
            self._playlist_results = []
            self._status_text = "Type a search query and press Enter."
            self._needs_refresh = False
            return
        try:
            tracks_payload = spotify.searchTracks(query)
            playlists_payload = spotify.searchPlaylists(query)
            self._track_results = [dict(item or {}) for item in tracks_payload.get("tracks", []) or []]
            self._playlist_results = [dict(item or {}) for item in playlists_payload.get("playlists", []) or []]
            total = len(self._track_results) + len(self._playlist_results)
            self._status_text = f"Showing {total} result{'s' if total != 1 else ''} for '{query}'."
        except Exception as error:
            self._track_results = []
            self._playlist_results = []
            self._status_text = f"Spotify search failed: {error}"
        self._needs_refresh = False

    def _draw_now_playing_panel(self, canvas, theme, left: int, top: int, right: int, bottom: int):
        shadow_round_rect(canvas, left, top, right, bottom, 18, fill=theme.tertiary_background, outline=theme.border, width=2)
        canvas.create_text(left + 20, top + 18, anchor="nw", text="Now Playing", fill=theme.text, font=("Segoe UI", 12, "bold"))

        track = str(self._now_playing.get("track") or "Nothing playing").strip() or "Nothing playing"
        artist = str(self._now_playing.get("artist") or "").strip()
        album = str(self._now_playing.get("album") or "").strip()
        device = str(self._now_playing.get("activeDevice") or "").strip()
        source = str(self._now_playing.get("source") or "").strip()

        canvas.create_text(left + 20, top + 46, anchor="nw", text=track, fill=theme.text, font=("Segoe UI", 14, "bold"), width=max(140, right - left - 40))
        if artist:
            canvas.create_text(left + 20, top + 74, anchor="nw", text=artist, fill=theme.placeholder, font=("Segoe UI", 11))
        if album:
            canvas.create_text(left + 20, top + 95, anchor="nw", text=album, fill=theme.placeholder, font=("Segoe UI", 10))
        if device or source:
            details = " • ".join(part for part in (device, source) if part)
            canvas.create_text(left + 20, top + 118, anchor="nw", text=details, fill=theme.placeholder, font=("Segoe UI", 9))

        progress = int(self._now_playing.get("progress") or 0)
        duration = max(1, int(self._now_playing.get("duration") or 0))
        bar_left = left + 20
        bar_right = right - 20
        bar_top = bottom - 150
        bar_bottom = bar_top + 8
        canvas.create_rectangle(bar_left, bar_top, bar_right, bar_bottom, fill=theme.shadow, outline=theme.shadow, width=0)
        filled = bar_left + int((max(0, min(progress, duration)) / duration) * max(1, bar_right - bar_left))
        canvas.create_rectangle(bar_left, bar_top, filled, bar_bottom, fill=theme.secondary_accent, outline=theme.secondary_accent, width=0)
        canvas.create_text(bar_left, bar_top - 18, anchor="w", text=self._format_time(progress), fill=theme.placeholder, font=("Segoe UI", 9))
        canvas.create_text(bar_right, bar_top - 18, anchor="e", text=self._format_time(duration), fill=theme.placeholder, font=("Segoe UI", 9))

        self._draw_transport_controls(canvas, theme, left + 20, bottom - 128, right - 20)
        self._draw_volume_control(canvas, theme, left + 20, bottom - 72, right - 20)

    def _draw_transport_controls(self, canvas, theme, left: int, top: int, right: int):
        button_w = 72
        button_h = 30
        gap = 12
        total = button_w * 3 + gap * 2
        start_x = left + max(0, (right - left - total) // 2)
        self._prev_button_bounds = (start_x, top, start_x + button_w, top + button_h)
        self._play_button_bounds = (start_x + button_w + gap, top, start_x + button_w + gap + button_w, top + button_h)
        self._pause_button_bounds = self._play_button_bounds
        self._next_button_bounds = (start_x + (button_w + gap) * 2, top, start_x + (button_w + gap) * 2 + button_w, top + button_h)
        self._draw_button(canvas, theme, *self._prev_button_bounds, "Prev")
        self._draw_button(canvas, theme, *self._play_button_bounds, "Play/Pause", accent=True)
        self._draw_button(canvas, theme, *self._next_button_bounds, "Next")

    def _draw_volume_control(self, canvas, theme, left: int, top: int, right: int):
        canvas.create_text(left, top, anchor="nw", text="Volume", fill=theme.text, font=("Segoe UI", 11, "bold"))
        value = int(self._now_playing.get("volume") or 0)
        self._volume_minus_bounds = (left, top + 30, left + 28, top + 58)
        self._volume_plus_bounds = (right - 28, top + 30, right, top + 58)
        self._draw_button(canvas, theme, *self._volume_minus_bounds, "−")
        self._draw_button(canvas, theme, *self._volume_plus_bounds, "+")

        slider_left = left + 40
        slider_right = right - 40
        slider_top = top + 40
        slider_bottom = top + 48
        self._volume_bounds = (slider_left, slider_top - 10, slider_right, slider_bottom + 10)
        canvas.create_rectangle(slider_left, slider_top, slider_right, slider_bottom, fill=theme.shadow, outline=theme.shadow, width=0)
        fill_right = slider_left + int((max(0, min(value, 100)) / 100) * max(1, slider_right - slider_left))
        canvas.create_rectangle(slider_left, slider_top, fill_right, slider_bottom, fill=theme.secondary_accent, outline=theme.secondary_accent, width=0)
        knob_x = fill_right
        canvas.create_oval(knob_x - 8, slider_top - 6, knob_x + 8, slider_bottom + 6, fill=theme.panel, outline=theme.soft_glow, width=2)
        canvas.create_text(slider_left, top + 60, anchor="nw", text=str(value), fill=theme.placeholder, font=("Segoe UI", 9))

    def _draw_browse_panel(self, canvas, theme, left: int, top: int, right: int, bottom: int):
        shadow_round_rect(canvas, left, top, right, bottom, 18, fill=theme.tertiary_background, outline=theme.border, width=2)
        canvas.create_text(left + 20, top + 18, anchor="nw", text="Spotify Browser", fill=theme.text, font=("Segoe UI", 12, "bold"))
        canvas.create_text(left + 20, top + 40, anchor="nw", text=self._status_text, fill=theme.placeholder, font=("Segoe UI", 9), width=max(180, right - left - 40))

        search_top = top + 68
        search_height = 34
        search_left = left + 20
        search_right = right - 96
        self._search_bounds = (search_left, search_top, search_right, search_top + search_height)
        self._search_button_bounds = (search_right + 10, search_top, right - 20, search_top + search_height)
        search_fill = theme.background if self._search_active else theme.panel
        search_outline = theme.secondary_accent if self._search_active else theme.border
        shadow_round_rect(canvas, search_left, search_top, search_right, search_top + search_height, 10, fill=search_fill, outline=search_outline, width=1)
        placeholder = self._search_query or "Search Spotify tracks or playlists"
        placeholder_fill = theme.text if self._search_query else theme.placeholder
        canvas.create_text(search_left + 14, search_top + search_height / 2, anchor="w", text=placeholder, fill=placeholder_fill, font=("Segoe UI", 11))
        self._draw_button(canvas, theme, *self._search_button_bounds, "Search", accent=True)

        results_top = search_top + 50
        results_bottom = bottom - 18
        self._results_bounds = (left + 16, results_top, right - 16, results_bottom)
        self._track_hitboxes = []
        self._playlist_hitboxes = []
        self._draw_result_list(canvas, theme, left + 20, results_top, right - 20, results_bottom)

    def _draw_result_list(self, canvas, theme, left: int, top: int, right: int, bottom: int):
        items: list[tuple[str, dict[str, object]]] = []
        if self._track_results:
            items.append(("Tracks", {"kind": "section"}))
            for track in self._track_results:
                items.append(("track", track))
        if self._playlist_results or self._saved_playlists:
            items.append(("Playlists", {"kind": "section"}))
            playlists = self._playlist_results or self._saved_playlists
            for playlist in playlists:
                items.append(("playlist", playlist))
        if not items:
            canvas.create_text(left, top + 12, anchor="nw", text="Search results will appear here.", fill=theme.placeholder, font=("Segoe UI", 10))
            self._max_scroll = 0
            self._scroll_offset = 0
            return

        cursor_y = top - self._scroll_offset
        row_gap = 10
        visible_bottom = bottom
        content_height = 0
        for kind, item in items:
            if kind == "Tracks" or kind == "Playlists":
                header_height = 26
                if cursor_y + header_height >= top and cursor_y <= visible_bottom:
                    canvas.create_text(left, cursor_y, anchor="nw", text=kind, fill=theme.text, font=("Segoe UI", 11, "bold"))
                cursor_y += header_height + 8
                content_height = cursor_y - top
                continue
            row_height = 58
            row_bounds = (left, cursor_y, right, cursor_y + row_height)
            if cursor_y + row_height >= top and cursor_y <= visible_bottom:
                fill = theme.panel
                outline = theme.border
                shadow_round_rect(canvas, left, cursor_y, right, cursor_y + row_height, 12, fill=fill, outline=outline, width=1)
                title = str(item.get("title") or item.get("name") or "Unknown")
                subtitle = str(item.get("artist") or item.get("description") or item.get("album") or "")
                canvas.create_text(left + 16, cursor_y + 10, anchor="nw", text=title, fill=theme.text, font=("Segoe UI", 10, "bold"), width=max(120, right - left - 60))
                if subtitle:
                    canvas.create_text(left + 16, cursor_y + 30, anchor="nw", text=subtitle, fill=theme.placeholder, font=("Segoe UI", 9), width=max(120, right - left - 60))
            if item.get("trackId"):
                self._track_hitboxes.append((row_bounds, item))
            else:
                self._playlist_hitboxes.append((row_bounds, item))
            cursor_y += row_height + row_gap
            content_height = cursor_y - top

        viewport_height = max(1, bottom - top)
        self._max_scroll = max(0, content_height - viewport_height)
        self._scroll_offset = max(0, min(self._scroll_offset, self._max_scroll))
        self._draw_scrollbar(canvas, theme, right - 2, top, bottom, self._scroll_offset, self._max_scroll)

    def _draw_scrollbar(self, canvas, theme, track_x: int, top: int, bottom: int, scroll_offset: int, max_scroll: int):
        track_left = track_x - 8
        track_right = track_x - 4
        canvas.create_rectangle(track_left, top, track_right, bottom, fill=theme.shadow, outline=theme.shadow, width=0)
        if max_scroll <= 0:
            return
        track_height = max(1, bottom - top)
        thumb_height = max(42, int((track_height * track_height) / max(1, track_height + max_scroll)))
        thumb_height = min(track_height, thumb_height)
        thumb_range = max(1, track_height - thumb_height)
        thumb_top = top + int((scroll_offset / max_scroll) * thumb_range)
        canvas.create_rectangle(track_left, thumb_top, track_right, thumb_top + thumb_height, fill=theme.soft_glow, outline=theme.soft_glow, width=0)

    def _draw_button(self, canvas, theme, x1: int, y1: int, x2: int, y2: int, label: str, accent: bool = False):
        outline = theme.secondary_accent if accent else theme.border
        fill = theme.panel
        shadow_round_rect(canvas, x1, y1, x2, y2, 8, fill=fill, outline=outline, width=1)
        canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, anchor="center", text=label, fill=theme.text, font=("Segoe UI", 9, "bold" if accent else "normal"))

    def _toggle_playback(self):
        now_playing = dict(self._now_playing or {})
        if now_playing.get("isPlaying"):
            self._call_spotify("pauseMusic")
        else:
            self._call_spotify("resumeMusic")

    def _adjust_volume(self, delta: int):
        current = int(self._now_playing.get("volume") or 0)
        self._call_spotify("setVolume", max(0, min(100, current + int(delta))))

    def _set_volume_from_point(self, x: int):
        left, _, right, _ = self._volume_bounds
        if right <= left:
            return
        pct = (x - left) / max(1, right - left)
        self._call_spotify("setVolume", int(max(0, min(100, round(pct * 100)))))

    def _play_track(self, track: dict[str, object]):
        self._call_spotify("playTrack", track=str(track.get("trackId") or track.get("title") or ""), artist=str(track.get("artist") or ""), query=str(track.get("title") or ""))

    def _play_playlist(self, playlist: dict[str, object]):
        self._call_spotify("playPlaylist", playlistId=str(playlist.get("playlistId") or ""), query=str(playlist.get("name") or playlist.get("title") or ""))

    def _call_spotify(self, method: str, *args, **kwargs):
        spotify = self._spotify
        if spotify is None:
            return None
        fn = getattr(spotify, method, None)
        if fn is None:
            return None
        try:
            result = fn(*args, **kwargs)
        except TypeError:
            result = fn(*args)
        except Exception as error:
            self._status_text = f"Spotify action failed: {error}"
            self._needs_refresh = False
            return None
        self._needs_refresh = True
        self._refresh_state()
        return result

    def _resolve_spotify(self):
        context = self.context
        if context is None:
            return None
        spotify = getattr(context, "spotify", None)
        if spotify is not None:
            return spotify
        module_manager = getattr(context, "moduleManager", None)
        if module_manager is not None and hasattr(module_manager, "getModule"):
            try:
                return module_manager.getModule("spotify")
            except Exception:
                return None
        return None

    @staticmethod
    def _format_time(value: int) -> str:
        total_seconds = max(0, int(value or 0) // 1000)
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}:{seconds:02d}"

    @staticmethod
    def _point_in_bounds(x: int, y: int, bounds: tuple[int, int, int, int]) -> bool:
        x1, y1, x2, y2 = bounds
        return x1 <= x <= x2 and y1 <= y <= y2

    @staticmethod
    def _fallback_playback():
        return {
            "track": "",
            "artist": "",
            "album": "",
            "duration": 0,
            "progress": 0,
            "isPlaying": False,
            "volume": 100,
            "activeDevice": "",
            "source": "",
        }
