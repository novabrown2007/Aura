"""Windows system tray support for the Aura shell."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys
import threading


user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

WNDPROC = ctypes.WINFUNCTYPE(
    wintypes.LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


WM_APP = 0x8000
WM_TRAY = WM_APP + 1
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIM_SETVERSION = 0x00000004

NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

NOTIFYICON_VERSION_4 = 4


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
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
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


class WindowsTrayIcon:
    """Minimal tray icon with click-to-activate behavior."""

    def __init__(self, tooltip: str, on_activate):
        self.tooltip = str(tooltip or "Aura")
        self.on_activate = on_activate
        self._thread = None
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._hwnd = None
        self._nid = None
        self._icon = None
        self._wndproc = None
        self._class_name = "AuraTrayWindow"
        self._class_atom = None
        self._thread_id = None

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="AuraTray", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def stop(self):
        self._stop_event.set()
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._thread = None
        self._hwnd = None

    def _run(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        hinstance = kernel32.GetModuleHandleW(None)

        wndproc = WNDPROC(self._wnd_proc)
        self._wndproc = wndproc

        wndclass = WNDCLASSW()
        wndclass.style = 0
        wndclass.lpfnWndProc = wndproc
        wndclass.cbClsExtra = 0
        wndclass.cbWndExtra = 0
        wndclass.hInstance = hinstance
        wndclass.hIcon = None
        wndclass.hCursor = None
        wndclass.hbrBackground = None
        wndclass.lpszMenuName = None
        wndclass.lpszClassName = self._class_name

        atom = user32.RegisterClassW(ctypes.byref(wndclass))
        if not atom:
            error = ctypes.get_last_error()
            if error != 1410:
                self._ready.set()
                return
        self._class_atom = atom

        hwnd = user32.CreateWindowExW(
            0,
            self._class_name,
            self._class_name,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            hinstance,
            None,
        )
        if not hwnd:
            self._ready.set()
            return

        self._hwnd = hwnd
        self._icon = shell32.ExtractIconW(None, sys.executable, 0)
        if not self._icon:
            self._ready.set()
            return

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = self._icon
        nid.szTip = self.tooltip[:127]
        nid.uTimeoutOrVersion = NOTIFYICON_VERSION_4
        self._nid = nid

        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        shell32.Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(nid))
        self._ready.set()

        msg = MSG()
        while not self._stop_event.is_set():
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result == 0 or result == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        self._cleanup()

    def _cleanup(self):
        if self._nid is not None:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            self._nid = None
        if self._icon:
            user32.DestroyIcon(self._icon)
            self._icon = None
        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
            self._hwnd = None

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY:
            if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                self.on_activate()
            return 0
        if msg == WM_DESTROY:
            self._stop_event.set()
            self._cleanup()
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
