import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QStackedWidget,
    QScrollArea, QProgressBar, QButtonGroup, QSizePolicy, QComboBox, QCheckBox, QSlider,
    QGraphicsOpacityEffect, QApplication
)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, pyqtProperty, QRectF, QEasingCurve, QPointF
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QPainterPath, QIcon, QFont, QFontMetrics, QLinearGradient
from ui.components.range_slider import RangeSlider
from ui.main_window_shared import NotificationBanner
from ui.token_icon_data import TOKEN_ICON_PNG_B64

def get_asset_path(filename):
    """
    Locates a bundled asset (e.g. CRPR.png, token.ico). Checks, in order: the PyInstaller bundle,
    the folder of the frozen executable, then the source tree (desktop/ next to main.py) and the
    working directory. Previously a frozen build returned the bundle path even when the file was
    not bundled (token.ico was missing from older builds), so the icon silently never rendered.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    search_paths = []
    if hasattr(sys, '_MEIPASS'):
        search_paths.append(os.path.join(sys._MEIPASS, filename))
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        search_paths += [os.path.join(exe_dir, filename), os.path.join(exe_dir, "_internal", filename)]
    search_paths += [
        os.path.join(root_dir, filename),
        os.path.join(script_dir, filename),
        os.path.join(os.getcwd(), filename),
    ]
    for p in search_paths:
        if os.path.exists(p):
            return p
    return search_paths[0] if search_paths else filename

def fade_switch(stack: QStackedWidget, index: int):
    if stack.currentIndex() == index:
        return

    effect = QGraphicsOpacityEffect(stack)
    stack.setGraphicsEffect(effect)
    stack.setCurrentIndex(index)

    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(200)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    stack._fade_anim = anim

    def cleanup():
        stack.setGraphicsEffect(None)

    anim.finished.connect(cleanup)
    anim.start()

def create_vector_icon(icon_name: str, color_hex: str) -> QPixmap:
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color_hex))
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    if icon_name == "scissors":
        painter.drawEllipse(3, 14, 5, 5)
        painter.drawEllipse(16, 14, 5, 5)
        painter.drawLine(8, 15, 18, 5)
        painter.drawLine(16, 15, 6, 5)

    elif icon_name == "sparkle":
        painter.drawLine(12, 2, 12, 8)
        painter.drawLine(12, 16, 12, 22)
        painter.drawLine(2, 12, 8, 12)
        painter.drawLine(16, 12, 22, 12)
        painter.drawLine(6, 6, 8, 8)
        painter.drawLine(18, 6, 16, 8)
        painter.drawLine(6, 18, 8, 16)
        painter.drawLine(18, 18, 16, 16)

    elif icon_name == "download":
        painter.drawLine(12, 3, 12, 16)
        painter.drawLine(6, 10, 12, 16)
        painter.drawLine(18, 10, 12, 16)
        painter.drawLine(4, 20, 20, 20)

    elif icon_name == "gear":
        painter.drawEllipse(7, 7, 10, 10)
        for i in range(8):
            painter.save()
            painter.translate(12, 12)
            painter.rotate(i * 45)
            painter.drawLine(0, -5, 0, -7)
            painter.restore()

    elif icon_name == "gauge":                       # Settings > Performance: a speedometer
        painter.drawArc(3, 5, 18, 18, 0 * 16, 180 * 16)
        painter.drawLine(3, 14, 21, 14)
        painter.drawLine(12, 14, 17, 8)
        painter.drawPoint(7, 10)

    elif icon_name == "user":
        painter.drawEllipse(8, 4, 8, 8)
        path = QPainterPath()
        path.moveTo(4, 21)
        path.quadTo(12, 13, 20, 21)
        painter.drawPath(path)

    elif icon_name == "info":
        painter.drawEllipse(3, 3, 18, 18)
        painter.drawLine(12, 10, 12, 16)
        painter.drawLine(12, 7, 12, 8)

    elif icon_name == "home":
        painter.drawLine(12, 4, 4, 11)
        painter.drawLine(12, 4, 20, 11)
        painter.drawLine(6, 11, 6, 20)
        painter.drawLine(18, 11, 18, 20)
        painter.drawLine(6, 20, 18, 20)
        painter.drawRect(10, 14, 4, 6)

    elif icon_name == "copy":
        painter.drawRect(8, 8, 10, 10)
        painter.drawLine(6, 16, 4, 16)
        painter.drawLine(4, 16, 4, 4)
        painter.drawLine(4, 4, 16, 4)
        painter.drawLine(16, 4, 16, 6)

    elif icon_name == "eye":
        path = QPainterPath()
        path.moveTo(2, 12)
        path.quadTo(12, 2, 22, 12)
        path.quadTo(12, 22, 2, 12)
        painter.drawPath(path)
        painter.drawEllipse(9, 9, 6, 6)

    elif icon_name == "eye-off":
        path = QPainterPath()
        path.moveTo(2, 12)
        path.quadTo(12, 2, 22, 12)
        path.quadTo(12, 22, 2, 12)
        painter.drawPath(path)
        painter.drawEllipse(9, 9, 6, 6)
        painter.drawLine(4, 4, 20, 20)

    elif icon_name == "check":
        painter.drawLine(5, 12, 10, 17)
        painter.drawLine(10, 17, 19, 6)

    elif icon_name == "bookmark":
        painter.drawLine(6, 4, 18, 4)
        painter.drawLine(6, 4, 6, 20)
        painter.drawLine(18, 4, 18, 20)
        painter.drawLine(6, 20, 12, 16)
        painter.drawLine(18, 20, 12, 16)

    elif icon_name == "check-circle":
        painter.drawEllipse(3, 3, 18, 18)
        painter.drawLine(8, 12, 11, 15)
        painter.drawLine(11, 15, 16, 9)

    elif icon_name == "link":
        painter.drawRoundedRect(QRectF(3, 9, 9, 6), 3, 3)
        painter.drawRoundedRect(QRectF(12, 9, 9, 6), 3, 3)
        painter.drawLine(9, 12, 15, 12)

    elif icon_name == "folder":
        path = QPainterPath()
        path.moveTo(3, 7)
        path.lineTo(9, 7)
        path.lineTo(11, 9)
        path.lineTo(21, 9)
        path.lineTo(21, 19)
        path.lineTo(3, 19)
        path.closeSubpath()
        painter.drawPath(path)

    elif icon_name == "film":
        painter.drawRoundedRect(QRectF(4, 3, 16, 18), 2, 2)
        painter.drawLine(8, 3, 8, 21)
        painter.drawLine(16, 3, 16, 21)
        painter.drawLine(4, 12, 20, 12)

    elif icon_name == "x":
        painter.drawLine(6, 6, 18, 18)
        painter.drawLine(18, 6, 6, 18)

    elif icon_name == "plus":
        painter.drawLine(12, 5, 12, 19)
        painter.drawLine(5, 12, 19, 12)

    elif icon_name == "lock":
        painter.drawRoundedRect(QRectF(5, 11, 14, 10), 2, 2)
        path = QPainterPath()
        path.moveTo(8, 11)
        path.lineTo(8, 8)
        path.arcTo(QRectF(8, 4, 8, 8), 180, -180)
        path.lineTo(16, 11)
        painter.drawPath(path)
        painter.drawLine(12, 15, 12, 17)

    elif icon_name == "play":
        painter.setBrush(QColor(color_hex))
        path = QPainterPath()
        path.moveTo(8, 5)
        path.lineTo(19, 12)
        path.lineTo(8, 19)
        path.closeSubpath()
        painter.drawPath(path)
    elif icon_name == "pause":
        painter.setBrush(QColor(color_hex))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(6, 5, 4, 14, 1.5, 1.5)
        painter.drawRoundedRect(14, 5, 4, 14, 1.5, 1.5)
    elif icon_name in ("volume", "mute"):
        painter.setBrush(QColor(color_hex))
        path = QPainterPath()
        path.moveTo(3, 9)
        path.lineTo(7, 9)
        path.lineTo(12, 5)
        path.lineTo(12, 19)
        path.lineTo(7, 15)
        path.lineTo(3, 15)
        path.closeSubpath()
        painter.drawPath(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if icon_name == "volume":
            painter.drawArc(11, 8, 6, 8, -60 * 16, 120 * 16)
            painter.drawArc(11, 5, 10, 14, -60 * 16, 120 * 16)
        else:
            painter.drawLine(15, 9, 21, 15)
            painter.drawLine(21, 9, 15, 15)
    elif icon_name == "loop":
        painter.drawArc(4, 5, 16, 14, 30 * 16, 300 * 16)
        painter.drawLine(18, 4, 19, 8)
        painter.drawLine(19, 8, 15, 9)

    elif icon_name == "chevron-down":
        painter.drawLine(6, 9, 12, 15)
        painter.drawLine(12, 15, 18, 9)

    elif icon_name == "chevron-up":
        painter.drawLine(6, 15, 12, 9)
        painter.drawLine(12, 9, 18, 15)

    painter.end()
    return pixmap


_TOKEN_PIXMAP_CACHE = {}


def _decode_ico(path: str, size: int) -> QPixmap:
    """Decodes token.ico directly (PNG or 32-bit BMP entries), for builds without Qt's ICO plugin."""
    import struct
    from PyQt6.QtGui import QImage
    try:
        with open(path, "rb") as f:
            data = f.read()
        _, kind, count = struct.unpack("<HHH", data[:6])
        if kind != 1 or count == 0:
            return QPixmap()
        entries = []
        for i in range(count):
            w, h, _, _, _, bpp, nbytes, off = struct.unpack("<BBBBHHII", data[6 + 16 * i: 22 + 16 * i])
            entries.append(((w or 256), (h or 256), bpp, nbytes, off))
        # smallest entry that is at least 2x the target (crisp on HiDPI), else the largest
        entries.sort(key=lambda e: e[0])
        pick = next((e for e in entries if e[0] >= size * 2), entries[-1])
        w, h, bpp, nbytes, off = pick
        blob = data[off: off + nbytes]
        if blob[:4] == bytes([0x89, 0x50, 0x4E, 0x47]):
            img = QImage.fromData(blob, "PNG")
        else:
            hdr = struct.unpack("<IiiHHIIiiII", blob[:40])
            bw, bh2, bbpp = hdr[1], hdr[2], hdr[4]
            if bbpp != 32:
                return QPixmap()
            bh = abs(bh2) // 2
            pixels = blob[hdr[0]: hdr[0] + bw * bh * 4]
            img = QImage(pixels, bw, bh, bw * 4, QImage.Format.Format_ARGB32).mirrored(False, True).copy()
        if img.isNull():
            return QPixmap()
        return QPixmap.fromImage(img)
    except Exception:
        return QPixmap()


def get_token_pixmap(size: int = 16) -> QPixmap:
    """The real CReaper token asset (token.ico next to main.py), scaled for inline use."""
    if size in _TOKEN_PIXMAP_CACHE:
        return _TOKEN_PIXMAP_CACHE[size]
    path = get_asset_path("token.ico")
    pix = QPixmap()
    if os.path.exists(path):
        icon = QIcon(path)
        if not icon.isNull():
            pix = icon.pixmap(QSize(size * 2, size * 2))
        if pix.isNull():
            pix = _decode_ico(path, size)
    if pix.isNull():
        # Packaged builds may not ship token.ico as a data file: use the embedded copy of the same image
        import base64
        pix.loadFromData(base64.b64decode(TOKEN_ICON_PNG_B64), "PNG")
    if not pix.isNull():
        pix = pix.scaled(size * 2, size * 2, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        pix.setDevicePixelRatio(2.0)
        _TOKEN_PIXMAP_CACHE[size] = pix
    return pix


class OptionCard(QCheckBox):
    """
    Checkbox card where the WHOLE card toggles it. A plain QCheckBox only reacts on its small
    indicator and its text, so clicks on the rest of the styled card did nothing. One click = one toggle
    (Qt's own click handling, no extra signal wiring); Space/Enter still work from the keyboard.
    """
    def hitButton(self, pos):
        return self.rect().contains(pos)


class TrackSlider(QSlider):
    """
    Slider that jumps to the clicked spot: a click anywhere on the track moves the handle there and
    the same press keeps dragging. A plain QSlider only steps by a page per click. Keyboard input
    (arrows, Page Up/Down, Home/End) is QSlider's own and unchanged. setValue() emits valueChanged
    once, and the inherited press handler then sees the handle under the cursor, so a click never
    produces a second update.
    """
    def mousePressEvent(self, event):
        from PyQt6.QtWidgets import QStyle, QStyleOptionSlider
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            style = self.style()
            handle = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt,
                                          QStyle.SubControl.SC_SliderHandle, self)
            pos = event.position().toPoint()
            if not handle.contains(pos):
                groove = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt,
                                              QStyle.SubControl.SC_SliderGroove, self)
                if self.orientation() == Qt.Orientation.Horizontal:
                    span = groove.width() - handle.width()
                    offset = pos.x() - groove.x() - handle.width() // 2
                else:
                    span = groove.height() - handle.height()
                    offset = pos.y() - groove.y() - handle.height() // 2
                value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), max(0, offset),
                                                       max(1, span), opt.upsideDown)
                self.setFocus(Qt.FocusReason.MouseFocusReason)
                self.setValue(value)                    # handle now under the cursor -> press starts a drag
        super().mousePressEvent(event)


def _ui_cache_dir() -> str:
    """Small generated UI images (e.g. checkbox tick) in the user's CReaper data folder."""
    from utils.app_paths import user_data_dir
    return user_data_dir("ui")


def make_token_badge(text: str, size: int = 16, object_name: str = "tokenChip"):
    """
    Token amount chip: [token.ico] <text>. Returns (frame, text_label) so callers can update
    the amount with text_label.setText(...).
    """
    chip = QFrame()
    chip.setObjectName(object_name)
    chip.setFixedHeight(size + 12)          # >= 26 px, so the 12 px corner radius always renders
    lay = QHBoxLayout(chip)
    lay.setContentsMargins(10, 0, 12, 0)
    lay.setSpacing(6)
    icon = QLabel()
    icon.setObjectName("tokenIcon")
    icon.setFixedSize(size, size)
    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon.setPixmap(get_token_pixmap(size))
    text_lbl = QLabel(text)
    text_lbl.setObjectName("tokenChipText")
    text_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
    lay.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)
    lay.addWidget(text_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
    return chip, text_lbl

def create_multi_state_icon(icon_name: str, base_color="#A1A1AA", hover_color="#FAFAFA", active_color="#A855F7") -> QIcon:
    icon = QIcon()
    icon.addPixmap(create_vector_icon(icon_name, base_color), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(create_vector_icon(icon_name, hover_color), QIcon.Mode.Active, QIcon.State.Off)
    icon.addPixmap(create_vector_icon(icon_name, active_color), QIcon.Mode.Normal, QIcon.State.On)
    icon.addPixmap(create_vector_icon(icon_name, active_color), QIcon.Mode.Active, QIcon.State.On)
    return icon

def make_clickable(widget, on_click, accessible_name: str = ""):
    """Mouse click + Enter/Space on a plain widget (e.g. the header token chip), with a hand cursor."""
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    if accessible_name:
        widget.setAccessibleName(accessible_name)

    def press(event):
        if event.button() == Qt.MouseButton.LeftButton:
            on_click()

    def key(event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            on_click()
    widget.mousePressEvent = press
    widget.keyPressEvent = key


class AnimatedAICard(QPushButton):
    """
    The Home cards of the two AI features, each with its own small living detail (drawn over the stylesheet card;
    a few lines per frame, only while the card is on screen and available):
      * "viewfinder" (Auto Clipper): camera crop marks in the corners that breathe in and out like a reframe,
        and a soft light sweep across the card.
      * "peaks" (AI Best Moments): a small waveform in the corner with a playhead scanning it; the bars it passes
        light up, and three peaks turn into found moments.
    Colours come from the central theme table (ui/styles.py); a theme switch recolours without restarting.
    """
    EFFECTS = ("viewfinder", "peaks")

    def __init__(self, parent=None, theme="purple", effect="peaks"):
        super().__init__(parent)
        self._pulse_pos = 0.0
        self.effect = effect if effect in self.EFFECTS else "peaks"
        self.set_theme(theme)

        self.anim = QPropertyAnimation(self, b"pulse_pos")
        self.anim.setDuration(5200 if self.effect == "peaks" else 3200)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setLoopCount(-1)

    def set_locked(self, locked: bool):
        """No tokens: the card looks unavailable (no effect, dimmed); clicks still explain why."""
        locked = bool(locked)
        if getattr(self, "_locked", False) == locked:
            return
        self._locked = locked
        self.setProperty("aiLocked", locked)
        self.style().unpolish(self)
        self.style().polish(self)
        if locked:
            self.anim.stop()
        elif self.isVisible():
            self.anim.start()
        self.update()

    def set_theme(self, theme_name: str):
        """Effect colours from the central theme table (ui/styles.py). Only colours change: the running animation
        keeps going, nothing is re-created, so repeated switches add nothing."""
        from ui.styles import THEMES, theme_colors
        name = str(theme_name).lower()
        base = QColor(theme_name) if name not in THEMES else QColor()
        if base.isValid():                                  # a custom colour (e.g. "#FF8800")
            self._core_color, self._head_color = base, base.lighter(150)
        else:
            t = theme_colors(name)
            self._core_color, self._head_color = QColor(t["effect_core"]), QColor(t["effect_head"])
        self.theme_name = name
        self.update()

    @pyqtProperty(float)
    def pulse_pos(self):
        return self._pulse_pos

    @pulse_pos.setter
    def pulse_pos(self, pos):
        self._pulse_pos = pos
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_locked", False):
            self.anim.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.anim.stop()

    def _color(self, color: QColor, alpha: float) -> QColor:
        c = QColor(color)
        c.setAlphaF(max(0.0, min(1.0, alpha)))
        return c

    def paintEvent(self, event):
        super().paintEvent(event)
        if getattr(self, "_locked", False):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.effect == "viewfinder":
            self._paint_viewfinder(p)
        else:
            self._paint_peaks(p)
        p.end()

    def _paint_viewfinder(self, p: QPainter):
        import math
        t = self._pulse_pos
        w, h = self.width(), self.height()
        # a soft diagonal light sweep, clipped to the card
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 14.0, 14.0)
        p.save()
        p.setClipPath(clip)
        x = -0.5 * w + 2.0 * w * t
        grad = QLinearGradient(x - 90, 0, x + 90, h)
        grad.setColorAt(0.0, self._color(self._core_color, 0.0))
        grad.setColorAt(0.5, self._color(self._core_color, 0.09 if self.underMouse() else 0.06))
        grad.setColorAt(1.0, self._color(self._core_color, 0.0))
        p.fillRect(self.rect(), grad)
        p.restore()
        # crop marks: they breathe in and out like the frame finding its subject
        s = 0.5 - 0.5 * math.cos(2 * math.pi * t)
        inset = 9.0 + 5.0 * s
        arm = 14.0 + 4.0 * s
        r = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        pen = QPen(self._color(self._head_color if self.underMouse() else self._core_color, 0.85), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for cx, cy, dx, dy in ((r.left(), r.top(), 1, 1), (r.right(), r.top(), -1, 1),
                               (r.left(), r.bottom(), 1, -1), (r.right(), r.bottom(), -1, -1)):
            p.drawLine(QPointF(cx, cy), QPointF(cx + dx * arm, cy))
            p.drawLine(QPointF(cx, cy), QPointF(cx, cy + dy * arm))

    # bar heights of the little waveform (fixed: the scan moves, the shape doesn't)
    _BARS = (0.30, 0.45, 0.35, 0.55, 0.40, 0.62, 0.48, 0.95, 0.52, 0.38, 0.44, 0.58, 0.36, 0.50, 0.42, 1.00,
             0.56, 0.40, 0.34, 0.47, 0.60, 0.39, 0.88, 0.50, 0.36, 0.44, 0.31, 0.27)
    _PEAKS = (7, 15, 22)

    def _paint_peaks(self, p: QPainter):
        # One loop: the playhead eases across (0-68%), the found moments linger (68-80%), then everything fades
        # back to the resting waveform (80-100%), so the restart is invisible instead of a jump back to 0.
        def smooth(x):
            x = max(0.0, min(1.0, x))
            return x * x * (3.0 - 2.0 * x)

        t = self._pulse_pos
        n = len(self._BARS)
        step, bar_w, area_h = 5.5, 2.6, 30.0
        area_w = step * (n - 1)
        right, bottom = self.width() - 22.0, self.height() - 20.0
        left = right - area_w
        s = smooth(t / 0.68)
        head = left + area_w * s
        head_alpha = min(smooth(t / 0.06), smooth((1.0 - s) / 0.12))  # the playhead fades in and out at the ends
        fade = 1.0 - smooth((t - 0.80) / 0.20)                         # found moments fade out before the loop
        hover = self.underMouse()
        white = QColor("#FFFFFF")
        for i, v in enumerate(self._BARS):
            x = left + i * step
            bh = 3.0 + (area_h - 3.0) * v
            near = max(0.0, 1.0 - abs(x - head) / 26.0) * head_alpha
            if i in self._PEAKS:
                lit = smooth((head - x) / 10.0) * fade               # 0 -> 1 as the playhead passes, then fades
                base = self._color(self._core_color, 0.55 + 0.4 * near)
                color = QColor.fromRgbF(
                    base.redF() + (self._head_color.redF() - base.redF()) * lit,
                    base.greenF() + (self._head_color.greenF() - base.greenF()) * lit,
                    base.blueF() + (self._head_color.blueF() - base.blueF()) * lit,
                    base.alphaF() + (1.0 - base.alphaF()) * lit)
            else:
                lit = 0.0
                color = self._color(white, (0.14 if not hover else 0.2) + 0.45 * near)
            pen = QPen(color, bar_w)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(x, bottom), QPointF(x, bottom - bh))
            if lit > 0.01:                                       # a moment was found here
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(self._color(self._head_color, 0.95 * lit))
                p.drawEllipse(QPointF(x, bottom - bh - 4.0 - 2.0 * lit), 1.4 + 1.0 * lit, 1.4 + 1.0 * lit)
        if head_alpha > 0.01:
            p.setPen(QPen(self._color(self._core_color, 0.7 * head_alpha), 1.2))
            p.drawLine(QPointF(head, bottom + 3.0), QPointF(head, bottom - area_h - 6.0))


def paint_accent_icon(label, icon: str, size, color: str):
    pix = create_vector_icon(icon, color)
    if size:
        pix = pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    label.setPixmap(pix)


class MainWindowUI:
    def __init__(self, main_window):
        self.mw = main_window

    # Accent-coloured pieces built once at startup are registered here so a theme change can
    # re-render them (settings_mgr.on_theme_changed -> apply_accent).
    def _accent_icon(self, label, icon: str, size=None):
        if not hasattr(self.mw, "_theme_icons"):
            self.mw._theme_icons = []
        self.mw._theme_icons.append((label, icon, size))
        paint_accent_icon(label, icon, size, self.mw.settings_mgr.get_accent_hex())

    def _theme_restyle(self, widget, object_name: str):
        from ui.styles import object_rules
        if not hasattr(self.mw, "_theme_restyled"):
            self.mw._theme_restyled = []
        self.mw._theme_restyled.append((widget, object_name))
        widget.setStyleSheet(object_rules(self.mw.settings.get_theme_color(), object_name))

    def _accent_title(self, label):
        if not hasattr(self.mw, "_theme_titles"):
            self.mw._theme_titles = []
        self.mw._theme_titles.append(label)
        label.setStyleSheet(f"color: {self.mw.settings_mgr.get_accent_hex()};")

    def setup_ui(self):
        self.build_global_header()

        self.mw.global_status_banner = NotificationBanner(self.mw.app_widget)

        self.mw.view_stack = QStackedWidget()
        self.mw.view_stack.setObjectName("viewStack")
        self.mw.app_layout.addWidget(self.mw.view_stack)

        self.build_start_screen()         # 0
        self.build_analysis_screen()      # 1
        self.build_editor_screen()        # 2
        self.build_downloader_screen()    # 3
        self.build_settings_screen()      # 4
        self.build_highlights_screen()    # 5
        self.build_ai_config_screen()     # 6
        self.build_clipper_screen()       # 7
        self.mw.clip_editor_mgr.build_screen()   # 8: timeline editor for Auto Clipper clips

    # ------------------------------------------------------------------
    # Shared layout helpers (consistent page structure across all screens)
    # ------------------------------------------------------------------
    def _scroll_page(self, max_width: int = 980, margins=(40, 24, 40, 40)):
        """Scrollable screen with a centred content column. Returns (screen_widget, column_layout)."""
        screen = QWidget()
        screen.setObjectName("screenContainer")
        outer = QVBoxLayout(screen)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page = QWidget()
        page.setObjectName("screenContainer")
        scroll.setWidget(page)
        outer.addWidget(scroll)
        row = QHBoxLayout(page)
        row.setContentsMargins(*margins)
        row.addStretch()
        column = QWidget()
        # transparent like the page around it: an unnamed QWidget gets the app's base "QWidget { background:
        # #09090B }" and painted a solid block over the moving background (Home showed none, Settings did)
        column.setObjectName("screenContainer")
        column.setMaximumWidth(max_width)
        column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        col = QVBoxLayout(column)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        col.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.addWidget(column, 10)
        row.addStretch()
        return screen, col

    def _back_button(self, text: str, callback, icon: str = "home"):
        """A quiet text link back to where the user came from (the tabs above already show where they are)."""
        btn = QPushButton(f" {text}")
        btn.setIcon(QIcon(create_vector_icon(icon, "#8E8E99")))
        btn.setObjectName("ghostBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn

    def _page_header(self, col, title: str, subtitle: str = "", back=None, badge: str = ""):
        if back is not None:
            nav = QHBoxLayout()
            nav.addWidget(back)
            nav.addStretch()
            col.addLayout(nav)
            col.addSpacing(20)
        t_row = QHBoxLayout()
        t_row.setSpacing(10)
        t = QLabel(title)
        t.setObjectName("h1")
        t_row.addWidget(t)
        if badge:
            b = QLabel(badge)
            b.setObjectName("betaBadge")
            t_row.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        t_row.addStretch()
        col.addLayout(t_row)
        if subtitle:
            col.addSpacing(6)
            s = QLabel(subtitle)
            s.setObjectName("pageSubtitle")
            s.setWordWrap(True)
            col.addWidget(s)
        col.addSpacing(24)

    def _card(self, accent: bool = False, margins=(24, 22, 24, 24), spacing: int = 14):
        card = QFrame()
        card.setObjectName("surfaceCardAccent" if accent else "surfaceCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(*margins)
        lay.setSpacing(spacing)
        return card, lay

    def _section_head(self, lay, title: str, hint: str = "", icon: str = ""):
        row = QHBoxLayout()
        row.setSpacing(12)
        if icon:
            tile = QLabel()
            tile.setObjectName("iconTile")
            tile.setFixedSize(36, 36)
            tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._accent_icon(tile, icon, 20)
            row.addWidget(tile, 0, Qt.AlignmentFlag.AlignTop)
        txt = QVBoxLayout()
        txt.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("sectionTitle")
        txt.addWidget(t)
        if hint:
            h = QLabel(hint)
            h.setObjectName("sectionHint")
            h.setWordWrap(True)
            txt.addWidget(h)
        row.addLayout(txt, 1)
        lay.addLayout(row)

    def _setting_row(self, lay, title: str, hint: str, control):
        row = QHBoxLayout()
        row.setSpacing(16)
        txt = QVBoxLayout()
        txt.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("sectionTitle")
        h = QLabel(hint)
        h.setObjectName("sectionHint")
        h.setWordWrap(True)
        txt.addWidget(t)
        txt.addWidget(h)
        row.addLayout(txt, 1)
        row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(row)

    def _divider(self, lay):
        sep = QFrame()
        sep.setObjectName("divider")
        sep.setFixedHeight(1)
        lay.addWidget(sep)

    # ------------------------------------------------------------------
    # Global header
    # ------------------------------------------------------------------
    def build_global_header(self):
        """Brand, navigation and token balance, placed in the window's own title bar (ui/components/window_chrome:
        one bar with the window controls, no separate header or divider line)."""
        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent;")
        left_lay = QHBoxLayout(left_widget)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(10)

        logo_lbl = QLabel()
        png_path = get_asset_path("CRPR.png")
        ico_path = get_asset_path("CRPR.ico")
        pix = QPixmap()
        if os.path.exists(png_path):
            pix = QPixmap(png_path)
        elif os.path.exists(ico_path):
            pix = QIcon(ico_path).pixmap(QSize(256, 256))
        if not pix.isNull():
            pix = pix.scaled(26, 26, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)

        title = QLabel("CReaper")
        title.setObjectName("appTitle")
        title.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        # Version from the one central constant (utils/settings.py AppSettings.APP_VERSION), never typed here
        from utils.settings import AppSettings
        self.mw.app_version_lbl = QLabel(f"v{AppSettings.APP_VERSION}")
        self.mw.app_version_lbl.setObjectName("appVersion")
        self.mw.app_version_lbl.setToolTip(f"CReaper version {AppSettings.APP_VERSION}")
        self.mw.app_version_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        brand = QHBoxLayout()
        brand.setContentsMargins(0, 0, 0, 0)
        brand.setSpacing(6)
        brand.addWidget(title, 0, Qt.AlignmentFlag.AlignVCenter)
        # its 4px top padding (styles.py) lines the smaller text up with the title's baseline
        brand.addWidget(self.mw.app_version_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        left_lay.addWidget(logo_lbl)
        left_lay.addLayout(brand)

        center_widget = QFrame()
        center_widget.setObjectName("navBar")
        center_lay = QHBoxLayout(center_widget)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(2)

        accent = self.mw.settings_mgr.get_accent_hex()

        def nav_btn(text, icon, tooltip):
            b = QPushButton(f" {text}")
            b.setIcon(create_multi_state_icon(icon, active_color=accent))
            b.setIconSize(QSize(16, 16))
            b.setObjectName("headerBtn")
            b.setToolTip(tooltip)
            from ui.components.window_chrome import TITLE_BAR_HEIGHT
            b.setFixedHeight(TITLE_BAR_HEIGHT)            # the active tab's underline sits on the bar's edge
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setCheckable(True)
            return b

        self.mw.home_btn = nav_btn("Home", "home", "Home")
        self.mw.home_btn.setChecked(True)
        self.mw.home_btn.clicked.connect(self.mw.workflow_mgr.reset_to_home)
        self.mw.highlights_btn = nav_btn("Highlights", "bookmark", "Highlighted Clips")
        self.mw.highlights_btn.clicked.connect(self.mw.highlights_mgr.open_highlights)
        self.mw.settings_btn = nav_btn("Settings", "gear", "Settings")
        self.mw.settings_btn.clicked.connect(self.mw.settings_mgr.open_settings)

        self.mw.header_btn_group = QButtonGroup(center_widget)
        self.mw.header_btn_group.setExclusive(True)
        self.mw.header_btn_group.addButton(self.mw.home_btn, 0)
        self.mw.header_btn_group.addButton(self.mw.highlights_btn, 1)
        self.mw.header_btn_group.addButton(self.mw.settings_btn, 4)

        center_lay.addWidget(self.mw.home_btn)
        center_lay.addWidget(self.mw.highlights_btn)
        center_lay.addWidget(self.mw.settings_btn)

        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent;")
        right_lay = QHBoxLayout(right_widget)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.addStretch()

        self.mw.token_chip, self.mw.token_lbl = make_token_badge("0", size=18)
        self.mw.token_chip.setToolTip("Your token balance. Click to get tokens in the CReaper Discord server.")
        make_clickable(self.mw.token_chip, lambda: self.mw.account_mgr.open_purchase(),
                       "Token balance: open the purchase channel")
        right_lay.addWidget(self.mw.token_chip, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        bar = self.mw.title_bar
        bar.left.addWidget(left_widget)
        bar.center.addWidget(center_widget)
        bar.right.addWidget(right_widget)
        self.mw.title_app_items = [center_widget, right_widget]

    # ------------------------------------------------------------------
    # Home
    # ------------------------------------------------------------------
    def _mode_card(self, button, icon_name, icon_color, title_text, desc_text, title_lbl=None, icon_lbl=None):
        button.setMinimumSize(300, 150)
        button.setMaximumHeight(176)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QVBoxLayout(button)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(12)
        tile = icon_lbl if icon_lbl is not None else QLabel()
        tile.setObjectName("iconTile")
        tile.setFixedSize(40, 40)
        tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_color == self.mw.settings_mgr.get_accent_hex():
            self._accent_icon(tile, icon_name)               # follows the theme
        else:
            tile.setPixmap(create_vector_icon(icon_name, icon_color))
        tile.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        t = title_lbl if title_lbl is not None else QLabel(title_text)
        t.setText(title_text)
        t.setObjectName("h2")
        t.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        head.addWidget(tile)
        head.addWidget(t, 1)
        lay.addLayout(head)

        d = QLabel(desc_text)
        d.setObjectName("sectionHint")
        d.setWordWrap(True)
        d.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lay.addWidget(d)
        lay.addStretch()
        return lay

    def _card_tag(self, text, object_name="pill"):
        tag = QLabel(text)
        tag.setObjectName(object_name)
        tag.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row = QHBoxLayout()
        row.addWidget(tag)
        row.addStretch()
        return row

    def build_start_screen(self):
        start_widget, col = self._scroll_page(max_width=900, margins=(40, 40, 40, 40))

        hero = QLabel("Create your next clip")
        hero.setObjectName("displayTitle")
        hero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(hero)
        col.addSpacing(8)
        sub = QLabel("Paste a video link (YouTube, TikTok, Instagram, Facebook, Twitch...) or open a local video, then pick how you want to cut it.")
        sub.setObjectName("pageSubtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        col.addWidget(sub)
        col.addSpacing(28)

        input_card, in_lay = self._card(margins=(10, 10, 10, 10), spacing=0)
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self.mw.url_input = QLineEdit()
        self.mw.url_input.setObjectName("heroInput")
        self.mw.url_input.setPlaceholderText("Paste a video link (YouTube, TikTok, Instagram, Facebook, Twitch...)")
        self.mw.url_input.setMinimumHeight(48)
        self.mw.url_input.addAction(QIcon(create_vector_icon("link", "#71717A")), QLineEdit.ActionPosition.LeadingPosition)
        self.mw.url_input.textChanged.connect(self.mw.workflow_mgr.on_home_url_changed)
        upload_btn = QPushButton(" Choose file")
        upload_btn.setIcon(QIcon(create_vector_icon("folder", "#D4D4D8")))
        upload_btn.setObjectName("secondaryBtn")
        upload_btn.setMinimumHeight(48)
        upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        upload_btn.clicked.connect(self.mw.workflow_mgr.upload_local_video)
        input_row.addWidget(self.mw.url_input, 1)
        input_row.addWidget(upload_btn)
        in_lay.addLayout(input_row)
        col.addWidget(input_card)
        col.addSpacing(32)

        sec = QLabel("CHOOSE A WORKFLOW")
        sec.setObjectName("fieldLabel")
        col.addWidget(sec)
        col.addSpacing(12)

        active_theme = self.mw.settings.get_theme_color()
        active_accent = self.mw.settings_mgr.get_accent_hex()

        flow_lay = QGridLayout()
        flow_lay.setHorizontalSpacing(16)
        flow_lay.setVerticalSpacing(16)

        manual_btn = QPushButton()
        manual_btn.setObjectName("modeCardManual")
        manual_btn.clicked.connect(lambda: self.mw.workflow_mgr.start_workflow(is_ai=False))
        m_lay = self._mode_card(manual_btn, "scissors", "#FAFAFA", "Standard Trim",
                                "Pick the exact start and end yourself and export the section.")
        m_lay.addLayout(self._card_tag("Manual"))

        self.mw.ai_btn = AnimatedAICard(theme=active_theme, effect="peaks")
        self.mw.ai_btn.setObjectName("modeCardAI")
        self.mw.ai_btn.clicked.connect(lambda: self.mw.account_mgr.guard_ai(
            lambda: self.mw.workflow_mgr.start_workflow(is_ai=True)))
        self.mw.ai_icon_lbl = QLabel()
        self.mw.ai_title_lbl = QLabel()
        a_lay = self._mode_card(self.mw.ai_btn, "sparkle", active_accent, "AI Best Moments",
                                "AI scans the whole video and suggests the strongest moments to clip.",
                                title_lbl=self.mw.ai_title_lbl, icon_lbl=self.mw.ai_icon_lbl)
        self._accent_title(self.mw.ai_title_lbl)
        # Token balance chip, styled like Auto Clipper's token chip (ai_usage_lbl is its text label)
        ai_tag_row = QHBoxLayout()
        ai_tag_row.setSpacing(8)
        ai_token_chip, self.mw.ai_usage_lbl = make_token_badge("Token required", size=14)
        ai_token_chip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        ai_tag_row.addWidget(ai_token_chip)
        ai_tag_row.addStretch()
        a_lay.addLayout(ai_tag_row)

        from ui.main_window_clipper import AI_CLIPPER_LOCKED
        if AI_CLIPPER_LOCKED:
            # Temporarily locked: plain, disabled card (no click handler, greyed out, lock icon)
            clipper_mode_btn = QPushButton()
            clipper_mode_btn.setObjectName("modeCardLocked")
            clipper_mode_btn.setToolTip("Auto Clipper is temporarily unavailable while we improve how it picks moments.")
            cl_title = QLabel()
            c_lay = self._mode_card(clipper_mode_btn, "lock", "#71717A", "Auto Clipper",
                                    "Temporarily unavailable while we improve how it picks moments. "
                                    "All other tools work as usual.",
                                    title_lbl=cl_title)
            cl_title.setStyleSheet("color: #71717A;")
            c_lay.addLayout(self._card_tag("TEMPORARILY UNAVAILABLE", "lockedBadge"))
            clipper_mode_btn.setCursor(Qt.CursorShape.ForbiddenCursor)
            clipper_mode_btn.setEnabled(False)
        else:
            clipper_mode_btn = AnimatedAICard(theme=active_theme, effect="viewfinder")
            clipper_mode_btn.setObjectName("modeCardAI")
            clipper_mode_btn.clicked.connect(lambda: self.mw.account_mgr.guard_ai(
                lambda: self.mw.clipper_mgr.show_clipper_screen(self.mw.url_input.text().strip())))
            cl_title = QLabel()
            c_lay = self._mode_card(clipper_mode_btn, "film", active_accent, "Auto Clipper",
                                    "Ready-to-post clips from a long video: the best moments, framed on the subject, with captions.",
                                    title_lbl=cl_title)
            self._accent_title(cl_title)
            tag_row = QHBoxLayout()
            tag_row.setSpacing(8)
            beta = QLabel("BETA")
            beta.setObjectName("betaBadge")
            beta.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            cost_chip, self.mw.clipper_card_cost_lbl = make_token_badge("Tokens required", size=14)
            cost_chip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            tag_row.addWidget(beta)
            tag_row.addWidget(cost_chip)
            tag_row.addStretch()
            c_lay.addLayout(tag_row)
        self.mw.clipper_mode_btn = clipper_mode_btn

        dl_mode_btn = QPushButton()
        dl_mode_btn.setObjectName("modeCardManual")
        dl_mode_btn.clicked.connect(lambda: self.mw.downloader_mgr.show_downloader_screen(self.mw.url_input.text().strip()))
        d_lay = self._mode_card(dl_mode_btn, "download", "#FAFAFA", "MP3 / MP4 Downloader",
                                "Save full videos as MP4 or extract the audio as MP3.")
        d_lay.addLayout(self._card_tag("MP4  ·  MP3"))

        flow_lay.addWidget(clipper_mode_btn, 0, 0)
        flow_lay.addWidget(self.mw.ai_btn, 0, 1)
        flow_lay.addWidget(manual_btn, 1, 0)
        flow_lay.addWidget(dl_mode_btn, 1, 1)
        col.addLayout(flow_lay)
        col.addStretch(1)

        self.mw.view_stack.addWidget(start_widget)

    # ------------------------------------------------------------------
    # AI analysis (loading)
    # ------------------------------------------------------------------
    def build_analysis_screen(self):
        analysis_widget = QWidget()
        analysis_widget.setObjectName("screenContainer")
        lay = QVBoxLayout(analysis_widget)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card, c_lay = self._card(accent=True, margins=(40, 36, 40, 36), spacing=0)
        card.setFixedWidth(480)
        c_lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        tile = QLabel()
        tile.setObjectName("iconTile")
        tile.setFixedSize(52, 52)
        tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._accent_icon(tile, "sparkle")
        title = QLabel("Finding the best moments")
        title.setObjectName("h2")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel("AI is reading the transcript and scoring every section of the video.")
        hint.setObjectName("sectionHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        self.mw.ai_prog = QProgressBar()
        self.mw.ai_prog.setObjectName("bigProgress")
        self.mw.ai_prog.setMinimum(0)
        self.mw.ai_prog.setMaximum(0)
        self.mw.ai_prog.setFixedWidth(360)
        self.mw.ai_prog.setFixedHeight(8)
        self.mw.analysis_status = QLabel("Preparing your video...")
        self.mw.analysis_status.setObjectName("sectionHint")
        self.mw.analysis_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mw.analysis_status.setWordWrap(True)

        c_lay.addWidget(tile, alignment=Qt.AlignmentFlag.AlignCenter)
        c_lay.addSpacing(16)
        c_lay.addWidget(title)
        c_lay.addSpacing(6)
        c_lay.addWidget(hint)
        c_lay.addSpacing(24)
        c_lay.addWidget(self.mw.ai_prog, alignment=Qt.AlignmentFlag.AlignCenter)
        c_lay.addSpacing(14)
        c_lay.addWidget(self.mw.analysis_status)
        lay.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        self.mw.view_stack.addWidget(analysis_widget)

    # ------------------------------------------------------------------
    # Editor (Standard Trim / AI suggestions)
    # ------------------------------------------------------------------
    def build_editor_screen(self):
        """
        Standard Trim: the video itself (Qt Multimedia preview), playback controls, an interactive
        trim timeline (handles + playhead), exact start/end fields and the export row. The AI
        suggestions sidebar (AI Best Moments) stays on the right.
        """
        from ui.components.trim_timeline import TrimTimeline
        from ui.components.video_preview import VideoPreview
        accent = self.mw.settings_mgr.get_accent_hex()
        editor_widget = QWidget()
        editor_widget.setObjectName("screenContainer")
        main_h_lay = QHBoxLayout(editor_widget)
        main_h_lay.setContentsMargins(28, 18, 28, 22)
        main_h_lay.setSpacing(22)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # --- header: back, title, duration
        nav_lay = QHBoxLayout()
        nav_lay.setSpacing(12)
        nav_lay.addWidget(self._back_button("Change Video", self.mw.workflow_mgr.reset_to_home))
        self.mw.video_title_lbl = QLabel("Video Title")
        self.mw.video_title_lbl.setObjectName("mediaTitle")
        self.mw.video_title_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.mw.video_dur_lbl = QLabel("Duration: 00:00")
        self.mw.video_dur_lbl.setObjectName("pill")
        nav_lay.addWidget(self.mw.video_title_lbl, 1)
        nav_lay.addWidget(self.mw.video_dur_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        left_col.addLayout(nav_lay)
        # kept for the code that sets a thumbnail; the real preview replaces it
        self.mw.thumb_lbl = QLabel()
        self.mw.thumb_lbl.hide()

        # --- the preview
        preview_card = QFrame()
        preview_card.setObjectName("previewCard")
        pc_lay = QVBoxLayout(preview_card)
        pc_lay.setContentsMargins(0, 0, 0, 0)
        self.mw.video_preview = VideoPreview()
        pc_lay.addWidget(self.mw.video_preview)
        left_col.addWidget(preview_card, 1)

        # --- playback controls
        ctl = QHBoxLayout()
        ctl.setSpacing(8)
        self.mw.play_btn = QPushButton()
        self.mw.play_btn.setObjectName("playerBtn")
        self.mw.play_btn.setIcon(QIcon(create_vector_icon("play", "#FAFAFA")))
        self.mw.play_btn.setIconSize(QSize(18, 18))
        self.mw.play_btn.setFixedSize(40, 36)
        self.mw.play_btn.setToolTip("Play / pause (Space)")
        self.mw.play_btn.setAccessibleName("Play or pause")
        self.mw.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.play_btn.clicked.connect(self.mw.editor_mgr.toggle_play)
        self.mw.time_lbl = QLabel("00:00:00 / 00:00:00")
        self.mw.time_lbl.setObjectName("timeLabel")
        self.mw.time_lbl.setMinimumWidth(150)
        self.mw.mute_btn = QPushButton()
        self.mw.mute_btn.setObjectName("playerBtn")
        self.mw.mute_btn.setIcon(QIcon(create_vector_icon("volume", "#D4D4D8")))
        self.mw.mute_btn.setIconSize(QSize(18, 18))
        self.mw.mute_btn.setFixedSize(36, 36)
        self.mw.mute_btn.setToolTip("Mute / unmute")
        self.mw.mute_btn.setAccessibleName("Mute")
        self.mw.mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.mute_btn.clicked.connect(self.mw.editor_mgr.toggle_mute)
        self.mw.volume_slider = TrackSlider(Qt.Orientation.Horizontal)
        self.mw.volume_slider.setRange(0, 100)
        self.mw.volume_slider.setValue(80)
        self.mw.volume_slider.setFixedWidth(90)
        self.mw.volume_slider.setAccessibleName("Volume")
        self.mw.volume_slider.valueChanged.connect(self.mw.editor_mgr.on_volume)
        self.mw.set_start_btn = QPushButton("Set start")
        self.mw.set_end_btn = QPushButton("Set end")
        for btn, tip in ((self.mw.set_start_btn, "Start the clip at the current playhead (I)"),
                         (self.mw.set_end_btn, "End the clip at the current playhead (O)")):
            btn.setObjectName("secondaryBtn")
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.set_start_btn.clicked.connect(self.mw.editor_mgr.set_start_here)
        self.mw.set_end_btn.clicked.connect(self.mw.editor_mgr.set_end_here)
        self.mw.preview_sel_btn = QPushButton(" Preview selection")
        self.mw.preview_sel_btn.setObjectName("secondaryBtn")
        self.mw.preview_sel_btn.setIcon(QIcon(create_vector_icon("loop", accent)))
        self.mw.preview_sel_btn.setCheckable(True)
        self.mw.preview_sel_btn.setToolTip("Play only the selected part, then stop")
        self.mw.preview_sel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.preview_sel_btn.clicked.connect(self.mw.editor_mgr.toggle_selection_preview)
        ctl.addWidget(self.mw.play_btn)
        ctl.addWidget(self.mw.time_lbl)
        ctl.addStretch(1)
        ctl.addWidget(self.mw.set_start_btn)
        ctl.addWidget(self.mw.set_end_btn)
        ctl.addWidget(self.mw.preview_sel_btn)
        ctl.addSpacing(10)
        ctl.addWidget(self.mw.mute_btn)
        ctl.addWidget(self.mw.volume_slider)
        left_col.addLayout(ctl)

        # --- timeline + exact times + export
        editor_panel, e_lay = self._card(margins=(18, 12, 18, 14), spacing=10)
        self.mw.slider = TrimTimeline(accent=accent)
        self.mw.slider.rangeChanged.connect(self.mw.editor_mgr.on_slider_moved)
        self.mw.slider.seekRequested.connect(self.mw.editor_mgr.on_timeline_seek)
        self.mw.slider.handleReleased.connect(self.mw.editor_mgr.on_handle_released)
        e_lay.addWidget(self.mw.slider)

        times_lay = QHBoxLayout()
        times_lay.setSpacing(8)
        st_lbl = QLabel("START")
        st_lbl.setObjectName("fieldLabel")
        self.mw.st_in = QLineEdit()
        self.mw.st_in.setFixedWidth(108)
        self.mw.st_in.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mw.st_in.setToolTip("Start time: HH:MM:SS or HH:MM:SS.s")
        self.mw.st_in.setAccessibleName("Start time")
        self.mw.st_in.editingFinished.connect(self.mw.editor_mgr.on_ts_edited)
        en_lbl = QLabel("END")
        en_lbl.setObjectName("fieldLabel")
        self.mw.en_in = QLineEdit()
        self.mw.en_in.setFixedWidth(108)
        self.mw.en_in.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mw.en_in.setToolTip("End time: HH:MM:SS or HH:MM:SS.s")
        self.mw.en_in.setAccessibleName("End time")
        self.mw.en_in.editingFinished.connect(self.mw.editor_mgr.on_ts_edited)
        self.mw.out_dur_lbl = QLabel("Selected 00:00:00.0")
        self.mw.out_dur_lbl.setObjectName("pillAccent")
        times_lay.addWidget(st_lbl)
        times_lay.addWidget(self.mw.st_in)
        times_lay.addSpacing(6)
        times_lay.addWidget(en_lbl)
        times_lay.addWidget(self.mw.en_in)
        times_lay.addSpacing(6)
        times_lay.addWidget(self.mw.out_dur_lbl)
        times_lay.addStretch(1)
        self.mw.ts_error_lbl = QLabel("")
        self.mw.ts_error_lbl.setStyleSheet("color: #F87171; font-size: 12px;")
        times_lay.addWidget(self.mw.ts_error_lbl)
        e_lay.addLayout(times_lay)

        self._divider(e_lay)
        export_lay = QHBoxLayout()
        export_lay.setSpacing(10)
        folder_icon = QLabel()
        folder_icon.setPixmap(create_vector_icon("folder", "#A1A1AA").scaled(
            18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.mw.f_lbl = QLabel(f"Save to: {self.mw.settings.get_output_folder()[-28:]}")
        self.mw.f_lbl.setObjectName("sectionHint")
        self.mw.f_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        f_btn = QPushButton("Change")
        f_btn.setObjectName("secondaryBtn")
        f_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        f_btn.clicked.connect(self.mw.editor_mgr.change_folder)
        self.mw.exp_prog = QProgressBar()
        self.mw.exp_prog.setObjectName("bigProgress")
        self.mw.exp_prog.setFixedHeight(8)
        self.mw.exp_prog.hide()
        self.mw.open_folder_btn = QPushButton("Open folder")
        self.mw.play_clip_btn = QPushButton("Play clip")
        for btn in (self.mw.open_folder_btn, self.mw.play_clip_btn):
            btn.setObjectName("secondaryBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.hide()
        self.mw.open_folder_btn.clicked.connect(self.mw.editor_mgr.open_output_folder)
        self.mw.play_clip_btn.clicked.connect(self.mw.editor_mgr.play_output_clip)
        self.mw.cancel_trim_btn = QPushButton("Cancel")
        self.mw.cancel_trim_btn.setObjectName("secondaryBtn")
        self.mw.cancel_trim_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.cancel_trim_btn.clicked.connect(self.mw.editor_mgr.cancel_trim)
        self.mw.cancel_trim_btn.hide()
        self.mw.trim_btn = QPushButton(" Trim && Download")
        self.mw.trim_btn.setIcon(QIcon(create_vector_icon("download", "#FFFFFF")))
        self.mw.trim_btn.setObjectName("trimButton")
        self.mw.trim_btn.setMinimumHeight(44)
        self.mw.trim_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.trim_btn.clicked.connect(self.mw.editor_mgr.start_trim)
        export_lay.addWidget(folder_icon)
        export_lay.addWidget(self.mw.f_lbl, 1)
        export_lay.addWidget(f_btn)
        export_lay.addWidget(self.mw.exp_prog, 1)
        export_lay.addWidget(self.mw.open_folder_btn)
        export_lay.addWidget(self.mw.play_clip_btn)
        export_lay.addWidget(self.mw.cancel_trim_btn)
        export_lay.addWidget(self.mw.trim_btn)
        e_lay.addLayout(export_lay)
        left_col.addWidget(editor_panel)
        main_h_lay.addLayout(left_col, 6)

        # --- player <-> timeline wiring
        vp = self.mw.video_preview
        vp.positionChanged.connect(self.mw.editor_mgr.on_position)
        vp.durationChanged.connect(self.mw.editor_mgr.on_player_duration)
        vp.playingChanged.connect(self.mw.editor_mgr.on_playing_changed)
        vp.rangeFinished.connect(self.mw.editor_mgr.on_range_finished)
        vp.ready.connect(self.mw.editor_mgr.on_preview_ready)
        vp.noPicture.connect(self.mw.editor_mgr.on_no_picture)
        from PyQt6.QtGui import QShortcut, QKeySequence
        for key, fn in (("Space", self.mw.editor_mgr.toggle_play), ("I", self.mw.editor_mgr.set_start_here),
                        ("O", self.mw.editor_mgr.set_end_here)):
            sc = QShortcut(QKeySequence(key), editor_widget)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)

        self.mw.sidebar = QFrame()
        self.mw.sidebar.setObjectName("sidebarPanel")
        side_lay = QVBoxLayout(self.mw.sidebar)
        side_lay.setContentsMargins(20, 4, 0, 0)
        side_lay.setSpacing(12)
        self._section_head(side_lay, "Suggested clips", "Ranked by score: #1 is the strongest. Times are from the "
                           "original video. Use one to load it into the trim range.", icon="sparkle")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.mw.scroll_widget = QWidget()
        self.mw.ai_cards_layout = QVBoxLayout(self.mw.scroll_widget)
        self.mw.ai_cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.mw.ai_cards_layout.setContentsMargins(0, 0, 12, 0)
        self.mw.ai_cards_layout.setSpacing(12)
        scroll.setWidget(self.mw.scroll_widget)
        side_lay.addWidget(scroll)
        main_h_lay.addWidget(self.mw.sidebar, 4)
        self.mw.sidebar.hide()
        self.mw.view_stack.addWidget(editor_widget)

    # ------------------------------------------------------------------
    # Downloader
    # ------------------------------------------------------------------
    def _option_card(self, button: QPushButton, icon_name: str, title: str, subtitle: str):
        """Checkable selection card with an icon, title and one-line description."""
        button.setObjectName("optionCard")
        button.setCheckable(True)
        button.setMinimumHeight(72)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(button)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)
        tile = QLabel()
        tile.setObjectName("iconTile")
        tile.setFixedSize(40, 40)
        tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._accent_icon(tile, icon_name)
        tile.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        txt = QVBoxLayout()
        txt.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("sectionTitle")
        t.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        s = QLabel(subtitle)
        s.setObjectName("sectionHint")
        s.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        txt.addWidget(t)
        txt.addWidget(s)
        lay.addWidget(tile)
        lay.addLayout(txt, 1)
        return button

    def _summary_row(self, lay, key: str, value_lbl: QLabel):
        row = QHBoxLayout()
        k = QLabel(key)
        k.setObjectName("metaKey")
        value_lbl.setObjectName("metaValue")
        row.addWidget(k)
        row.addStretch()
        row.addWidget(value_lbl)
        lay.addLayout(row)

    def build_downloader_screen(self):
        dl_widget, col = self._scroll_page(max_width=980)
        self._page_header(col, "MP3 / MP4 Downloader", "Download a video or its audio from YouTube, TikTok, Instagram and more, or convert a file on your PC (no internet needed).",
                          back=self._back_button("Home", self.mw.workflow_mgr.reset_to_home))

        # =========================================================
        # INPUT STATE: options (left) + summary / action (right)
        # =========================================================
        self.mw.dl_input_container = QWidget()
        in_row = QHBoxLayout(self.mw.dl_input_container)
        in_row.setContentsMargins(0, 0, 0, 0)
        in_row.setSpacing(20)

        opts_card, input_v = self._card(margins=(26, 24, 26, 26), spacing=0)

        # Link
        link_lbl = QLabel("VIDEO LINK OR FILE")
        link_lbl.setObjectName("fieldLabel")
        input_v.addWidget(link_lbl)
        input_v.addSpacing(8)
        self.mw.dl_url_input = QLineEdit()
        self.mw.dl_url_input.setPlaceholderText("Paste a video link  -  YouTube, TikTok, Instagram, Facebook, Twitch...")
        self.mw.dl_url_input.setMinimumHeight(48)
        self.mw.dl_url_input.addAction(QIcon(create_vector_icon("link", "#71717A")), QLineEdit.ActionPosition.LeadingPosition)
        self.mw.dl_url_input.returnPressed.connect(self.mw.downloader_mgr.start_download)
        self.mw.dl_url_input.textChanged.connect(lambda _t: self.mw.downloader_mgr.on_format_changed())
        dl_src_row = QHBoxLayout()
        dl_src_row.setSpacing(10)
        dl_browse_btn = QPushButton(" Browse")
        dl_browse_btn.setIcon(QIcon(create_vector_icon("folder", "#D4D4D8")))
        dl_browse_btn.setObjectName("secondaryBtn")
        dl_browse_btn.setMinimumHeight(48)
        dl_browse_btn.setToolTip("Choose a video or audio file on your PC to convert")
        dl_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dl_browse_btn.clicked.connect(self.mw.downloader_mgr.browse_local_file)
        dl_src_row.addWidget(self.mw.dl_url_input, 1)
        dl_src_row.addWidget(dl_browse_btn)
        input_v.addLayout(dl_src_row)
        input_v.addSpacing(6)
        link_hint = QLabel("Paste a video link to download, or browse a local video/audio file to convert it offline.")
        link_hint.setObjectName("sectionHint")
        input_v.addWidget(link_hint)
        input_v.addSpacing(24)

        # Format
        fmt_lbl = QLabel("FORMAT")
        fmt_lbl.setObjectName("fieldLabel")
        input_v.addWidget(fmt_lbl)
        input_v.addSpacing(8)
        fmt_h = QGridLayout()
        fmt_h.setHorizontalSpacing(12)
        fmt_h.setVerticalSpacing(12)
        self.mw.dl_fmt_mp4 = self._option_card(QPushButton(), "film", "MP4 Video", "Video with audio")
        self.mw.dl_fmt_mp4.setChecked(True)
        self.mw.dl_fmt_mp3 = self._option_card(QPushButton(), "download", "MP3 Audio", "Audio track only")
        self.mw.dl_fmt_m4a = self._option_card(QPushButton(), "download", "M4A Audio", "AAC, small files")
        self.mw.dl_fmt_wav = self._option_card(QPushButton(), "download", "WAV Audio", "Lossless, for editing")
        fmt_group = QButtonGroup(self.mw.dl_input_container)
        fmt_group.setExclusive(True)
        for i, b in enumerate((self.mw.dl_fmt_mp4, self.mw.dl_fmt_mp3, self.mw.dl_fmt_m4a, self.mw.dl_fmt_wav)):
            fmt_group.addButton(b)
            fmt_h.addWidget(b, i // 2, i % 2)
        self.mw.dl_fmt_group = fmt_group
        input_v.addLayout(fmt_h)
        input_v.addSpacing(24)

        # Quality
        self.mw.dl_quality_lbl = QLabel("VIDEO QUALITY")
        self.mw.dl_quality_lbl.setObjectName("fieldLabel")
        input_v.addWidget(self.mw.dl_quality_lbl)
        input_v.addSpacing(8)

        def quality_row(options, tips):
            w = QWidget()
            w.setProperty("cardContent", True)
            row = QHBoxLayout(w)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            group = QButtonGroup(w)
            group.setExclusive(True)
            for i, q in enumerate(options):
                btn = QPushButton(q)
                btn.setObjectName("qualityCard")
                btn.setCheckable(True)
                btn.setMinimumHeight(40)
                btn.setToolTip(tips.get(q, ""))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                if i == 0:
                    btn.setChecked(True)
                group.addButton(btn)
                row.addWidget(btn)
            return w, group

        self.mw.dl_qual_mp4_widget, self.mw.dl_mp4_qual_group = quality_row(
            ["Best", "1080p", "720p", "480p"],
            {"Best": "Highest quality available", "480p": "Smallest file size"})
        input_v.addWidget(self.mw.dl_qual_mp4_widget)
        self.mw.dl_qual_mp3_widget, self.mw.dl_mp3_qual_group = quality_row(
            ["320k", "256k", "192k", "128k"],
            {"320k": "Highest audio bitrate", "128k": "Smallest file size"})
        self.mw.dl_qual_mp3_widget.hide()
        input_v.addWidget(self.mw.dl_qual_mp3_widget)
        input_v.addStretch(1)

        fmt_group.buttonToggled.connect(lambda _b, _c: self.mw.downloader_mgr.on_format_changed())
        self.mw.dl_mp4_qual_group.buttonClicked.connect(lambda _b: self.mw.downloader_mgr.update_summary())
        self.mw.dl_mp3_qual_group.buttonClicked.connect(lambda _b: self.mw.downloader_mgr.update_summary())

        # Summary / action panel
        summary, s_lay = self._card(accent=True, margins=(24, 22, 24, 24), spacing=12)
        summary.setFixedWidth(300)
        s_title = QLabel("Download summary")
        s_title.setObjectName("sectionTitle")
        s_lay.addWidget(s_title)
        self.mw.dl_sum_format = QLabel("MP4 Video")
        self.mw.dl_sum_quality = QLabel("Best")
        self._summary_row(s_lay, "FORMAT", self.mw.dl_sum_format)
        self._summary_row(s_lay, "QUALITY", self.mw.dl_sum_quality)
        self._divider(s_lay)

        save_lbl = QLabel("SAVE TO")
        save_lbl.setObjectName("metaKey")
        s_lay.addWidget(save_lbl)
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self.mw.dl_f_lbl = QLabel("...")
        self.mw.dl_f_lbl.setObjectName("pathField")
        self.mw.dl_f_lbl.setMinimumWidth(80)
        f_btn = QPushButton()
        f_btn.setIcon(QIcon(create_vector_icon("folder", "#D4D4D8")))
        f_btn.setObjectName("secondaryBtn")
        f_btn.setToolTip("Change output folder")
        f_btn.setFixedSize(40, 36)
        f_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        f_btn.clicked.connect(self.mw.downloader_mgr.change_folder)
        folder_row.addWidget(self.mw.dl_f_lbl, 1)
        folder_row.addWidget(f_btn)
        s_lay.addLayout(folder_row)
        s_lay.addSpacing(8)

        self.mw.dl_btn = QPushButton(" Download")
        self.mw.dl_btn.setIcon(QIcon(create_vector_icon("download", "#FFFFFF")))
        self.mw.dl_btn.setObjectName("primaryButton")
        self.mw.dl_btn.setMinimumHeight(50)
        self.mw.dl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.dl_btn.clicked.connect(self.mw.downloader_mgr.start_download)
        s_lay.addWidget(self.mw.dl_btn)
        dl_hint = QLabel("Downloads run in the background. You can cancel at any time.")
        dl_hint.setObjectName("sectionHint")
        dl_hint.setWordWrap(True)
        dl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s_lay.addWidget(dl_hint)
        s_lay.addStretch()

        in_row.addWidget(opts_card, 1)
        in_row.addWidget(summary, 0, Qt.AlignmentFlag.AlignTop)
        col.addWidget(self.mw.dl_input_container)

        # =========================================================
        # PROGRESS STATE
        # =========================================================
        self.mw.dl_progress_container, prog_v = self._card(margins=(28, 26, 28, 26), spacing=0)
        head = QHBoxLayout()
        head.setSpacing(14)
        self.mw.dl_prog_icon = QLabel()
        self.mw.dl_prog_icon.setObjectName("iconTile")
        self.mw.dl_prog_icon.setFixedSize(48, 48)
        self.mw.dl_prog_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._accent_icon(self.mw.dl_prog_icon, "download")
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.mw.dl_prog_title = QLabel("Downloading")
        self.mw.dl_prog_title.setObjectName("sectionTitle")
        self.mw.dl_prog_sub = QLabel("")
        self.mw.dl_prog_sub.setObjectName("sectionHint")
        titles.addWidget(self.mw.dl_prog_title)
        titles.addWidget(self.mw.dl_prog_sub)
        self.mw.dl_prog_pct = QLabel("0%")
        self.mw.dl_prog_pct.setObjectName("statValue")
        head.addWidget(self.mw.dl_prog_icon)
        head.addLayout(titles, 1)
        head.addWidget(self.mw.dl_prog_pct, 0, Qt.AlignmentFlag.AlignVCenter)
        prog_v.addLayout(head)
        prog_v.addSpacing(18)
        self.mw.dl_prog = QProgressBar()
        self.mw.dl_prog.setObjectName("bigProgress")
        self.mw.dl_prog.setTextVisible(False)
        self.mw.dl_prog.setFixedHeight(10)
        prog_v.addWidget(self.mw.dl_prog)
        prog_v.addSpacing(10)
        info_row = QHBoxLayout()
        self.mw.dl_prog_info = QLabel("Preparing...")
        self.mw.dl_prog_info.setObjectName("sectionHint")
        self.mw.dl_cancel_btn = QPushButton(" Cancel")
        self.mw.dl_cancel_btn.setIcon(QIcon(create_vector_icon("x", "#FCA5A5")))
        self.mw.dl_cancel_btn.setObjectName("dangerGhostBtn")
        self.mw.dl_cancel_btn.setMinimumHeight(38)
        self.mw.dl_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.dl_cancel_btn.clicked.connect(self.mw.downloader_mgr.cancel_download)
        info_row.addWidget(self.mw.dl_prog_info, 1)
        info_row.addWidget(self.mw.dl_cancel_btn)
        prog_v.addLayout(info_row)
        self.mw.dl_progress_container.hide()
        col.addWidget(self.mw.dl_progress_container)

        # =========================================================
        # COMPLETE STATE
        # =========================================================
        self.mw.dl_complete_container, comp_v = self._card(margins=(28, 24, 28, 26), spacing=0)
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        ok_icon = QLabel()
        ok_icon.setPixmap(create_vector_icon("check-circle", "#10B981").scaled(
            20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.mw.dl_ok_pill = QLabel("DOWNLOAD COMPLETE")
        self.mw.dl_ok_pill.setObjectName("successPill")
        status_row.addWidget(ok_icon)
        status_row.addWidget(self.mw.dl_ok_pill)
        status_row.addStretch()
        comp_v.addLayout(status_row)
        comp_v.addSpacing(16)

        file_card, fc_lay = self._card(margins=(16, 14, 16, 14), spacing=0)
        file_card.setObjectName("statTile")
        file_row = QHBoxLayout()
        file_row.setSpacing(14)
        self.mw.dl_complete_icon = QLabel()
        self.mw.dl_complete_icon.setObjectName("iconTile")
        self.mw.dl_complete_icon.setFixedSize(48, 48)
        self.mw.dl_complete_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        file_txt = QVBoxLayout()
        file_txt.setSpacing(6)
        self.mw.dl_complete_filename = QLabel("Video.mp4")
        self.mw.dl_complete_filename.setObjectName("sectionTitle")
        self.mw.dl_complete_filename.setMinimumWidth(120)
        pills = QHBoxLayout()
        pills.setSpacing(8)
        self.mw.dl_complete_fmt = QLabel("MP4")
        self.mw.dl_complete_fmt.setObjectName("pillAccent")
        self.mw.dl_complete_size = QLabel("-")
        self.mw.dl_complete_size.setObjectName("pill")
        pills.addWidget(self.mw.dl_complete_fmt)
        pills.addWidget(self.mw.dl_complete_size)
        pills.addStretch()
        file_txt.addWidget(self.mw.dl_complete_filename)
        file_txt.addLayout(pills)
        file_row.addWidget(self.mw.dl_complete_icon)
        file_row.addLayout(file_txt, 1)
        fc_lay.addLayout(file_row)
        comp_v.addWidget(file_card)
        comp_v.addSpacing(16)

        loc_lbl = QLabel("SAVED TO")
        loc_lbl.setObjectName("fieldLabel")
        self.mw.dl_complete_path = QLabel("-")
        self.mw.dl_complete_path.setObjectName("pathField")
        self.mw.dl_complete_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        comp_v.addWidget(loc_lbl)
        comp_v.addSpacing(6)
        comp_v.addWidget(self.mw.dl_complete_path)
        comp_v.addSpacing(22)

        btn_h_lay = QHBoxLayout()
        btn_h_lay.setSpacing(10)
        self.mw.dl_open_folder_btn = QPushButton(" Open Folder")
        self.mw.dl_open_folder_btn.setIcon(QIcon(create_vector_icon("folder", "#FFFFFF")))
        self.mw.dl_open_folder_btn.setObjectName("primaryButton")
        self.mw.dl_open_folder_btn.setMinimumHeight(44)
        self.mw.dl_open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.dl_open_folder_btn.clicked.connect(self.mw.downloader_mgr.open_download_folder)
        self.mw.dl_dl_again_btn = QPushButton("Do It Again")
        self.mw.dl_dl_again_btn.setObjectName("secondaryBtn")
        self.mw.dl_dl_again_btn.setMinimumHeight(44)
        self.mw.dl_dl_again_btn.setToolTip("Back to the same link with your current options")
        self.mw.dl_dl_again_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.dl_dl_again_btn.clicked.connect(lambda: self.mw.downloader_mgr.reset_ui(self.mw.dl_url_input.text()))
        self.mw.dl_back_dl_btn = QPushButton("Start Over")
        self.mw.dl_back_dl_btn.setObjectName("secondaryBtn")
        self.mw.dl_back_dl_btn.setMinimumHeight(44)
        self.mw.dl_back_dl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.dl_back_dl_btn.clicked.connect(lambda: self.mw.downloader_mgr.reset_ui(""))
        btn_h_lay.addWidget(self.mw.dl_open_folder_btn)
        btn_h_lay.addStretch()
        btn_h_lay.addWidget(self.mw.dl_dl_again_btn)
        btn_h_lay.addWidget(self.mw.dl_back_dl_btn)
        comp_v.addLayout(btn_h_lay)
        self.mw.dl_complete_container.hide()
        col.addWidget(self.mw.dl_complete_container)
        col.addStretch(1)
        self.mw.view_stack.addWidget(dl_widget)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def build_settings_screen(self):
        settings_widget = QWidget()
        settings_widget.setObjectName("screenContainer")
        lay = QVBoxLayout(settings_widget)
        lay.setContentsMargins(40, 32, 40, 40)

        content_lay = QHBoxLayout()
        content_lay.setSpacing(28)

        sidebar, sidebar_lay = self._card(margins=(14, 18, 14, 18), spacing=6)
        sidebar.setFixedWidth(230)
        title = QLabel("Settings")
        title.setObjectName("h2")
        title.setContentsMargins(8, 0, 0, 0)
        sidebar_lay.addWidget(title)
        sidebar_lay.addSpacing(10)

        self.mw.settings_sidebar_group = QButtonGroup(sidebar)
        # (the AI Provider tab was removed: the app always uses CReaper's own AI providers, configured on the server)
        tabs = [("Profile", "user", 0), ("Preferences", "gear", 1), ("Performance", "gauge", 4), ("Storage", "folder", 3),
                ("About", "info", 2)]
        accent = self.mw.settings_mgr.get_accent_hex()
        for name, icon_name, idx in tabs:
            btn = QPushButton(f"  {name}")
            btn.setObjectName("sidebarTab")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(create_multi_state_icon(icon_name, active_color=accent))
            btn.setIconSize(QSize(18, 18))
            if name == "Profile": self.mw.prof_tab_btn = btn
            elif name == "Preferences": self.mw.pref_tab_btn = btn
            elif name == "About": self.mw.about_tab_btn = btn
            elif name == "Storage": self.mw.storage_tab_btn = btn
            elif name == "Performance": self.mw.perf_tab_btn = btn
            self.mw.settings_sidebar_group.addButton(btn, idx)
            sidebar_lay.addWidget(btn)
            btn.clicked.connect(lambda checked, i=idx: self.mw.settings_mgr.switch_tab(i))
        sidebar_lay.addStretch()

        self.mw.settings_stack = QStackedWidget()
        self.mw.settings_stack.setStyleSheet("background: transparent;")
        self.build_profile_tab()
        self.build_preferences_tab()
        self.build_about_tab()
        self.build_storage_tab()                          # stack index 3
        self.build_performance_tab()                      # stack index 4

        content_lay.addWidget(sidebar, 0, Qt.AlignmentFlag.AlignTop)
        content_lay.addWidget(self.mw.settings_stack, 1)
        lay.addLayout(content_lay)
        self.mw.view_stack.addWidget(settings_widget)

    def _settings_tab(self, title: str, subtitle: str):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        t = QLabel(title)
        t.setObjectName("h1")
        s = QLabel(subtitle)
        s.setObjectName("pageSubtitle")
        lay.addWidget(t)
        lay.addSpacing(4)
        lay.addWidget(s)
        lay.addSpacing(20)
        return w, lay

    def build_profile_tab(self):
        prof_widget, prof_lay = self._settings_tab("Profile", "Your CReaper account, license and tokens.")
        card, c_lay = self._card(margins=(28, 26, 28, 28), spacing=0)

        # --- account (Discord)
        acct_row = QHBoxLayout()
        acct_txt = QVBoxLayout()
        acct_txt.setSpacing(2)
        lbl_acct = QLabel("ACCOUNT")
        lbl_acct.setObjectName("fieldLabel")
        self.mw.prof_account_val = QLabel("Not signed in")
        self.mw.prof_account_val.setObjectName("sectionTitle")
        self.mw.prof_account_sub = QLabel("")
        self.mw.prof_account_sub.setObjectName("sectionHint")
        acct_txt.addWidget(lbl_acct)
        acct_txt.addSpacing(4)
        acct_txt.addWidget(self.mw.prof_account_val)
        acct_txt.addWidget(self.mw.prof_account_sub)
        self.mw.prof_signout_btn = QPushButton("Sign out")
        self.mw.prof_signout_btn.setObjectName("secondaryBtn")
        self.mw.prof_signout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.prof_signout_btn.clicked.connect(self.mw.account_mgr.sign_out)
        acct_row.addLayout(acct_txt, 1)
        acct_row.addWidget(self.mw.prof_signout_btn, 0, Qt.AlignmentFlag.AlignTop)
        c_lay.addLayout(acct_row)
        c_lay.addSpacing(22)

        # --- license (display only: not editable, selectable or copyable; masked by the server)
        lbl_key = QLabel("LICENSE KEY")
        lbl_key.setObjectName("fieldLabel")
        key_container = QFrame()
        key_container.setObjectName("dataFieldContainer")
        key_lay = QHBoxLayout(key_container)
        key_lay.setContentsMargins(16, 10, 16, 10)
        self.mw.prof_key_val = QLabel("Not purchased")
        self.mw.prof_key_val.setObjectName("transparentCodeField")
        self.mw.prof_key_val.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.mw.prof_key_val.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.mw.prof_key_val.setAccessibleName("License key")
        key_lay.addWidget(self.mw.prof_key_val, 1)
        # kept (hidden) for the theme code; the license is no longer copyable
        self.mw.copy_key_btn = QPushButton()
        self.mw.copy_key_btn.setIcon(create_multi_state_icon("copy", active_color=self.mw.settings_mgr.get_accent_hex()))
        self.mw.copy_key_btn.hide()
        c_lay.addWidget(lbl_key)
        c_lay.addSpacing(8)
        c_lay.addWidget(key_container)

        # link an existing key (customers from before Discord sign-in); hidden once a license is linked
        self.mw.prof_link_box = QWidget()
        self.mw.prof_link_box.setProperty("cardContent", True)
        link_lay = QVBoxLayout(self.mw.prof_link_box)
        link_lay.setContentsMargins(0, 10, 0, 0)
        link_lay.setSpacing(6)
        link_row = QHBoxLayout()
        link_row.setSpacing(8)
        self.mw.prof_link_input = QLineEdit()
        self.mw.prof_link_input.setPlaceholderText("Already bought Premium? Enter your license key to link it")
        self.mw.prof_link_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.mw.prof_link_input.setMinimumHeight(38)
        self.mw.prof_link_btn = QPushButton("Link license")
        self.mw.prof_link_btn.setObjectName("secondaryBtn")
        self.mw.prof_link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.prof_link_btn.clicked.connect(self.mw.settings_mgr.link_license)
        self.mw.prof_link_input.returnPressed.connect(self.mw.settings_mgr.link_license)
        link_row.addWidget(self.mw.prof_link_input, 1)
        link_row.addWidget(self.mw.prof_link_btn)
        self.mw.prof_link_msg = QLabel("")
        self.mw.prof_link_msg.setObjectName("sectionHint")
        self.mw.prof_link_msg.setWordWrap(True)
        link_lay.addLayout(link_row)
        link_lay.addWidget(self.mw.prof_link_msg)
        c_lay.addWidget(self.mw.prof_link_box)
        c_lay.addSpacing(24)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        exp_card, exp_lay = self._card(margins=(18, 16, 18, 16), spacing=4)
        exp_card.setObjectName("statTile")
        lbl_exp = QLabel("EXPIRES")
        lbl_exp.setObjectName("fieldLabel")
        self.mw.prof_exp_date = QLabel("")
        self.mw.prof_exp_date.setObjectName("statValue")
        self.mw.prof_exp_date.setMinimumHeight(28)
        self.mw.prof_exp_time = QLabel("")
        self.mw.prof_exp_time.setStyleSheet("color: #A1A1AA; font-size: 13px; font-weight: 500;")
        self.mw.prof_exp_days = QLabel("")
        time_days_lay = QHBoxLayout()
        time_days_lay.setContentsMargins(0, 0, 0, 0)
        time_days_lay.addWidget(self.mw.prof_exp_time)
        time_days_lay.addSpacing(10)
        time_days_lay.addWidget(self.mw.prof_exp_days)
        time_days_lay.addStretch()
        exp_lay.addWidget(lbl_exp)
        exp_lay.addWidget(self.mw.prof_exp_date)
        exp_lay.addLayout(time_days_lay)

        stat_card, st_lay = self._card(margins=(18, 16, 18, 16), spacing=4)
        stat_card.setObjectName("statTile")
        lbl_stat = QLabel("STATUS")
        lbl_stat.setObjectName("fieldLabel")
        # status pill: tinted badge with a round dot (colours set in refresh_profile)
        self.mw.prof_stat_pill = QFrame()
        self.mw.prof_stat_pill.setObjectName("statusPill")
        self.mw.prof_stat_pill.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        pill_lay = QHBoxLayout(self.mw.prof_stat_pill)
        pill_lay.setContentsMargins(10, 4, 12, 4)
        pill_lay.setSpacing(8)
        self.mw.prof_stat_dot = QFrame()
        self.mw.prof_stat_dot.setObjectName("statusDot")
        self.mw.prof_stat_dot.setFixedSize(8, 8)
        self.mw.prof_stat_text = QLabel("")
        self.mw.prof_stat_text.setObjectName("statusPillText")
        pill_lay.addWidget(self.mw.prof_stat_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        pill_lay.addWidget(self.mw.prof_stat_text, 0, Qt.AlignmentFlag.AlignVCenter)
        pill_row = QHBoxLayout()
        pill_row.setContentsMargins(0, 2, 0, 2)
        pill_row.addWidget(self.mw.prof_stat_pill)
        pill_row.addStretch()
        self.mw.prof_stat_sub = QLabel("")
        self.mw.prof_stat_sub.setStyleSheet("color: #A1A1AA; font-size: 13px; font-weight: 500;")
        self.mw.prof_stat_sub.setWordWrap(True)
        st_lay.addWidget(lbl_stat)
        st_lay.addLayout(pill_row)
        st_lay.addWidget(self.mw.prof_stat_sub)
        st_lay.addStretch()

        tok_card, tk_lay = self._card(margins=(18, 16, 18, 16), spacing=4)
        tok_card.setObjectName("statTile")
        lbl_tok = QLabel("AVAILABLE TOKENS")
        lbl_tok.setObjectName("fieldLabel")
        self.mw.prof_tokens_val = QLabel("0")
        self.mw.prof_tokens_val.setObjectName("statValue")
        self.mw.prof_tokens_sub = QLabel("")
        self.mw.prof_tokens_sub.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        self.mw.prof_tokens_sub.setWordWrap(True)
        tk_lay.addWidget(lbl_tok)
        tk_lay.addWidget(self.mw.prof_tokens_val)
        tk_lay.addWidget(self.mw.prof_tokens_sub)
        tk_lay.addStretch()

        stats_row.addWidget(exp_card, 1)
        stats_row.addWidget(stat_card, 1)
        stats_row.addWidget(tok_card, 1)
        c_lay.addLayout(stats_row)
        c_lay.addSpacing(10)
        self.mw.prof_status_note = QLabel("")
        self.mw.prof_status_note.setObjectName("sectionHint")
        self.mw.prof_status_note.setWordWrap(True)
        c_lay.addWidget(self.mw.prof_status_note)
        c_lay.addSpacing(14)

        lbl_mach = QLabel("MACHINE ID")
        lbl_mach.setObjectName("fieldLabel")
        mach_container = QFrame()
        mach_container.setObjectName("dataFieldContainer")
        mach_lay = QHBoxLayout(mach_container)
        mach_lay.setContentsMargins(16, 4, 6, 4)
        self.mw.prof_mach_val = QLineEdit("...")
        self.mw.prof_mach_val.setReadOnly(True)
        self.mw.prof_mach_val.setEchoMode(QLineEdit.EchoMode.Password)
        self.mw.prof_mach_val.setObjectName("transparentCodeField")
        self.mw.mach_vis_btn = QPushButton()
        self.mw.mach_vis_btn.setIcon(create_multi_state_icon("eye", active_color=self.mw.settings_mgr.get_accent_hex()))
        self.mw.mach_vis_btn.setFixedSize(36, 36)
        self.mw.mach_vis_btn.setObjectName("fieldActionBtn")
        self.mw.mach_vis_btn.setToolTip("Show Machine ID")
        self.mw.mach_vis_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.mach_vis_btn.clicked.connect(self.mw.settings_mgr.toggle_machine_id)
        mach_lay.addWidget(self.mw.prof_mach_val)
        mach_lay.addWidget(self.mw.mach_vis_btn)
        c_lay.addWidget(lbl_mach)
        c_lay.addSpacing(8)
        c_lay.addWidget(mach_container)

        prof_lay.addWidget(card)
        prof_lay.addStretch()
        self.mw.settings_stack.addWidget(prof_widget)

    def build_performance_tab(self):
        """Settings > Performance (ui/components/performance_panel.py; enforced by utils/resources.py)."""
        from ui.components.performance_panel import PerformancePanel
        from ui.styles import theme_colors
        w, lay = self._settings_tab("Performance", "How much of your PC CReaper may use while it processes video.")
        self.mw.perf_panel = PerformancePanel(self.mw.settings, theme_colors(self.mw.settings.get_theme_color())["light"])
        lay.addWidget(self.mw.perf_panel)
        scroll = QScrollArea()                            # (taller than the other tabs on small windows)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QScrollArea > QWidget > QWidget { background: transparent; }")
        scroll.setWidget(w)
        self.mw.settings_stack.addWidget(scroll)

    def build_preferences_tab(self):
        pref_widget, pref_lay = self._settings_tab("Preferences", "Appearance and storage.")
        card, c_lay = self._card(margins=(28, 24, 28, 24), spacing=20)

        bg_enabled = self.mw.settings.get_animated_background()
        self.mw.bg_toggle = QPushButton("ON" if bg_enabled else "OFF")
        self.mw.bg_toggle.setCheckable(True)
        self.mw.bg_toggle.setChecked(bg_enabled)
        self.mw.bg_toggle.setObjectName("toggleCard")
        self.mw.bg_toggle.setFixedSize(80, 40)
        self.mw.bg_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.bg_toggle.toggled.connect(self.mw.settings_mgr.on_bg_toggled)
        self._setting_row(c_lay, "Moving Background", "Enable the subtle animated background effect.", self.mw.bg_toggle)
        self._divider(c_lay)

        hw_on = bool(self.mw.settings.get_value("preview_hw_decoding", False))
        self.mw.hw_decode_toggle = QPushButton("ON" if hw_on else "OFF")
        self.mw.hw_decode_toggle.setCheckable(True)
        self.mw.hw_decode_toggle.setChecked(hw_on)
        self.mw.hw_decode_toggle.setObjectName("toggleCard")
        self.mw.hw_decode_toggle.setFixedSize(80, 40)
        self.mw.hw_decode_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.hw_decode_toggle.toggled.connect(self.mw.settings_mgr.on_hw_decode_toggled)
        self._setting_row(c_lay, "Hardware Video Decoding",
                          "Use the graphics card to play previews (less CPU on 4K and high frame rate videos). "
                          "Turned off again by itself if your driver shows a broken picture. Applies after a restart.",
                          self.mw.hw_decode_toggle)
        self._divider(c_lay)

        self.mw.theme_combo = QComboBox()
        self.mw.theme_combo.setObjectName("themeCombo")
        self.mw.theme_combo.addItems(["Purple", "Blue", "Green", "Red"])
        self.mw.theme_combo.setFixedSize(150, 40)
        self.mw.theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        current_theme = self.mw.settings.get_theme_color().capitalize()
        index = self.mw.theme_combo.findText(current_theme)
        if index >= 0:
            self.mw.theme_combo.setCurrentIndex(index)
        self.mw.theme_combo.currentTextChanged.connect(self.mw.settings_mgr.on_theme_changed)
        self._setting_row(c_lay, "Theme Color", "Accent color used across the app.", self.mw.theme_combo)
        self._divider(c_lay)

        self.mw.retention_combo = QComboBox()
        self.mw.retention_combo.setObjectName("themeCombo")
        self.mw.retention_combo.addItems(["After 1 day", "After 3 days", "After 7 days", "After 1 month"])
        self.mw.retention_combo.setFixedSize(150, 40)
        self.mw.retention_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        current_ret_days = self.mw.settings.get_highlight_retention()
        ret_map_rev = {1: "After 1 day", 3: "After 3 days", 7: "After 7 days", 30: "After 1 month"}
        index = self.mw.retention_combo.findText(ret_map_rev.get(current_ret_days, "After 7 days"))
        if index >= 0:
            self.mw.retention_combo.setCurrentIndex(index)
        self.mw.retention_combo.currentTextChanged.connect(self.mw.settings_mgr.on_retention_changed)
        self._setting_row(c_lay, "Highlight Storage", "Automatically remove saved highlights after this period.", self.mw.retention_combo)

        pref_lay.addWidget(card)
        pref_lay.addStretch()
        self.mw.settings_stack.addWidget(pref_widget)

    def build_storage_tab(self):
        st_widget, st_lay = self._settings_tab("Storage", "See what CReaper keeps on this PC and free up space.")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(0, 0, 8, 0)
        b_lay.setSpacing(16)
        scroll.setWidget(body)
        self.mw.storage_scroll = scroll
        st_lay.addWidget(scroll, 1)

        # --- where CReaper is installed and keeps its data (any drive; changed by the launcher)
        loc, loc_lay = self._card(margins=(28, 24, 28, 24), spacing=10)
        loc_row = QHBoxLayout()
        loc_row.setSpacing(16)
        loc_txt = QVBoxLayout()
        loc_txt.setSpacing(2)
        loc_title = QLabel("Install location")
        loc_title.setObjectName("sectionTitle")
        self.mw.storage_location_lbl = QLabel("")
        self.mw.storage_location_lbl.setObjectName("sectionHint")
        self.mw.storage_location_lbl.setWordWrap(True)
        self.mw.storage_location_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        loc_txt.addWidget(loc_title)
        loc_txt.addWidget(self.mw.storage_location_lbl)
        self.mw.storage_location_btn = QPushButton("Change location...")
        self.mw.storage_location_btn.setObjectName("secondaryBtn")
        self.mw.storage_location_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.storage_location_btn.clicked.connect(self.mw.storage_mgr.change_install_location)
        loc_row.addLayout(loc_txt, 1)
        loc_row.addWidget(self.mw.storage_location_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        loc_lay.addLayout(loc_row)
        self.mw.storage_location_lbl.setText(self.mw.storage_mgr.install_location_text())
        b_lay.addWidget(loc)

        # --- overview + Clear Cache
        card, c_lay = self._card(margins=(28, 24, 28, 24), spacing=14)
        head = QHBoxLayout()
        head_txt = QVBoxLayout()
        head_txt.setSpacing(2)
        k = QLabel("CACHE")
        k.setObjectName("fieldLabel")
        self.mw.storage_total_lbl = QLabel("...")
        self.mw.storage_total_lbl.setObjectName("h1")
        head_txt.addWidget(k)
        head_txt.addWidget(self.mw.storage_total_lbl)
        self.mw.storage_refresh_btn = QPushButton("Refresh")
        self.mw.storage_refresh_btn.setObjectName("secondaryBtn")
        self.mw.storage_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.storage_refresh_btn.clicked.connect(self.mw.storage_mgr.refresh)
        head.addLayout(head_txt, 1)
        head.addWidget(self.mw.storage_refresh_btn, 0, Qt.AlignmentFlag.AlignTop)
        c_lay.addLayout(head)

        self.mw.storage_category_lbls = {}
        for key, title, hint in (
                ("temp", "Temporary processing files", "Leftover work files from trims, renders and downloads."),
                ("preview", "Preview images", "Frames used by the Auto Clipper preview."),
                ("transcripts", "Cached transcripts", "Transcripts of recently used videos."),
                ("music", "Background music cache", "Downloaded music tracks for Auto Clipper.")):
            val = QLabel("...")
            val.setObjectName("metaValue")
            val.setFixedWidth(80)                          # sizes change; the row layout doesn't
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._setting_row(c_lay, title, hint, val)
            self.mw.storage_category_lbls[key] = val
        self._divider(c_lay)
        note = QLabel("Clear Cache removes only these files; everything here is recreated when needed. "
                      "Not measured or touched: the installed app, your clips and videos, settings, license, "
                      "custom sounds and downloaded AI models (see below).")
        note.setObjectName("sectionHint")
        note.setWordWrap(True)
        c_lay.addWidget(note)
        act = QHBoxLayout()
        self.mw.storage_clear_btn = QPushButton(" Clear Cache")
        self.mw.storage_clear_btn.setObjectName("primaryButton")
        self.mw.storage_clear_btn.setMinimumHeight(44)
        self.mw.storage_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.storage_clear_btn.clicked.connect(self.mw.storage_mgr.clear_cache)
        # the settings stack's "background: transparent" would erase the button fill; keep the app's look
        self._theme_restyle(self.mw.storage_clear_btn, "primaryButton")
        act.addWidget(self.mw.storage_clear_btn)
        act.addStretch()
        c_lay.addLayout(act)
        self.mw.storage_status_lbl = QLabel("")
        self.mw.storage_status_lbl.setObjectName("sectionHint")
        self.mw.storage_status_lbl.setWordWrap(True)
        status_font = QFont(self.mw.storage_status_lbl.font())
        status_font.setPixelSize(13)
        self.mw.storage_status_lbl.setMinimumHeight(QFontMetrics(status_font).lineSpacing() * 2 + 2)
        self.mw.storage_status_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        c_lay.addWidget(self.mw.storage_status_lbl)
        b_lay.addWidget(card)

        # --- advanced: downloaded models and other large files, removed one by one
        adv, a_lay = self._card(margins=(28, 24, 28, 24), spacing=10)
        adv_head = QHBoxLayout()
        adv_t = QLabel("Advanced cleanup")
        adv_t.setObjectName("sectionTitle")
        self.mw.storage_models_total_lbl = QLabel("...")
        self.mw.storage_models_total_lbl.setObjectName("metaValue")
        adv_head.addWidget(adv_t, 1)
        adv_head.addWidget(self.mw.storage_models_total_lbl)
        a_lay.addLayout(adv_head)
        adv_hint = QLabel("Downloaded AI models and logs. Clear Cache never removes these. Removing a model may "
                          "mean it has to be downloaded again before the feature that uses it works.")
        adv_hint.setObjectName("sectionHint")
        adv_hint.setWordWrap(True)
        a_lay.addWidget(adv_hint)
        self._divider(a_lay)
        self.mw.storage_assets_lay = QVBoxLayout()
        self.mw.storage_assets_lay.setSpacing(4)
        a_lay.addLayout(self.mw.storage_assets_lay)
        b_lay.addWidget(adv)
        b_lay.addStretch()
        self.mw.settings_stack.addWidget(st_widget)

    def build_about_tab(self):
        about_widget, about_lay = self._settings_tab("About", "CReaper for creators.")
        card, c_lay = self._card(margins=(32, 36, 32, 36), spacing=8)

        logo = QLabel()
        png_path = get_asset_path("CRPR.png")
        ico_path = get_asset_path("CRPR.ico")
        pix = QPixmap()
        if os.path.exists(png_path):
            pix = QPixmap(png_path)
        elif os.path.exists(ico_path):
            pix = QIcon(ico_path).pixmap(QSize(256, 256))
        if not pix.isNull():
            logo.setPixmap(pix.scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        name = QLabel("CReaper")
        name.setObjectName("h1")
        sub = QLabel("Your AI moments finder.")
        sub.setObjectName("sectionHint")
        ver = QLabel(f"v{getattr(self.mw.settings, 'APP_VERSION', '3.2.0')}")
        ver.setObjectName("pill")
        desc = QLabel("CReaper is a simple, affordable clipping tool built for creators. Find the best moments with AI, "
                      "trim videos, and download MP3/MP4, all while keeping it as cheap as possible for small creators.")
        desc.setObjectName("sectionHint")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        credits = QLabel("Credits: @rxadrian in Discord")
        credits.setObjectName("sectionHint")
        links = QLabel("Discord: https://discord.gg/YRHNMAhDn8")
        links.setObjectName("sectionHint")
        links.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        c_lay.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)
        c_lay.addSpacing(6)
        c_lay.addWidget(name, alignment=Qt.AlignmentFlag.AlignCenter)
        c_lay.addWidget(sub, alignment=Qt.AlignmentFlag.AlignCenter)
        c_lay.addSpacing(6)
        c_lay.addWidget(ver, alignment=Qt.AlignmentFlag.AlignCenter)
        c_lay.addSpacing(18)
        c_lay.addWidget(desc)
        c_lay.addSpacing(14)
        self._divider(c_lay)
        c_lay.addSpacing(10)
        c_lay.addWidget(credits, alignment=Qt.AlignmentFlag.AlignCenter)
        c_lay.addWidget(links, alignment=Qt.AlignmentFlag.AlignCenter)

        about_lay.addWidget(card)
        about_lay.addStretch()
        self.mw.settings_stack.addWidget(about_widget)

    # ------------------------------------------------------------------
    # Highlighted clips
    # ------------------------------------------------------------------
    def build_highlights_screen(self):
        highlights_widget = QWidget()
        highlights_widget.setObjectName("screenContainer")
        outer = QVBoxLayout(highlights_widget)
        outer.setContentsMargins(40, 32, 40, 32)
        outer.setSpacing(0)

        head = QHBoxLayout()
        txt = QVBoxLayout()
        txt.setSpacing(4)
        title = QLabel("Highlighted Clips")
        title.setObjectName("h1")
        sub = QLabel("Moments you saved from AI Best Moments. Reopen the source or clean up old ones.")
        sub.setObjectName("pageSubtitle")
        sub.setWordWrap(True)
        txt.addWidget(title)
        txt.addWidget(sub)
        head.addLayout(txt, 1)
        outer.addLayout(head)
        outer.addSpacing(24)

        self.mw.highlights_status = QLabel("Loading highlights...")
        self.mw.highlights_status.setObjectName("emptyState")
        self.mw.highlights_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mw.highlights_status.setWordWrap(True)
        self.mw.highlights_status.setMinimumHeight(120)
        outer.addWidget(self.mw.highlights_status)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.mw.highlights_scroll_widget = QWidget()
        self.mw.highlights_cards_layout = QVBoxLayout(self.mw.highlights_scroll_widget)
        self.mw.highlights_cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.mw.highlights_cards_layout.setContentsMargins(0, 0, 12, 0)
        self.mw.highlights_cards_layout.setSpacing(16)
        scroll.setWidget(self.mw.highlights_scroll_widget)
        outer.addWidget(scroll, 1)
        self.mw.view_stack.addWidget(highlights_widget)

    # ------------------------------------------------------------------
    # AI Best Moments configuration
    # ------------------------------------------------------------------
    def build_ai_config_screen(self):
        ai_cfg_widget, col = self._scroll_page(max_width=980)
        self._page_header(col, "AI Best Moments", "Choose a target clip length, then let AI find the strongest moments.",
                          back=self._back_button("Change Video", self.mw.workflow_mgr.reset_to_home))

        # options (left) + summary / action (right), like the other workflows
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(20)
        left = QVBoxLayout()
        left.setSpacing(16)

        media_card, mc_lay = self._card(margins=(18, 18, 18, 18))
        m_lay = QHBoxLayout()
        m_lay.setSpacing(18)
        self.mw.ai_cfg_thumb_lbl = QLabel()
        self.mw.ai_cfg_thumb_lbl.setObjectName("thumbFrame")
        self.mw.ai_cfg_thumb_lbl.setFixedSize(192, 108)
        self.mw.ai_cfg_thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_lay = QVBoxLayout()
        info_lay.setSpacing(8)
        self.mw.ai_cfg_title_lbl = QLabel("Video Title")
        self.mw.ai_cfg_title_lbl.setObjectName("mediaTitle")
        self.mw.ai_cfg_title_lbl.setWordWrap(True)
        self.mw.ai_cfg_dur_lbl = QLabel("Duration: 00:00")
        self.mw.ai_cfg_dur_lbl.setObjectName("pill")
        dur_row = QHBoxLayout()
        dur_row.addWidget(self.mw.ai_cfg_dur_lbl)
        dur_row.addStretch()
        self.mw.ai_cfg_url_lbl = QLabel("")
        self.mw.ai_cfg_url_lbl.setObjectName("sectionHint")
        self.mw.ai_cfg_url_lbl.setWordWrap(True)
        info_lay.addWidget(self.mw.ai_cfg_title_lbl)
        info_lay.addLayout(dur_row)
        info_lay.addWidget(self.mw.ai_cfg_url_lbl)
        info_lay.addStretch()
        m_lay.addWidget(self.mw.ai_cfg_thumb_lbl)
        m_lay.addLayout(info_lay, 1)
        mc_lay.addLayout(m_lay)
        left.addWidget(media_card)

        cfg_card, cfg_lay = self._card(margins=(24, 22, 24, 24), spacing=16)
        self.mw.ai_duration_combo = QComboBox()
        self.mw.ai_duration_combo.setObjectName("themeCombo")
        # "Any" (default): each moment as long as it needs; the presets ask for a target length
        self.mw.ai_duration_combo.addItems(["Any", "15s", "20s", "30s", "60s"])
        self.mw.ai_duration_combo.setCurrentText("Any")
        self.mw.ai_duration_combo.setFixedSize(150, 40)
        self.mw.ai_duration_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setting_row(cfg_lay, "Clip Duration", "Any: each moment as long as it needs. Or pick a target length.",
                          self.mw.ai_duration_combo)
        # optional, OFF unless the user turns it on (remembered): hook + main body pairs, extra tokens
        related_on = bool(self.mw.settings.get_value("ai_related_moments", False))
        self.mw.ai_related_toggle = QPushButton("ON" if related_on else "OFF")
        self.mw.ai_related_toggle.setCheckable(True)
        self.mw.ai_related_toggle.setChecked(related_on)
        self.mw.ai_related_toggle.setObjectName("toggleCard")
        self.mw.ai_related_toggle.setFixedSize(80, 40)
        self.mw.ai_related_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.ai_related_toggle.setAccessibleName("Related Moments")
        self.mw.ai_related_toggle.toggled.connect(self.mw.workflow_mgr.on_related_toggled)
        self._setting_row(cfg_lay, "Related Moments",
                          "Find separate moments that work together as a hook and main story. Uses extra tokens.",
                          self.mw.ai_related_toggle)
        left.addWidget(cfg_card)
        left.addStretch()

        # Summary / action panel
        summary, s_lay = self._card(accent=True, margins=(24, 22, 24, 24), spacing=12)
        summary.setFixedWidth(300)
        s_title = QLabel("Analysis summary")
        s_title.setObjectName("sectionTitle")
        s_lay.addWidget(s_title)
        self.mw.ai_sum_length = QLabel("Any")
        self._summary_row(s_lay, "CLIP LENGTH", self.mw.ai_sum_length)
        self.mw.ai_duration_combo.currentTextChanged.connect(self.mw.ai_sum_length.setText)
        self.mw.ai_sum_related = QLabel("On" if related_on else "Off")
        self._summary_row(s_lay, "RELATED MOMENTS", self.mw.ai_sum_related)
        self._divider(s_lay)

        cost_row = QHBoxLayout()
        cost_key = QLabel("COST")
        cost_key.setObjectName("fieldLabel")
        self.mw.ai_cfg_cost_chip, self.mw.ai_cfg_cost_lbl = make_token_badge("...")
        self.mw.ai_cfg_cost_chip.setToolTip("Tokens this analysis uses for this video")
        cost_row.addWidget(cost_key)
        cost_row.addStretch()
        cost_row.addWidget(self.mw.ai_cfg_cost_chip)
        s_lay.addLayout(cost_row)

        bal_row = QHBoxLayout()
        bal_key = QLabel("YOUR BALANCE")
        bal_key.setObjectName("fieldLabel")
        self.mw.ai_cfg_balance_chip, self.mw.ai_cfg_balance_lbl = make_token_badge("...", object_name="tokenChipMuted")
        bal_row.addWidget(bal_key)
        bal_row.addStretch()
        bal_row.addWidget(self.mw.ai_cfg_balance_chip)
        s_lay.addLayout(bal_row)
        self.mw.ai_cfg_refill_lbl = QLabel("")
        self.mw.ai_cfg_refill_lbl.setObjectName("sectionHint")
        self.mw.ai_cfg_refill_lbl.setWordWrap(True)
        s_lay.addWidget(self.mw.ai_cfg_refill_lbl)
        self.mw.ai_cfg_cost_hint = QLabel("")
        self.mw.ai_cfg_cost_hint.setObjectName("sectionHint")
        self.mw.ai_cfg_cost_hint.setWordWrap(True)
        s_lay.addWidget(self.mw.ai_cfg_cost_hint)
        s_lay.addSpacing(8)

        self.mw.ai_start_find_btn = QPushButton(" Find Best Moments")
        self.mw.ai_start_find_btn.setIcon(QIcon(create_vector_icon("sparkle", "#FFFFFF")))
        self.mw.ai_start_find_btn.setObjectName("primaryButton")
        self.mw.ai_start_find_btn.setMinimumHeight(50)
        self.mw.ai_start_find_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.ai_start_find_btn.clicked.connect(self.mw.workflow_mgr.start_ai_moments_analysis)
        s_lay.addWidget(self.mw.ai_start_find_btn)
        eta = QLabel("Tokens are only used when the analysis runs.")
        eta.setObjectName("sectionHint")
        eta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eta.setWordWrap(True)
        s_lay.addWidget(eta)
        s_lay.addStretch()

        row.addLayout(left, 1)
        row.addWidget(summary, 0, Qt.AlignmentFlag.AlignTop)
        col.addLayout(row)
        col.addStretch(1)
        self.mw.view_stack.addWidget(ai_cfg_widget)

    def _clipper_step_card(self, number: int, title: str, hint: str, tag: str = ""):
        """Numbered workflow section card (tag: "Required" / "Optional" next to the title); returns
        (card, body_layout)."""
        card = QFrame()
        card.setObjectName("surfaceCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 20, 24, 22)
        lay.setSpacing(14)

        head = QHBoxLayout()
        head.setSpacing(12)
        badge = QLabel(str(number))
        badge.setObjectName("stepBadge")
        badge.setFixedSize(24, 24)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        t_row = QHBoxLayout()
        t_row.setSpacing(8)
        t = QLabel(title)
        t.setObjectName("sectionTitle")
        t_row.addWidget(t)
        if tag:
            tg = QLabel(tag)
            tg.setObjectName("requiredTag" if tag.lower() == "required" else "optionalTag")
            t_row.addWidget(tg, 0, Qt.AlignmentFlag.AlignVCenter)
        t_row.addStretch()
        h = QLabel(hint)
        h.setObjectName("sectionHint")
        h.setWordWrap(True)
        titles.addLayout(t_row)
        titles.addWidget(h)
        head.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        head.addLayout(titles, 1)
        lay.addLayout(head)
        return card, lay

    def build_clipper_screen(self):
        self.mw.clipper_widget = QWidget()
        self.mw.clipper_widget.setObjectName("screenContainer")
        outer = QVBoxLayout(self.mw.clipper_widget)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page = QWidget()
        page.setObjectName("screenContainer")
        scroll.setWidget(page)
        outer.addWidget(scroll)

        page_lay = QHBoxLayout(page)
        page_lay.setContentsMargins(40, 24, 40, 40)
        page_lay.addStretch()
        column = QWidget()
        column.setMaximumWidth(980)
        column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay = QVBoxLayout(column)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        page_lay.addWidget(column, 10)
        page_lay.addStretch()

        # --- Navigation + page header ---
        nav_lay = QHBoxLayout()
        self.mw.clipper_nav_back_btn = QPushButton(" Home")
        self.mw.clipper_nav_back_btn.setIcon(QIcon(create_vector_icon("home", "#FAFAFA")))
        self.mw.clipper_nav_back_btn.setObjectName("ghostBtn")
        self.mw.clipper_nav_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_nav_back_btn.clicked.connect(self.mw.workflow_mgr.reset_to_home)
        nav_lay.addWidget(self.mw.clipper_nav_back_btn)
        nav_lay.addStretch()
        lay.addLayout(nav_lay)
        lay.addSpacing(12)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title = QLabel("Auto Clipper")
        title.setObjectName("h1")
        beta_badge = QLabel("BETA")
        beta_badge.setObjectName("betaBadge")
        title_row.addWidget(title)
        title_row.addWidget(beta_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch()
        lay.addLayout(title_row)
        lay.addSpacing(4)
        subtitle = QLabel("Turn a long video into ready-to-post clips. Add a video, check the choices below, "
                          "then press Generate.")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        lay.addWidget(subtitle)
        lay.addSpacing(20)

        # =========================================================
        # INPUT STATE: the four questions (left) + summary / create (right)
        # =========================================================
        self.mw.clipper_input_container = QWidget()
        self.mw.clipper_input_container.setObjectName("screenContainer")
        in_row = QHBoxLayout(self.mw.clipper_input_container)
        in_row.setContentsMargins(0, 0, 0, 0)
        in_row.setSpacing(20)

        steps_col = QVBoxLayout()
        steps_col.setSpacing(12)
        accent = self.mw.settings_mgr.get_accent_hex() if hasattr(self.mw, "settings_mgr") else "#A855F7"

        def chip(text, tip=""):
            b = QPushButton(text)
            b.setObjectName("chipBtn")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumHeight(34)
            if tip:
                b.setToolTip(tip)
            return b

        def field_label(text):
            lbl = QLabel(text)
            lbl.setObjectName("fieldLabel")
            return lbl

        # Step 1: the video (required)
        src_card, src_lay = self._clipper_step_card(1, "Add your video", "Paste a link, or choose a video file on this PC.",
                                                    tag="Required")
        url_row = QHBoxLayout()
        url_row.setSpacing(10)
        self.mw.clipper_url_input = QLineEdit()
        self.mw.clipper_url_input.setPlaceholderText("Paste a video link (YouTube, TikTok, Instagram, Facebook, Twitch...)")
        self.mw.clipper_url_input.setMinimumHeight(44)
        self.mw.clipper_url_input.setAccessibleName("Video link or file")
        self.mw.clipper_url_input.addAction(QIcon(create_vector_icon("link", "#71717A")), QLineEdit.ActionPosition.LeadingPosition)
        self.mw.clipper_url_input.returnPressed.connect(self.mw.clipper_mgr.fetch_metadata)
        self.mw.clipper_url_input.textChanged.connect(self.mw.clipper_mgr.on_url_text_changed)
        url_row.addWidget(self.mw.clipper_url_input, 1)
        or_lbl = QLabel("or")
        or_lbl.setObjectName("sectionHint")
        url_row.addWidget(or_lbl)
        self.mw.clipper_browse_btn = QPushButton(" Choose file")
        self.mw.clipper_browse_btn.setIcon(QIcon(create_vector_icon("folder", "#D4D4D8")))
        self.mw.clipper_browse_btn.setObjectName("secondaryBtn")
        self.mw.clipper_browse_btn.setMinimumHeight(44)
        self.mw.clipper_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_browse_btn.setToolTip("Choose a video file on this PC (MP4, MKV, MOV, AVI, WEBM...)")
        self.mw.clipper_browse_btn.clicked.connect(self.mw.clipper_mgr.browse_local)
        url_row.addWidget(self.mw.clipper_browse_btn)
        src_lay.addLayout(url_row)
        self.mw.clipper_local_note = QLabel(
            "Local files stay on your PC. Their speech is transcribed on this PC when the speech model is "
            "installed; otherwise only the audio is sent to CReaper's transcription service. The AI judges small "
            "still frames and the transcript, never the full video.")
        self.mw.clipper_local_note.setObjectName("sectionHint")
        self.mw.clipper_local_note.setWordWrap(True)
        self.mw.clipper_local_note.hide()
        src_lay.addWidget(self.mw.clipper_local_note)

        self.mw.clipper_meta_empty = QLabel("No video yet. Its title and length appear here once it loads.")
        self.mw.clipper_meta_empty.setObjectName("emptyState")
        self.mw.clipper_meta_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mw.clipper_meta_empty.setWordWrap(True)
        src_lay.addWidget(self.mw.clipper_meta_empty)

        self.mw.clipper_meta_widget = QWidget()
        self.mw.clipper_meta_widget.setProperty("cardContent", True)
        meta_lay = QHBoxLayout(self.mw.clipper_meta_widget)
        meta_lay.setContentsMargins(0, 0, 0, 0)
        meta_lay.setSpacing(14)
        self.mw.clipper_thumb_lbl = QLabel("No image")
        self.mw.clipper_thumb_lbl.setObjectName("thumbFrame")
        self.mw.clipper_thumb_lbl.setFixedSize(128, 72)
        self.mw.clipper_thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meta_info_lay = QVBoxLayout()
        meta_info_lay.setSpacing(6)
        self.mw.clipper_meta_title = QLabel("-")
        self.mw.clipper_meta_title.setObjectName("sectionTitle")
        self.mw.clipper_meta_title.setWordWrap(True)
        meta_pills = QHBoxLayout()
        meta_pills.setSpacing(8)
        self.mw.clipper_meta_creator = QLabel("-")
        self.mw.clipper_meta_creator.setObjectName("pill")
        self.mw.clipper_meta_duration = QLabel("-")
        self.mw.clipper_meta_duration.setObjectName("pill")
        meta_pills.addWidget(self.mw.clipper_meta_creator)
        meta_pills.addWidget(self.mw.clipper_meta_duration)
        meta_pills.addStretch()
        meta_info_lay.addWidget(self.mw.clipper_meta_title)
        meta_info_lay.addLayout(meta_pills)
        meta_info_lay.addStretch()
        meta_lay.addWidget(self.mw.clipper_thumb_lbl, 0, Qt.AlignmentFlag.AlignTop)
        meta_lay.addLayout(meta_info_lay, 1)
        self.mw.clipper_meta_widget.hide()
        src_lay.addWidget(self.mw.clipper_meta_widget)
        steps_col.addWidget(src_card)

        # Step 2: what kind of video (Auto detect by default; the type steers which moments the AI picks)
        from ui.main_window_clipper import CONTENT_TYPES
        type_card, type_lay = self._clipper_step_card(
            2, "What kind of video is it?", "Auto detect works it out for you. Pick a type if you know it.",
            tag="Optional")
        type_row = QGridLayout()
        type_row.setHorizontalSpacing(8)
        type_row.setVerticalSpacing(8)
        self.mw.clipper_type_group = QButtonGroup(self.mw.clipper_widget)
        self.mw.clipper_type_group.setExclusive(True)
        self.mw.clipper_type_btns = {}
        for i, (key, label, _hint) in enumerate(CONTENT_TYPES):
            b = chip(label)
            b.setProperty("typeKey", key)
            self.mw.clipper_type_group.addButton(b, i)
            self.mw.clipper_type_btns[key] = b
            type_row.addWidget(b, i // 4, i % 4)
        self.mw.clipper_type_btns["auto"].setChecked(True)
        self.mw.clipper_type_group.idClicked.connect(self.mw.clipper_mgr.on_content_type_changed)
        type_lay.addLayout(type_row)
        self.mw.clipper_type_hint = QLabel("")
        self.mw.clipper_type_hint.setObjectName("sectionHint")
        self.mw.clipper_type_hint.setWordWrap(True)
        type_lay.addWidget(self.mw.clipper_type_hint)
        steps_col.addWidget(type_card)

        # Step 3: the shape of the finished video
        from services.output_format import ASPECTS, INFO as ASPECT_INFO
        from ui.components.aspect_tile import AspectTile
        shape_card, shape_lay = self._clipper_step_card(3, "Shape", "How the finished video is framed.")
        shape_row = QHBoxLayout()
        shape_row.setSpacing(8)
        self.mw.clipper_aspect_group = QButtonGroup(self.mw.clipper_widget)
        self.mw.clipper_aspect_group.setExclusive(True)
        self.mw.clipper_aspect_btns = {}
        for i, key in enumerate(ASPECTS):
            title_txt, sub, use = ASPECT_INFO[key]
            tile = AspectTile(key, title_txt, sub, accent)
            tile.setToolTip(use)
            self.mw.clipper_aspect_group.addButton(tile, i)
            self.mw.clipper_aspect_btns[key] = tile
            shape_row.addWidget(tile)
        self.mw.clipper_aspect_group.idClicked.connect(self.mw.clipper_mgr.on_aspect_changed)
        shape_lay.addLayout(shape_row)
        # how the footage fills the shape: crop around the subject (default) or the whole video + background.
        # Each option shows a small picture of what it does (ui/components/framing_tile.py); saved values stay
        # "fill" / "fit".
        from ui.components.framing_tile import FramingTile, FRAMING_OPTIONS
        shape_lay.addWidget(field_label("HOW THE VIDEO FITS"))
        fr_row = QHBoxLayout()
        fr_row.setSpacing(8)
        self.mw.clipper_framing_group = QButtonGroup(self.mw.clipper_widget)
        self.mw.clipper_framing_group.setExclusive(True)
        self.mw.clipper_framing_btns = {}
        for i, (key, text, desc) in enumerate(FRAMING_OPTIONS):
            b = FramingTile(key, text, desc, accent)
            self.mw.clipper_framing_group.addButton(b, i)
            self.mw.clipper_framing_btns[key] = b
            fr_row.addWidget(b, 1)
        self.mw.clipper_framing_btns["fill"].setChecked(True)
        self.mw.clipper_framing_group.idClicked.connect(self.mw.clipper_mgr.on_framing_changed)
        shape_lay.addLayout(fr_row)
        self.mw.clipper_aspect_hint = QLabel("")
        self.mw.clipper_aspect_hint.setObjectName("sectionHint")
        self.mw.clipper_aspect_hint.setWordWrap(True)
        shape_lay.addWidget(self.mw.clipper_aspect_hint)
        steps_col.addWidget(shape_card)

        # Step 4: how long, and how many
        len_card, len_lay = self._clipper_step_card(4, "Length", "How long each video is, and how many to make.")
        len_lay.addWidget(field_label("LENGTH OF EACH VIDEO"))
        len_row = QHBoxLayout()
        len_row.setSpacing(8)
        from PyQt6.QtWidgets import QSpinBox
        self.mw.clipper_length_group = QButtonGroup(self.mw.clipper_widget)
        self.mw.clipper_length_group.setExclusive(True)
        self.mw.clipper_length_btns = {}
        from ui.main_window_clipper import LENGTH_PRESETS
        for i, (key, label) in enumerate(LENGTH_PRESETS):
            b = chip(label)
            self.mw.clipper_length_group.addButton(b, i)
            self.mw.clipper_length_btns[key] = b
            len_row.addWidget(b)
        self.mw.clipper_length_btns["auto"].setChecked(True)
        self.mw.clipper_length_spin = QSpinBox()
        self.mw.clipper_length_spin.setObjectName("compactSpin")
        self.mw.clipper_length_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.mw.clipper_length_spin.setRange(10, 180)
        self.mw.clipper_length_spin.setValue(45)
        self.mw.clipper_length_spin.setSuffix(" s")
        self.mw.clipper_length_spin.setMinimumHeight(34)
        self.mw.clipper_length_spin.setFixedWidth(84)
        self.mw.clipper_length_spin.setAccessibleName("Custom length in seconds")
        self.mw.clipper_length_spin.setToolTip("Any length from 10 to 180 seconds")
        self.mw.clipper_length_spin.setEnabled(False)
        len_row.addWidget(self.mw.clipper_length_spin)
        len_row.addStretch()
        self.mw.clipper_length_group.idClicked.connect(self.mw.clipper_mgr.on_length_changed)
        self.mw.clipper_length_spin.valueChanged.connect(lambda _v: self.mw.clipper_mgr.on_length_changed())
        len_lay.addLayout(len_row)
        self.mw.clipper_length_hint = QLabel("")
        self.mw.clipper_length_hint.setObjectName("sectionHint")
        self.mw.clipper_length_hint.setWordWrap(True)
        len_lay.addWidget(self.mw.clipper_length_hint)

        # ---- Number of clips (one AI analysis; only distinct, strong moments come back)
        len_lay.addSpacing(4)
        len_lay.addWidget(field_label("NUMBER OF VIDEOS"))
        count_row = QHBoxLayout()
        count_row.setSpacing(8)
        self.mw.clipper_count_group = QButtonGroup(self.mw.clipper_widget)
        self.mw.clipper_count_group.setExclusive(True)
        self.mw.clipper_count_btns = {}
        for n in (1, 3, 5, 10, 20):
            b = chip(str(n))
            b.setMinimumWidth(44)
            self.mw.clipper_count_group.addButton(b, n)
            self.mw.clipper_count_btns[n] = b
            count_row.addWidget(b)
        custom_lbl = QLabel("Custom")
        custom_lbl.setObjectName("sectionHint")
        self.mw.clipper_count_spin = QSpinBox()
        self.mw.clipper_count_spin.setObjectName("compactSpin")
        self.mw.clipper_count_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.mw.clipper_count_spin.setRange(1, 20)
        self.mw.clipper_count_spin.setMinimumHeight(34)
        self.mw.clipper_count_spin.setFixedWidth(70)
        self.mw.clipper_count_spin.setToolTip("Any number from 1 to 20")
        self.mw.clipper_count_spin.setAccessibleName("Number of videos")
        count_row.addSpacing(4)
        count_row.addWidget(custom_lbl)
        count_row.addWidget(self.mw.clipper_count_spin)
        count_row.addStretch()
        len_lay.addLayout(count_row)
        self.mw.clipper_count_group.idClicked.connect(self.mw.clipper_mgr.on_clip_count_changed)
        self.mw.clipper_count_spin.valueChanged.connect(self.mw.clipper_mgr.on_clip_count_changed)
        self.mw.clipper_count_hint = QLabel("")
        self.mw.clipper_count_hint.setObjectName("sectionHint")
        self.mw.clipper_count_hint.setWordWrap(True)
        len_lay.addWidget(self.mw.clipper_count_hint)
        steps_col.addWidget(len_card)

        # Step 5: how the captions look (style, font, size, colours, word highlight), shown in the preview and
        # used by every clip made (ui/components/caption_style_ui.py; the clip editor has the same panel)
        cap_card, cap_lay = self._clipper_step_card(5, "Captions", "Style, font and colours. The preview shows them.")
        from ui.components.caption_style_ui import CaptionLookPanel
        self.mw.clipper_caption_panel = CaptionLookPanel(size_in_look=True, columns=4)
        self.mw.clipper_caption_panel.changed.connect(self.mw.clipper_mgr.on_caption_look_changed)
        cap_lay.addWidget(self.mw.clipper_caption_panel)
        steps_col.addWidget(cap_card)

        # =========================================================
        # MORE OPTIONS (closed by default): everything that already has a good default
        # =========================================================
        adv_card = QFrame()
        adv_card.setObjectName("surfaceCard")
        adv_outer = QVBoxLayout(adv_card)
        adv_outer.setContentsMargins(0, 0, 0, 0)
        adv_outer.setSpacing(0)
        self.mw.clipper_advanced_toggle = QPushButton()
        self.mw.clipper_advanced_toggle.setObjectName("disclosureBtn")
        self.mw.clipper_advanced_toggle.setCheckable(True)
        self.mw.clipper_advanced_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_advanced_toggle.setMinimumHeight(60)
        self.mw.clipper_advanced_toggle.setAccessibleName("More options")
        tog_lay = QHBoxLayout(self.mw.clipper_advanced_toggle)
        tog_lay.setContentsMargins(24, 10, 20, 10)
        tog_lay.setSpacing(12)
        tog_txt = QVBoxLayout()
        tog_txt.setSpacing(1)
        tog_t = QLabel("More options")
        tog_t.setObjectName("sectionTitle")
        self.mw.clipper_advanced_summary = QLabel("Sound, headline, what to look for, time ranges, background, look")
        self.mw.clipper_advanced_summary.setObjectName("sectionHint")
        for w in (tog_t, self.mw.clipper_advanced_summary):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            tog_txt.addWidget(w)
        self.mw.clipper_advanced_chevron = QLabel()
        self.mw.clipper_advanced_chevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.mw.clipper_advanced_chevron.setPixmap(create_vector_icon("chevron-down", "#A1A1AA").scaled(
            16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        tog_lay.addLayout(tog_txt, 1)
        tog_lay.addWidget(self.mw.clipper_advanced_chevron)
        adv_outer.addWidget(self.mw.clipper_advanced_toggle)

        self.mw.clipper_advanced_body = QWidget()
        self.mw.clipper_advanced_body.setProperty("cardContent", True)
        opt_lay = QVBoxLayout(self.mw.clipper_advanced_body)
        opt_lay.setContentsMargins(24, 4, 24, 22)
        opt_lay.setSpacing(12)
        self.mw.clipper_advanced_body.hide()
        self.mw.clipper_advanced_toggle.toggled.connect(self.mw.clipper_mgr.set_advanced_open)
        adv_outer.addWidget(self.mw.clipper_advanced_body)

        # ---- Editing options
        opt_lay.addWidget(field_label("ADDED TO EACH VIDEO"))
        opt_grid = QGridLayout()
        opt_grid.setHorizontalSpacing(10)
        opt_grid.setVerticalSpacing(8)
        check_icon = os.path.join(_ui_cache_dir(), "check_white.png")
        if not os.path.exists(check_icon):
            create_vector_icon("check", "#FFFFFF").save(check_icon)
        check_css = "QCheckBox::indicator:checked { image: url(%s); }" % check_icon.replace("\\", "/")
        self.mw.clipper_option_checks = {}
        for i, (key, label, tip) in enumerate([
                ("captions", "Captions", "Word-by-word captions synced to the speech."),
                ("sound_effects", "Sound effects", "Adds a fitting sound effect only when a moment calls for it."),
                ("background_music", "Background music", "Soft music under the speech, faded out at the end."),
                ("hook", "Hook headline", "A short attention-grabbing headline at the top of the video.")]):
            cb = OptionCard(label)
            cb.setObjectName("optionCheck")
            cb.setToolTip(tip)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setMinimumHeight(40)
            cb.setStyleSheet(check_css)
            cb.toggled.connect(self.mw.clipper_mgr.on_option_toggled)
            self.mw.clipper_option_checks[key] = cb
            opt_grid.addWidget(cb, i // 2, i % 2)
        opt_lay.addLayout(opt_grid)
        more_row = QHBoxLayout()
        more_row.setSpacing(10)
        more_lbl = QLabel("Your own sound effects")
        more_lbl.setObjectName("sectionHint")
        self.mw.clipper_add_more_btn = QPushButton(" Add sounds")
        self.mw.clipper_add_more_btn.setIcon(QIcon(create_vector_icon("plus", "#D4D4D8")))
        self.mw.clipper_add_more_btn.setObjectName("secondaryBtn")
        self.mw.clipper_add_more_btn.setMinimumHeight(32)
        self.mw.clipper_add_more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_add_more_btn.clicked.connect(self.mw.clipper_mgr.toggle_custom_sounds)
        more_row.addWidget(more_lbl)
        more_row.addStretch()
        more_row.addWidget(self.mw.clipper_add_more_btn)
        opt_lay.addLayout(more_row)
        from ui.custom_sounds import CustomSoundsPanel
        self.mw.clipper_sounds_panel = CustomSoundsPanel()
        self.mw.clipper_sounds_panel.hide()
        opt_lay.addWidget(self.mw.clipper_sounds_panel)
        self._divider(opt_lay)

        # ---- What to look for (optional): the user's own request, the primary selection goal when given
        from utils.time_ranges import CUSTOM_PROMPT_MAX, MAX_RANGES
        prompt_head = QHBoxLayout()
        prompt_head.addWidget(field_label("WHAT SHOULD IT LOOK FOR?"))
        prompt_head.addStretch()
        self.mw.clipper_prompt_count = QLabel(f"0/{CUSTOM_PROMPT_MAX}")
        self.mw.clipper_prompt_count.setObjectName("sectionHint")
        prompt_head.addWidget(self.mw.clipper_prompt_count)
        opt_lay.addLayout(prompt_head)
        self.mw.clipper_prompt_input = QLineEdit()
        self.mw.clipper_prompt_input.setMaxLength(CUSTOM_PROMPT_MAX)
        self.mw.clipper_prompt_input.setMinimumHeight(38)
        self.mw.clipper_prompt_input.setPlaceholderText("e.g. Find the funniest reactions")
        self.mw.clipper_prompt_input.setAccessibleName("What should it look for")
        self.mw.clipper_prompt_input.setToolTip(
            f"Optional, up to {CUSTOM_PROMPT_MAX} characters. When filled in, Auto Clipper picks the moments that "
            "match it first. Leave it empty for the usual automatic choice.")
        self.mw.clipper_prompt_input.textChanged.connect(self.mw.clipper_mgr.on_prompt_changed)
        opt_lay.addWidget(self.mw.clipper_prompt_input)

        # ---- Where to look (optional): time ranges of the video to search
        ranges_head = QHBoxLayout()
        ranges_head.addWidget(field_label("ONLY SEARCH THESE PARTS"))
        ranges_head.addStretch()
        self.mw.clipper_add_range_btn = QPushButton("+ Add time range")
        self.mw.clipper_add_range_btn.setObjectName("secondaryBtn")
        self.mw.clipper_add_range_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_add_range_btn.setMinimumHeight(30)
        self.mw.clipper_add_range_btn.clicked.connect(lambda: self.mw.clipper_mgr.add_range_row())
        ranges_head.addWidget(self.mw.clipper_add_range_btn)
        opt_lay.addLayout(ranges_head)
        self.mw.clipper_ranges_box = QVBoxLayout()
        self.mw.clipper_ranges_box.setSpacing(6)
        opt_lay.addLayout(self.mw.clipper_ranges_box)
        self.mw.clipper_range_rows = []
        self.mw.clipper_ranges_hint = QLabel(
            f"For example 00:02:00 to 00:05:00. Up to {MAX_RANGES} ranges. Leave empty to search the whole video.")
        self.mw.clipper_ranges_hint.setObjectName("sectionHint")
        self.mw.clipper_ranges_hint.setWordWrap(True)
        opt_lay.addWidget(self.mw.clipper_ranges_hint)
        self._divider(opt_lay)

        # ---- Where it's posted (tunes pacing and the hook; platforms still in development are not offered)
        plat_row = QHBoxLayout()
        plat_row.setSpacing(8)
        plat_row.addWidget(field_label("POSTING TO"))
        plat_row.addSpacing(6)

        def plat_btn(text, enabled=True):
            b = chip(text)
            b.setCheckable(enabled)
            b.setDisabled(not enabled)
            b.setVisible(enabled)                    # coming-soon platforms are not shown as buttons
            return b

        self.mw.clipper_platform_youtube = plat_btn("YouTube Shorts")
        self.mw.clipper_platform_youtube.setChecked(True)
        self.mw.clipper_platform_whop = plat_btn("Whop", enabled=False)
        self.mw.clipper_platform_ig = plat_btn("Instagram", enabled=False)
        self.mw.clipper_platform_tiktok = plat_btn("TikTok", enabled=False)
        plat_btn_grp = QButtonGroup(self.mw.clipper_widget)
        plat_btn_grp.setExclusive(True)
        for b in (self.mw.clipper_platform_youtube, self.mw.clipper_platform_whop,
                  self.mw.clipper_platform_ig, self.mw.clipper_platform_tiktok):
            plat_btn_grp.addButton(b)
            plat_row.addWidget(b)
        self.mw.clipper_platform_youtube.toggled.connect(self.mw.clipper_mgr.on_platform_changed)
        self.mw.clipper_platform_whop.toggled.connect(self.mw.clipper_mgr.on_platform_changed)
        soon = QLabel("More platforms soon")
        soon.setObjectName("sectionHint")
        plat_row.addWidget(soon)
        plat_row.addStretch()
        opt_lay.addLayout(plat_row)

        self.mw.clipper_campaign_widget = QFrame()
        self.mw.clipper_campaign_widget.setObjectName("surfaceCardAccent")
        camp_lay = QVBoxLayout(self.mw.clipper_campaign_widget)
        camp_lay.setContentsMargins(16, 14, 16, 14)
        camp_lay.setSpacing(8)
        camp_lay.addWidget(field_label("WHOP CAMPAIGN REQUIREMENTS"))
        camp_h_lay = QHBoxLayout()
        self.mw.clipper_camp_file_lbl = QLabel("No document uploaded.")
        self.mw.clipper_camp_file_lbl.setStyleSheet("color: #A1A1AA;")
        self.mw.clipper_camp_file_lbl.setWordWrap(True)
        self.mw.clipper_camp_upload_btn = QPushButton("Upload PDF / DOCX")
        self.mw.clipper_camp_upload_btn.setObjectName("secondaryBtn")
        self.mw.clipper_camp_upload_btn.setMinimumHeight(36)
        self.mw.clipper_camp_upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_camp_upload_btn.clicked.connect(self.mw.clipper_mgr.upload_campaign_doc)
        camp_h_lay.addWidget(self.mw.clipper_camp_file_lbl, 1)
        camp_h_lay.addWidget(self.mw.clipper_camp_upload_btn)
        camp_lay.addLayout(camp_h_lay)
        self.mw.clipper_campaign_widget.hide()
        opt_lay.addWidget(self.mw.clipper_campaign_widget)
        self._divider(opt_lay)

        # ---- Background (what fills the frame around the picture)
        bg_row = QHBoxLayout()
        bg_row.setSpacing(10)
        from services.backgrounds import MODES as BG_MODES, MODE_LABELS as BG_LABELS
        self.mw.clipper_bg_combo = QComboBox()
        self.mw.clipper_bg_combo.setObjectName("themeCombo")
        self.mw.clipper_bg_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_bg_combo.setAccessibleName("Background")
        for mode in BG_MODES:
            self.mw.clipper_bg_combo.addItem(BG_LABELS[mode], mode)
        self.mw.clipper_bg_combo.currentIndexChanged.connect(self.mw.clipper_mgr.on_background_changed)
        bg_row.addWidget(field_label("BACKGROUND"))
        bg_row.addWidget(self.mw.clipper_bg_combo, 1)
        opt_lay.addLayout(bg_row)
        self.mw.clipper_bg_hint = QLabel("")
        self.mw.clipper_bg_hint.setObjectName("sectionHint")
        self.mw.clipper_bg_hint.setWordWrap(True)
        opt_lay.addWidget(self.mw.clipper_bg_hint)

        # ---- Look: live still preview (real frame, final layout) + visual adjustments
        look = QHBoxLayout()
        look.setSpacing(16)
        prev_col = QVBoxLayout()
        prev_col.setSpacing(6)
        self.mw.clipper_preview_lbl = QLabel("Add a video to see a preview")
        self.mw.clipper_preview_lbl.setObjectName("previewFrame")
        self.mw.clipper_preview_lbl.setFixedSize(162, 288)
        self.mw.clipper_preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mw.clipper_preview_lbl.setWordWrap(True)
        # The note (sample text / transcript hints) changes with Captions / Hook. It lives on its own
        # full-width line under the row with a FIXED two-line height: inside the row, its varying
        # height used to stretch the row and spread the slider rows apart.
        self.mw.clipper_preview_note = QLabel("")
        self.mw.clipper_preview_note.setObjectName("sectionHint")
        self.mw.clipper_preview_note.setWordWrap(True)
        self.mw.clipper_preview_note.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        note_font = QFont(self.mw.clipper_preview_note.font())
        note_font.setPixelSize(13)                      # QLabel#sectionHint font size (styles.py)
        self.mw.clipper_preview_note.setFixedHeight(QFontMetrics(note_font).lineSpacing() * 2 + 2)
        self.mw.clipper_preview_note.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        prev_col.addWidget(self.mw.clipper_preview_lbl)
        prev_col.addStretch()
        look.addLayout(prev_col)

        sliders = QGridLayout()
        sliders.setHorizontalSpacing(10)
        sliders.setVerticalSpacing(14)
        self.mw.clipper_look_reset = QPushButton("Reset")
        self.mw.clipper_look_reset.setObjectName("secondaryBtn")
        self.mw.clipper_look_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_look_reset.clicked.connect(self.mw.clipper_mgr.reset_visual)
        sliders.addWidget(field_label("LOOK"), 0, 0)
        sliders.addWidget(self.mw.clipper_look_reset, 0, 2, Qt.AlignmentFlag.AlignRight)
        from services.visual_adjust import RANGES
        self.mw.clipper_visual_sliders = {}
        self.mw.clipper_visual_values = {}
        for row, (key, label, tip) in enumerate([
                ("temperature", "Temperature", "Left: cooler (blue). Right: warmer (orange)."),
                ("brightness", "Brightness", "Overall lightness."),
                ("contrast", "Contrast", "Difference between light and dark areas."),
                ("saturation", "Saturation", "Colour intensity."),
                ("sharpness", "Sharpness", "Crisper detail (kept moderate to avoid halos)."),
                ("vignette", "Vignette", "Darker edges around the picture.")], start=1):
            name = QLabel(label)
            name.setToolTip(tip)
            sl = TrackSlider(Qt.Orientation.Horizontal)
            sl.setRange(*RANGES[key])
            sl.setValue(0)
            sl.setSingleStep(1)
            sl.setPageStep(10)
            sl.setToolTip(tip)
            sl.setCursor(Qt.CursorShape.PointingHandCursor)
            sl.setAccessibleName(label)
            val = QLabel("0")
            val.setObjectName("sectionHint")
            val.setFixedWidth(64)
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            sl.valueChanged.connect(lambda v, k=key: self.mw.clipper_mgr.on_visual_changed(k, v))
            sliders.addWidget(name, row, 0)
            sliders.addWidget(sl, row, 1)
            sliders.addWidget(val, row, 2)
            self.mw.clipper_visual_sliders[key] = sl
            self.mw.clipper_visual_values[key] = val
        sliders.setColumnStretch(1, 1)
        sliders.setRowStretch(row + 1, 1)               # spare height goes below the sliders, not between them
        look.addLayout(sliders, 1)
        opt_lay.addLayout(look)
        opt_lay.addWidget(self.mw.clipper_preview_note)
        steps_col.addWidget(adv_card)
        steps_col.addStretch()

        # =========================================================
        # Summary / create panel: what will be made, what it costs, one primary action
        # =========================================================
        summary = QFrame()
        summary.setObjectName("surfaceCard")
        summary.setFixedWidth(300)
        s_lay = QVBoxLayout(summary)
        s_lay.setContentsMargins(22, 20, 22, 22)
        s_lay.setSpacing(10)
        s_title = QLabel("Your clips")
        s_title.setObjectName("sectionTitle")
        s_lay.addWidget(s_title)

        def sum_row(key):
            row = QHBoxLayout()
            row.setSpacing(8)
            k = QLabel(key)
            k.setObjectName("summaryKey")
            v = QLabel("-")
            v.setObjectName("summaryValue")
            v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            v.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            row.addWidget(k)
            row.addWidget(v, 1)
            s_lay.addLayout(row)
            return v

        self.mw.clipper_sum_video = sum_row("Video")
        self.mw.clipper_sum_type = sum_row("Kind")
        self.mw.clipper_sum_shape = sum_row("Shape")
        self.mw.clipper_sum_length = sum_row("Length")
        self.mw.clipper_sum_count = sum_row("Videos")
        self._divider(s_lay)

        cost_row = QHBoxLayout()
        cost_lbl = QLabel("Cost")
        cost_lbl.setObjectName("summaryKey")
        self.mw.clipper_cost_chip, self.mw.clipper_cost_lbl = make_token_badge("Paste a link")
        self.mw.clipper_cost_chip.setToolTip("Tokens required for this video")
        cost_row.addWidget(cost_lbl)
        cost_row.addStretch()
        cost_row.addWidget(self.mw.clipper_cost_chip)
        s_lay.addLayout(cost_row)

        bal_row = QHBoxLayout()
        bal_lbl = QLabel("Your balance")
        bal_lbl.setObjectName("summaryKey")
        self.mw.clipper_balance_chip, self.mw.clipper_balance_lbl = make_token_badge("...", object_name="tokenChipMuted")
        bal_row.addWidget(bal_lbl)
        bal_row.addStretch()
        bal_row.addWidget(self.mw.clipper_balance_chip)
        s_lay.addLayout(bal_row)
        # Plain-language refill info, e.g. "Premium plan · refills to 2,300 in 2d 5h" (allowance comes from the server)
        self.mw.clipper_refill_lbl = QLabel("")
        self.mw.clipper_refill_lbl.setObjectName("sectionHint")
        self.mw.clipper_refill_lbl.setWordWrap(True)
        s_lay.addWidget(self.mw.clipper_refill_lbl)
        s_lay.addSpacing(6)

        self.mw.clipper_start_btn = QPushButton(" Generate Clip")
        self.mw.clipper_start_btn.setIcon(QIcon(create_vector_icon("sparkle", "#FFFFFF")))
        self.mw.clipper_start_btn.setObjectName("primaryButton")
        self.mw.clipper_start_btn.setMinimumHeight(48)
        self.mw.clipper_start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_start_btn.clicked.connect(self.mw.clipper_mgr.start_clipper)
        s_lay.addWidget(self.mw.clipper_start_btn)
        # why Create is unavailable ("Add a video first"), or what happens next
        self.mw.clipper_start_hint = QLabel("Runs on your PC. Usually takes a few minutes.")
        self.mw.clipper_start_hint.setObjectName("sectionHint")
        self.mw.clipper_start_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mw.clipper_start_hint.setWordWrap(True)
        s_lay.addWidget(self.mw.clipper_start_hint)
        self._divider(s_lay)

        # Step "where": the output folder (the finished MP4s are saved here)
        f_head = QHBoxLayout()
        f_key = QLabel("Saved to")
        f_key.setObjectName("summaryKey")
        f_btn = QPushButton("Change")
        f_btn.setObjectName("linkBtn")
        f_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        f_btn.clicked.connect(self.mw.clipper_mgr.change_folder)
        f_head.addWidget(f_key)
        f_head.addStretch()
        f_head.addWidget(f_btn)
        s_lay.addLayout(f_head)
        self.mw.clipper_f_lbl = QLabel("...")
        self.mw.clipper_f_lbl.setObjectName("pathField")
        self.mw.clipper_f_lbl.setMinimumWidth(80)
        s_lay.addWidget(self.mw.clipper_f_lbl)
        s_lay.addStretch()

        in_row.addLayout(steps_col, 1)
        in_row.addWidget(summary, 0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(self.mw.clipper_input_container)

        # =========================================================
        # PROCESSING STATE
        # =========================================================
        self.mw.clipper_progress_container = QFrame()
        self.mw.clipper_progress_container.setObjectName("surfaceCard")
        p_lay = QVBoxLayout(self.mw.clipper_progress_container)
        p_lay.setContentsMargins(32, 32, 32, 32)
        p_lay.setSpacing(0)
        p_lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # a simple shimmering tile with the estimated time left ("3m"), steady and counting down
        from ui.components.processing_stage import ProcessingStage, GlowProgressBar
        self.mw.clipper_prog_thumb = ProcessingStage()

        self.mw.clipper_prog_title = QLabel("Editing your video...")
        self.mw.clipper_prog_title.setObjectName("h2")
        self.mw.clipper_prog_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mw.clipper_prog_info = QLabel("Preparing...")
        self.mw.clipper_prog_info.setObjectName("sectionHint")
        self.mw.clipper_prog_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mw.clipper_prog_info.setWordWrap(True)
        # as wide as the bar and room for two lines: a long step name used to wrap into a narrow, clipped box
        self.mw.clipper_prog_info.setFixedWidth(520)
        self.mw.clipper_prog_info.setMinimumHeight(self.mw.clipper_prog_info.fontMetrics().lineSpacing() * 2 + 4)

        self.mw.clipper_prog = GlowProgressBar()
        self.mw.clipper_prog.setObjectName("bigProgress")
        self.mw.clipper_prog.setFixedHeight(10)
        self.mw.clipper_prog.setFixedWidth(520)

        stages_row = QHBoxLayout()
        stages_row.setSpacing(8)
        self.mw.clipper_stage_labels = []
        for name in ("Finding moments", "Downloading", "Framing", "Captions & sound", "Final render"):
            st = QLabel(name)
            st.setObjectName("stageLabel")
            st.setAlignment(Qt.AlignmentFlag.AlignCenter)
            st.setProperty("state", "pending")
            self.mw.clipper_stage_labels.append(st)
            stages_row.addWidget(st)

        self.mw.clipper_cancel_btn = QPushButton(" Cancel")
        self.mw.clipper_cancel_btn.setIcon(QIcon(create_vector_icon("x", "#FCA5A5")))
        self.mw.clipper_cancel_btn.setObjectName("dangerGhostBtn")
        self.mw.clipper_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_cancel_btn.clicked.connect(self.mw.clipper_mgr.cancel_clipper)

        p_lay.addWidget(self.mw.clipper_prog_thumb, alignment=Qt.AlignmentFlag.AlignCenter)
        p_lay.addSpacing(24)
        p_lay.addWidget(self.mw.clipper_prog_title, alignment=Qt.AlignmentFlag.AlignCenter)
        p_lay.addSpacing(6)
        p_lay.addWidget(self.mw.clipper_prog_info, alignment=Qt.AlignmentFlag.AlignCenter)
        p_lay.addSpacing(20)
        p_lay.addWidget(self.mw.clipper_prog, alignment=Qt.AlignmentFlag.AlignCenter)
        p_lay.addSpacing(16)
        p_lay.addLayout(stages_row)
        p_lay.addSpacing(24)
        p_lay.addWidget(self.mw.clipper_cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.mw.clipper_progress_container)

        # =========================================================
        # RESULT STATE: finished-export screen
        # =========================================================
        self.mw.clipper_complete_container = QFrame()
        self.mw.clipper_complete_container.setObjectName("surfaceCard")
        self.mw.clipper_complete_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        cmp_row = QHBoxLayout(self.mw.clipper_complete_container)
        cmp_row.setContentsMargins(24, 24, 28, 24)
        cmp_row.setSpacing(28)

        # Left: 9:16 preview (a real frame of the rendered clip) with a play overlay
        preview_col = QVBoxLayout()
        preview_col.setSpacing(10)
        preview_holder = QWidget()
        preview_holder.setProperty("cardContent", True)
        preview_holder.setFixedSize(216, 384)
        self.mw.clipper_result_thumb = QLabel("Preview\nunavailable", preview_holder)
        self.mw.clipper_result_thumb.setObjectName("previewFrame")
        self.mw.clipper_result_thumb.setGeometry(0, 0, 216, 384)
        self.mw.clipper_result_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mw.clipper_play_overlay = QPushButton(preview_holder)
        self.mw.clipper_play_overlay.setObjectName("playOverlay")
        self.mw.clipper_play_overlay.setFixedSize(56, 56)
        self.mw.clipper_play_overlay.move((216 - 56) // 2, (384 - 56) // 2)
        self.mw.clipper_play_overlay.setIcon(QIcon(create_vector_icon("play", "#FFFFFF")))
        self.mw.clipper_play_overlay.setIconSize(QSize(24, 24))
        self.mw.clipper_play_overlay.setToolTip("Play clip")
        self.mw.clipper_play_overlay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_play_overlay.clicked.connect(self.mw.clipper_mgr.preview_clip)
        preview_col.addWidget(preview_holder)
        self.mw.clipper_complete_filename = QLabel("clip.mp4")
        self.mw.clipper_complete_filename.setObjectName("sectionHint")
        self.mw.clipper_complete_filename.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mw.clipper_complete_filename.setFixedWidth(216)
        preview_col.addWidget(self.mw.clipper_complete_filename)
        preview_col.addStretch()
        cmp_row.addLayout(preview_col)

        # Right: status, title, details, location, actions
        info = QVBoxLayout()
        info.setSpacing(0)
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        ok_icon = QLabel()
        ok_icon.setPixmap(create_vector_icon("check-circle", "#10B981").scaled(
            20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        ok_pill = QLabel("EXPORT COMPLETE")
        ok_pill.setObjectName("successPill")
        status_row.addWidget(ok_icon)
        status_row.addWidget(ok_pill)
        status_row.addStretch()
        info.addLayout(status_row)
        info.addSpacing(14)

        self.mw.clipper_result_title = QLabel("Best Moment")
        self.mw.clipper_result_title.setObjectName("h1")
        self.mw.clipper_result_title.setWordWrap(True)
        info.addWidget(self.mw.clipper_result_title)
        info.addSpacing(16)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        def meta_cell(key):
            cell = QFrame()
            cell.setObjectName("metaCell")
            c_lay = QVBoxLayout(cell)
            c_lay.setContentsMargins(12, 9, 12, 10)
            c_lay.setSpacing(2)
            k = QLabel(key)
            k.setObjectName("metaKey")
            v = QLabel("-")
            v.setObjectName("metaValue")
            c_lay.addWidget(k)
            c_lay.addWidget(v)
            return cell, v

        cells = []
        for key in ("DURATION", "ASPECT RATIO", "RESOLUTION", "FILE SIZE", "PLATFORM", "AI SCORE"):
            cells.append(meta_cell(key))
        (c_dur, self.mw.clipper_result_dur), (c_ar, self.mw.clipper_result_aspect), \
            (c_res, self.mw.clipper_result_res), (c_size, self.mw.clipper_result_size), \
            (c_plat, self.mw.clipper_result_platform), (c_score, self.mw.clipper_result_score) = cells
        for i, (cell, _) in enumerate(cells):
            grid.addWidget(cell, i // 3, i % 3)
        info.addLayout(grid)
        info.addSpacing(16)

        why_lbl = QLabel("WHY THIS MOMENT")
        why_lbl.setObjectName("fieldLabel")
        self.mw.clipper_result_reason = QLabel("")
        self.mw.clipper_result_reason.setObjectName("sectionHint")
        self.mw.clipper_result_reason.setWordWrap(True)
        info.addWidget(why_lbl)
        info.addSpacing(6)
        info.addWidget(self.mw.clipper_result_reason)
        info.addSpacing(16)

        loc_lbl = QLabel("SAVED TO")
        loc_lbl.setObjectName("fieldLabel")
        self.mw.clipper_complete_path = QLabel("-")
        self.mw.clipper_complete_path.setObjectName("pathField")
        self.mw.clipper_complete_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info.addWidget(loc_lbl)
        info.addSpacing(6)
        info.addWidget(self.mw.clipper_complete_path)
        info.addSpacing(20)
        info.addStretch()

        btns_lay = QHBoxLayout()
        btns_lay.setSpacing(10)
        self.mw.clipper_preview_btn = QPushButton(" Play Clip")
        self.mw.clipper_preview_btn.setIcon(QIcon(create_vector_icon("play", "#FFFFFF")))
        self.mw.clipper_preview_btn.setObjectName("primaryButton")
        self.mw.clipper_preview_btn.setMinimumHeight(44)
        self.mw.clipper_preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_preview_btn.clicked.connect(self.mw.clipper_mgr.preview_clip)
        self.mw.clipper_open_folder_btn = QPushButton(" Open Folder")
        self.mw.clipper_open_folder_btn.setIcon(QIcon(create_vector_icon("folder", "#D4D4D8")))
        self.mw.clipper_open_folder_btn.setObjectName("secondaryBtn")
        self.mw.clipper_open_folder_btn.setMinimumHeight(44)
        self.mw.clipper_open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_open_folder_btn.clicked.connect(self.mw.clipper_mgr.open_output_folder)
        self.mw.clipper_back_btn = QPushButton(" Create Another")
        self.mw.clipper_back_btn.setIcon(QIcon(create_vector_icon("sparkle", "#D4D4D8")))
        self.mw.clipper_back_btn.setObjectName("secondaryBtn")
        self.mw.clipper_back_btn.setMinimumHeight(44)
        self.mw.clipper_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_back_btn.clicked.connect(lambda: self.mw.clipper_mgr.reset_ui())
        self.mw.clipper_edit_btn = QPushButton(" Edit Clip")
        self.mw.clipper_edit_btn.setIcon(QIcon(create_vector_icon("scissors", "#D4D4D8")))
        self.mw.clipper_edit_btn.setObjectName("secondaryBtn")
        self.mw.clipper_edit_btn.setMinimumHeight(44)
        self.mw.clipper_edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw.clipper_edit_btn.setToolTip("Open this clip in the timeline editor (the original file is kept)")
        self.mw.clipper_edit_btn.clicked.connect(self.mw.clipper_mgr.edit_current_clip)
        btns_lay.addWidget(self.mw.clipper_preview_btn)
        btns_lay.addWidget(self.mw.clipper_edit_btn)
        btns_lay.addWidget(self.mw.clipper_open_folder_btn)
        btns_lay.addStretch()
        btns_lay.addWidget(self.mw.clipper_back_btn)
        info.addLayout(btns_lay)
        cmp_row.addLayout(info, 1)

        # Several clips: one entry per clip (rank, AI score, headline); the card below shows the selected one
        self.mw.clipper_results_strip = QFrame()
        self.mw.clipper_results_strip.setObjectName("surfaceCard")
        strip_lay = QVBoxLayout(self.mw.clipper_results_strip)
        strip_lay.setContentsMargins(20, 16, 20, 16)
        strip_lay.setSpacing(10)
        self.mw.clipper_results_title = QLabel("YOUR CLIPS")
        self.mw.clipper_results_title.setObjectName("fieldLabel")
        strip_lay.addWidget(self.mw.clipper_results_title)
        self.mw.clipper_results_notice = QLabel("")
        self.mw.clipper_results_notice.setObjectName("sectionHint")
        self.mw.clipper_results_notice.setWordWrap(True)
        strip_lay.addWidget(self.mw.clipper_results_notice)
        results_scroll = QScrollArea()
        results_scroll.setWidgetResizable(True)
        results_scroll.setFixedHeight(64)
        results_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        results_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        results_body = QWidget()
        results_body.setStyleSheet("background: transparent;")
        self.mw.clipper_results_row = QHBoxLayout(results_body)
        self.mw.clipper_results_row.setContentsMargins(0, 0, 0, 0)
        self.mw.clipper_results_row.setSpacing(8)
        self.mw.clipper_results_row.addStretch()
        results_scroll.setWidget(results_body)
        strip_lay.addWidget(results_scroll)
        self.mw.clipper_results_group = QButtonGroup(self.mw.clipper_results_strip)
        self.mw.clipper_results_group.setExclusive(True)
        self.mw.clipper_results_group.idClicked.connect(self.mw.clipper_mgr.show_result_index)
        self.mw.clipper_results_strip.hide()
        lay.addWidget(self.mw.clipper_results_strip)
        lay.addSpacing(12)
        lay.addWidget(self.mw.clipper_complete_container)
        lay.addStretch(1)
        self.mw.clipper_progress_container.hide()
        self.mw.clipper_complete_container.hide()
        self.mw.view_stack.addWidget(self.mw.clipper_widget)
