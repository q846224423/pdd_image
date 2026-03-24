"""
ui/widgets.py — PyQt6 可复用组件
"""
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QCursor
from PIL import Image
import io


class HoverPreview(QLabel):
    """鼠标悬停大图预览浮窗"""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet("""
            QLabel {
                background: #111111;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self._timer   = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._do_show)
        self._pil_img = None
        self._pos     = None
        self.hide()

    def trigger(self, pil_img, global_pos):
        self._pil_img = pil_img
        self._pos     = global_pos
        self._timer.start(250)

    def _do_show(self):
        if self._pil_img is None:
            return
        preview = self._pil_img.copy()
        preview.thumbnail((480, 480), Image.LANCZOS)
        photo = pil_to_pixmap(preview)
        self.setPixmap(photo)
        self.adjustSize()

        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = self._pos.x() + 16
        y = self._pos.y() + 16
        if x + self.width()  > screen.right():  x = self._pos.x() - self.width()  - 16
        if y + self.height() > screen.bottom(): y = self._pos.y() - self.height() - 16
        self.move(x, y)
        self.show()

    def hide_preview(self):
        self._timer.stop()
        self.hide()
        self._pil_img = None


class ClickableLabel(QLabel):
    """可点击的 QLabel"""
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


def pil_to_pixmap(pil_img: Image.Image) -> QPixmap:
    """PIL Image → QPixmap"""
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    qimg = QImage.fromData(buf.read())
    return QPixmap.fromImage(qimg)
