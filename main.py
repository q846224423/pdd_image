"""
main.py — 程序入口
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon, QPixmap, QImage, QPalette, QColor
from PyQt6.QtCore import Qt
from ui.app import MainWindow
from ui.styles import QSS, C


def load_icon():
    base = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base, "logo.png")
    if not os.path.exists(logo_path):
        return QIcon()
    try:
        from PIL import Image, ImageDraw
        import io
        img = Image.open(logo_path).convert("RGBA").resize((256, 256), Image.LANCZOS)
        mask = Image.new("L", (256, 256), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 255, 255), fill=255)
        result = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        result.paste(img, mask=mask)
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        buf.seek(0)
        qimg = QImage.fromData(buf.read())
        return QIcon(QPixmap.fromImage(qimg))
    except Exception:
        return QIcon(logo_path)


def build_palette():
    """强制暗黑调色板"""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(C["bg_app"]))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(C["text_primary"]))
    p.setColor(QPalette.ColorRole.Base,            QColor(C["bg_secondary"]))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(C["bg_tertiary"]))
    p.setColor(QPalette.ColorRole.Text,            QColor(C["text_primary"]))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(C["text_primary"]))
    p.setColor(QPalette.ColorRole.Button,          QColor(C["bg_secondary"]))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(C["text_primary"]))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(C["accent"]))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.Link,            QColor(C["blue"]))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(C["text_muted"]))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(C["bg_secondary"]))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(C["text_primary"]))
    p.setColor(QPalette.ColorRole.Mid,             QColor(C["border"]))
    p.setColor(QPalette.ColorRole.Dark,            QColor(C["bg_tertiary"]))
    p.setColor(QPalette.ColorRole.Shadow,          QColor("#000000"))
    return p


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setPalette(build_palette())
    app.setStyleSheet(QSS)
    app.setFont(QFont(C["font"], 10))
    app.setApplicationName("选品图片抓取器")

    icon = load_icon()
    app.setWindowIcon(icon)

    win = MainWindow()
    win.setWindowIcon(icon)
    win.show()
    sys.exit(app.exec())
