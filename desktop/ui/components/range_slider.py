from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen

class RangeSlider(QWidget):
    rangeChanged = pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(64) # Taller for a modern NLE timeline feel
        self.min_val = 0
        self.max_val = 100
        self.start_val = 0
        self.end_val = 100
        
        self.handle_width = 12
        self.handle_height = 40
        self.groove_height = 40
        self.active_handle = None

    def setMaximum(self, value):
        self.max_val = max(1, value)
        self.end_val = self.max_val
        self.start_val = 0
        self.update()

    def setRangeValues(self, start, end):
        self.start_val = max(self.min_val, min(start, self.max_val - 1))
        self.end_val = max(self.start_val + 1, min(end, self.max_val))
        self.update()

    def _val_to_x(self, val):
        width = self.width() - (2 * self.handle_width)
        if self.max_val == self.min_val: return self.handle_width
        return self.handle_width + int(((val - self.min_val) / (self.max_val - self.min_val)) * width)

    def _x_to_val(self, x):
        width = self.width() - (2 * self.handle_width)
        ratio = min(max(x - self.handle_width, 0), width) / width
        return self.min_val + int(ratio * (self.max_val - self.min_val))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        y_center = self.height() // 2
        gh = self.groove_height
        hw = self.handle_width
        hh = self.handle_height
        
        # 1. Draw inactive background track (dark)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#09090B"))) # Deep background
        bg_rect = QRectF(hw, y_center - gh//2, self.width() - 2*hw, gh)
        painter.drawRoundedRect(bg_rect, 6, 6)
        
        x1 = self._val_to_x(self.start_val)
        x2 = self._val_to_x(self.end_val)
        
        # 2. Draw active track (accent colored fill)
        active_rect = QRectF(x1, y_center - gh//2, x2 - x1, gh)
        painter.setBrush(QBrush(QColor(59, 130, 246, 70))) # 3B82F6 with alpha
        painter.setPen(QPen(QColor("#3B82F6"), 2))
        painter.drawRoundedRect(active_rect, 4, 4)
        
        # 3. Draw NLE handles
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#FAFAFA")))
        
        # Left Handle
        left_handle = QRectF(x1 - hw, y_center - hh//2, hw, hh)
        painter.drawRoundedRect(left_handle, 4, 4)
        
        # Right Handle
        right_handle = QRectF(x2, y_center - hh//2, hw, hh)
        painter.drawRoundedRect(right_handle, 4, 4)
        
        # Add subtle grip lines to handles
        painter.setPen(QPen(QColor("#52525B"), 1))
        painter.drawLine(int(x1 - hw/2), int(y_center - 6), int(x1 - hw/2), int(y_center + 6))
        painter.drawLine(int(x2 + hw/2), int(y_center - 6), int(x2 + hw/2), int(y_center + 6))

    def mousePressEvent(self, event):
        x = event.pos().x()
        x1 = self._val_to_x(self.start_val)
        x2 = self._val_to_x(self.end_val)
        
        dist1 = abs(x - x1)
        dist2 = abs(x - x2)
        
        if dist1 < dist2 and dist1 < 24:
            self.active_handle = 'start'
        elif dist2 < 24:
            self.active_handle = 'end'

    def mouseMoveEvent(self, event):
        if not self.active_handle: return
        nv = self._x_to_val(event.pos().x())
        if self.active_handle == 'start':
            self.start_val = min(nv, self.end_val - 1)
        else:
            self.end_val = max(nv, self.start_val + 1)
            
        self.update()
        self.rangeChanged.emit(self.start_val, self.end_val)

    def mouseReleaseEvent(self, event):
        self.active_handle = None