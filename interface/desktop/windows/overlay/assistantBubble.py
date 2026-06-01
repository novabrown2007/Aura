"""Floating assistant bubble for Aura on Windows."""

from __future__ import annotations


class AssistantBubble:
    """A small clickable online indicator for Aura on Windows."""

    def __init__(self, context=None, root=None, onOpen=None, positionManager=None):
        self.context = context
        self.root = root
        self.onOpen = onOpen
        self.positionManager = positionManager
        self.window = None
        self.canvas = None
        self.visible = False
        self.dragStart = None
        self.dragOrigin = None
        self.dragMoved = False
        self._releaseHandled = False
        self.animationPhase = 0
        self.state = "IDLE"
        self.message = ""
        self.provider = ""
        self.connected = True
        self.micState = "IDLE"
        self.logger = getattr(getattr(context, "logger", None), "getChild", lambda *_: None)("Desktop.Bubble") if getattr(context, "logger", None) else None

    def ensureWindow(self):
        if self.window is not None:
            return self.window
        from tkinter import Canvas, Toplevel

        master = self.root
        if master is None or not hasattr(master, "tk"):
            return None

        style = self._bubbleStyle()
        bubble = Toplevel(master)
        bubble.overrideredirect(True)
        bubble.attributes("-topmost", True)
        bubble.attributes("-alpha", float(self._getConfigValue("overlayOpacity", 0.97)))
        bubble.configure(bg=style["shell"])
        self._applyBubbleMask(bubble, style)
        bubble.geometry(f'{style["diameter"]}x{style["diameter"]}+60+60')
        bubble.bind("<ButtonPress-1>", self._onDragStart)
        bubble.bind("<B1-Motion>", self._onDragMove)
        bubble.bind("<ButtonRelease-1>", self._onDragEnd)

        canvas = Canvas(
            bubble,
            width=style["diameter"],
            height=style["diameter"],
            bg=style["shell"],
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        canvas.pack(fill="both", expand=True)
        self.canvas = canvas
        self._drawBubbleChrome()

        self.window = bubble
        self._restorePosition()
        self._render()
        return bubble

    def show(self):
        window = self.ensureWindow()
        if window is None:
            return
        try:
            self._restorePosition()
            window.deiconify()
            window.lift()
            self.visible = True
            self._render()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Bubble show failed: {error}")

    def hide(self):
        if self.window is None:
            return
        try:
            self.window.withdraw()
            self.visible = False
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Bubble hide failed: {error}")

    def destroy(self):
        if self.window is None:
            return
        try:
            self.window.destroy()
        except Exception:
            pass
        self.window = None
        self.canvas = None
        self.visible = False

    def setAnimationPhase(self, phase: int):
        self.animationPhase = int(phase)
        self._render()

    def setState(self, state: str, message: str = "", provider: str = "", connected: bool = True):
        self.state = str(state or "IDLE").upper()
        self.message = str(message or "")
        self.provider = str(provider or "")
        self.connected = bool(connected)
        self._render()

    def setMicState(self, state: str, active: bool = False, muted: bool = False, confidence: float = 0.0, silence: float = 0.0):
        self.micState = str(state or "IDLE").upper()
        self._render()

    def setProcessing(self, active: bool, message: str = "Processing"):
        self.state = "PROCESSING" if active else self.state
        self.message = str(message or "")
        self._render()

    def _render(self):
        if self.window is None:
            return
        try:
            self._drawBubbleChrome()
        except Exception:
            pass

    def _onOpenRequested(self, _event=None):
        if self.dragMoved:
            return
        if callable(self.onOpen):
            try:
                self.onOpen()
            except Exception:
                pass

    def _onDragStart(self, event):
        if self.window is None:
            return
        self.dragStart = (getattr(event, "x_root", 0), getattr(event, "y_root", 0))
        self.dragOrigin = (self.window.winfo_x(), self.window.winfo_y())
        self.dragMoved = False
        self._releaseHandled = False

    def _onDragMove(self, event):
        if self.window is None:
            return
        try:
            if self.dragStart is None or self.dragOrigin is None:
                return
            self.dragMoved = True
            startX, startY = self.dragStart
            originX, originY = self.dragOrigin
            currentX = getattr(event, "x_root", startX)
            currentY = getattr(event, "y_root", startY)
            deltaX = currentX - startX
            deltaY = currentY - startY
            x = originX + deltaX
            y = originY + deltaY
            self.window.geometry(f"+{int(x)}+{int(y)}")
            if self.positionManager is not None and hasattr(self.window, "winfo_screenwidth"):
                try:
                    from interface.desktop.windows.models import OverlayPosition

                    style = self._bubbleStyle()
                    position = OverlayPosition(
                        x=int(x),
                        y=int(y),
                        width=style["diameter"],
                        height=style["diameter"],
                        screenWidth=int(self.window.winfo_screenwidth()),
                        screenHeight=int(self.window.winfo_screenheight()),
                    )
                    self.positionManager.save(position)
                except Exception:
                    pass
        except Exception:
            pass

    def _onDragEnd(self, _event=None):
        if self._releaseHandled:
            return
        self._releaseHandled = True
        if self.dragMoved:
            self._restorePosition(saveCurrent=True)
        elif self.dragStart is not None:
            self._onOpenRequested()
        self.dragStart = None
        self.dragOrigin = None
        self.dragMoved = False

    def _restorePosition(self, saveCurrent: bool = False):
        if self.window is None or self.positionManager is None:
            return
        try:
            if saveCurrent and hasattr(self.window, "geometry"):
                self.positionManager.captureWindowPosition(self.window)
            position = self.positionManager.restoreWindowPosition(self.window)
            if hasattr(self.window, "geometry") and position is not None:
                style = self._bubbleStyle()
                self.window.geometry(f"{style['diameter']}x{style['diameter']}+{int(position.x)}+{int(position.y)}")
        except Exception:
            pass

    def snapshot(self) -> dict:
        return {"visible": self.visible, "animationPhase": self.animationPhase, "state": self.state}

    def _bubbleStyle(self) -> dict:
        diameter = int(self._getConfigValue("overlayBubbleDiameter", 56))
        return {
            "diameter": diameter,
            "shell": "#07111d",
            "bubble": "#2f73b6",
            "bubbleAlt": "#3f8be0",
            "shadow": "#04101b",
            "outline": "#8ec3ff",
            "glow": "#6ab2ff",
        }

    def _drawBubbleChrome(self):
        canvas = getattr(self, "canvas", None)
        if canvas is None:
            return
        try:
            canvas.delete("chrome")
            style = self._bubbleStyle()
            diameter = style["diameter"]
            r = max(8, diameter // 2 - 2)
            self._drawCircle(canvas, 3, 4, diameter - 6, diameter - 5, r, fill=style["shadow"], outline="", tag="chrome")
            self._drawCircle(canvas, 1, 2, diameter - 8, diameter - 9, r, fill=style["bubble"], outline=style["outline"], tag="chrome")
            self._drawCircle(canvas, 8, 8, diameter - 18, diameter - 18, max(6, r - 8), fill=style["bubbleAlt"], outline="", tag="chrome")
            self._drawCircle(canvas, 15, 12, diameter - 28, diameter - 26, max(4, r - 13), fill=style["glow"], outline="", tag="chrome")
        except Exception:
            pass

    def _applyBubbleMask(self, window, style):
        if window is None:
            return
        try:
            window.attributes("-transparentcolor", style["shell"])
        except Exception:
            pass

    @staticmethod
    def _drawCircle(canvas, x1, y1, x2, y2, radius, fill, outline, tag):
        canvas.create_oval(x1, y1, x2, y2, fill=fill, outline=outline, tags=(tag,))

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
