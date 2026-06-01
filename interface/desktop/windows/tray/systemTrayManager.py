"""Native Windows system tray integration for Aura."""

from __future__ import annotations

import ctypes
import os
import threading
from ctypes import wintypes
from typing import Any

from interface.desktop.windows.tray.trayMenu import TrayMenu, TrayMenuItem


class SystemTrayManager:
    """Manage a Windows tray icon when the platform supports it."""

    WM_USER = 0x0400
    WM_APP = 0x8000
    WM_COMMAND = 0x0111
    WM_DESTROY = 0x0002
    WM_RBUTTONUP = 0x0205
    WM_LBUTTONUP = 0x0202
    WM_CONTEXTMENU = 0x007B
    NIM_ADD = 0x00000000
    NIM_MODIFY = 0x00000001
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    TPM_RIGHTBUTTON = 0x0002
    TPM_RETURNCMD = 0x0100
    IDI_APPLICATION = 32512
    DEFAULT_CALLBACK = WM_APP + 1

    class WNDCLASSW(ctypes.Structure):
        """Minimal Win32 window class definition for the tray message window."""

        _fields_ = [
            ("style", wintypes.UINT),
            ("lpfnWndProc", ctypes.c_void_p),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", ctypes.c_void_p),
            ("hIcon", ctypes.c_void_p),
            ("hCursor", ctypes.c_void_p),
            ("hbrBackground", ctypes.c_void_p),
            ("lpszMenuName", ctypes.c_wchar_p),
            ("lpszClassName", ctypes.c_wchar_p),
        ]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", wintypes.HICON),
            ("szTip", wintypes.WCHAR * 128),
            ("dwState", wintypes.DWORD),
            ("dwStateMask", wintypes.DWORD),
            ("szInfo", wintypes.WCHAR * 256),
            ("uVersion", wintypes.UINT),
            ("szInfoTitle", wintypes.WCHAR * 64),
            ("dwInfoFlags", wintypes.DWORD),
            ("guidItem", ctypes.c_byte * 16),
            ("hBalloonIcon", wintypes.HICON),
        ]

    def __init__(self, context=None, overlayManager=None):
        self.context = context
        self.overlayManager = overlayManager
        self.enabled = bool(self._getConfigValue("systemTrayEnabled", True))
        self.started = False
        self.available = False
        self._thread = None
        self._running = threading.Event()
        self._callbackMessage = self.DEFAULT_CALLBACK
        self._hwnd = None
        self._nid = None
        self._menu = TrayMenu()
        self._menuActions = {}
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.Tray") if logger else None

    def start(self):
        if self.started:
            return self
        self.started = True
        if not self.enabled:
            return self
        if os.name != "nt":
            return self
        try:
            self._thread = threading.Thread(target=self._runMessageLoop, daemon=True)
            self._running.set()
            self._thread.start()
        except Exception as error:
            self.available = False
            if self.logger:
                self.logger.warning(f"Tray initialization failed: {error}")
        return self

    def stop(self):
        self._running.clear()
        if self._hwnd and os.name == "nt":
            try:
                self._deleteIcon()
                ctypes.windll.user32.PostMessageW(self._hwnd, self.WM_DESTROY, 0, 0)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=1.0)
            except Exception:
                pass
        self.started = False
        self.available = False

    def configureMenu(self, menu: TrayMenu, actionMap: dict[str, Any]):
        self._menu = menu
        self._menuActions = dict(actionMap or {})

    def restoreWindow(self):
        if self.overlayManager is not None:
            self.overlayManager.showWindow()

    def requestExit(self):
        if self.overlayManager is not None:
            self.overlayManager.requestExit(reason="tray")

    def snapshot(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "enabled": self.enabled,
            "started": self.started,
            "running": bool(self._running.is_set()),
            "menu": self._menu.asDict(),
        }

    def _runMessageLoop(self):
        if os.name != "nt":
            return
        try:
            self._createWindowAndIcon()
            self.available = True
            msg = wintypes.MSG()
            while self._running.is_set():
                result = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
                if result == 0:
                    break
                ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as error:
            self.available = False
            if self.logger:
                self.logger.warning(f"Tray message loop failed: {error}")
        finally:
            try:
                self._deleteIcon()
            except Exception:
                pass

    def _createWindowAndIcon(self):
        if self._hwnd is not None:
            return

        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

        def windowProc(hwnd, msg, wparam, lparam):
            if msg == self._callbackMessage:
                self._handleTrayCallback(lparam)
                return 0
            if msg == self.WM_COMMAND:
                self._handleCommand(int(wparam))
                return 0
            if msg == self.WM_DESTROY:
                ctypes.windll.user32.PostQuitMessage(0)
                return 0
            return 0

        self._windowProc = WNDPROC(windowProc)
        className = "AuraTrayWindow"
        hInstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        wndClass = self.WNDCLASSW()
        wndClass.lpfnWndProc = ctypes.cast(self._windowProc, ctypes.c_void_p).value
        wndClass.hInstance = hInstance
        wndClass.lpszClassName = className
        ctypes.windll.user32.RegisterClassW(ctypes.byref(wndClass))
        self._hwnd = ctypes.windll.user32.CreateWindowExW(
            0,
            className,
            "AuraTray",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            hInstance,
            None,
        )
        if not self._hwnd:
            raise RuntimeError("Tray window creation failed.")
        self._addIcon()

    def _addIcon(self):
        icon = ctypes.windll.user32.LoadIconW(0, self.IDI_APPLICATION)
        tip = "Aura Assistant"
        nid = self.NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(self.NOTIFYICONDATAW)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
        nid.uCallbackMessage = self._callbackMessage
        nid.hIcon = icon
        nid.szTip = tip
        if not ctypes.windll.shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(nid)):
            raise RuntimeError("Tray icon registration failed.")
        self._nid = nid

    def _deleteIcon(self):
        if self._nid is not None:
            ctypes.windll.shell32.Shell_NotifyIconW(self.NIM_DELETE, ctypes.byref(self._nid))
            self._nid = None

    def _handleTrayCallback(self, lparam):
        if lparam == self.WM_LBUTTONUP:
            self.restoreWindow()
        elif lparam in (self.WM_CONTEXTMENU, self.WM_RBUTTONUP):
            self._showMenu()

    def _showMenu(self):
        if self._hwnd is None:
            return
        try:
            hMenu = ctypes.windll.user32.CreatePopupMenu()
            for item in self._menu.items:
                if item.separator:
                    ctypes.windll.user32.AppendMenuW(hMenu, 0x00000800, 0, None)
                    continue
                flags = 0x00000000
                if not item.enabled:
                    flags |= 0x00000003
                ctypes.windll.user32.AppendMenuW(hMenu, flags, int(item.itemId), item.label)
            ctypes.windll.user32.SetForegroundWindow(self._hwnd)
            point = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
            command = ctypes.windll.user32.TrackPopupMenu(
                hMenu,
                self.TPM_RETURNCMD | self.TPM_RIGHTBUTTON,
                point.x,
                point.y,
                0,
                self._hwnd,
                None,
            )
            if command:
                self._handleCommand(int(command))
            ctypes.windll.user32.DestroyMenu(hMenu)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Tray menu display failed: {error}")

    def _handleCommand(self, commandId: int):
        for item in self._menu.items:
            if int(item.itemId) == int(commandId):
                action = self._menuActions.get(item.actionName)
                if callable(action):
                    try:
                        action()
                    except Exception as error:
                        if self.logger:
                            self.logger.warning(f"Tray action failed ({item.actionName}): {error}")
                break

    def _getConfigValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, None)
        if value is None and "." not in key:
            value = config.get(f"interface.desktop.windows.{key}", None)
        if value is None:
            return default
        return value
