"""
ui/styles.py — PyQt6 暗黑主题
"""

C = {
    "font":           "Microsoft YaHei UI",
    "bg_app":         "#16171A",
    "bg_primary":     "#1E1F23",
    "bg_secondary":   "#26272C",
    "bg_tertiary":    "#2E2F35",
    "bg_hover":       "#33343B",
    "bg_input":       "#26272C",
    "border":         "#3A3B42",
    "border_hover":   "#4A4B52",
    "text_primary":   "#F0F0F2",
    "text_secondary": "#9A9BA8",
    "text_muted":     "#5A5B65",
    "accent":         "#E8192C",
    "accent_dark":    "#C41525",
    "accent_light":   "#3D0A10",
    "green":          "#07C160",
    "green_dark":     "#06AD56",
    "green_light":    "#0A2E1A",
    "blue":           "#4A8FD4",
    "blue_light":     "#0D2340",
    "sidebar_w":      52,
}

QSS = """
QWidget {
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
    color: #F0F0F2;
    background-color: #16171A;
}
QMainWindow, QDialog {
    background: #16171A;
}
QToolTip {
    background: #26272C;
    color: #F0F0F2;
    border: 1px solid #3A3B42;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
}

/* ── 侧边栏 ── */
QFrame#sidebar {
    background: #1E1F23;
    border-right: 1px solid #3A3B42;
}
QPushButton#sb_btn {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 0;
    font-size: 18px;
    color: #5A5B65;
}
QPushButton#sb_btn:hover {
    background: #2E2F35;
    color: #9A9BA8;
}
QPushButton#sb_btn_active {
    background: #3D0A10;
    border: none;
    border-radius: 8px;
    padding: 0;
    font-size: 18px;
    color: #E8192C;
}

/* ── 顶栏 ── */
QFrame#topbar {
    background: #1E1F23;
    border-bottom: 1px solid #3A3B42;
}
QLabel#title_lbl {
    font-size: 15px;
    font-weight: bold;
    color: #F0F0F2;
    background: transparent;
}
QLabel#sub_lbl {
    font-size: 11px;
    color: #3A3B42;
    background: transparent;
}
QLabel#status_pill {
    font-size: 11px;
    font-weight: bold;
    color: #07C160;
    background: #0A2E1A;
    border-radius: 12px;
    padding: 3px 10px;
}
QLabel#status_pill_busy {
    font-size: 11px;
    font-weight: bold;
    color: #4A8FD4;
    background: #0D2340;
    border-radius: 12px;
    padding: 3px 10px;
}

/* ── 搜索栏 ── */
QFrame#searchbar {
    background: #1E1F23;
    border-bottom: 1px solid #3A3B42;
}
QLabel#field_lbl {
    font-size: 10px;
    font-weight: bold;
    color: #5A5B65;
    background: transparent;
    letter-spacing: 0.3px;
}

/* ── 输入框 ── */
QLineEdit {
    background: #26272C;
    border: 1px solid #3A3B42;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
    color: #F0F0F2;
    selection-background-color: #E8192C;
}
QLineEdit:hover { border-color: #4A4B52; }
QLineEdit:focus {
    border: 1.5px solid #E8192C;
    background: #2E2F35;
}
QLineEdit:read-only {
    color: #5A5B65;
    background: #26272C;
    border: 1px solid #3A3B42;
}
QLineEdit#path_entry {
    background: #26272C;
    border: 1px solid #3A3B42;
    border-radius: 7px;
    padding: 5px 10px;
    font-size: 11px;
    color: #5A5B65;
}

/* ── 按钮 ── */
QPushButton {
    background: #26272C;
    border: 1px solid #3A3B42;
    border-radius: 7px;
    padding: 5px 14px;
    font-size: 12px;
    color: #9A9BA8;
    font-family: "Microsoft YaHei UI";
}
QPushButton:hover {
    background: #2E2F35;
    border-color: #4A4B52;
    color: #F0F0F2;
}
QPushButton:pressed { background: #33343B; }
QPushButton:disabled { color: #3A3B42; background: #1E1F23; }

/* ── 主按钮（红）── */
QPushButton#btn_primary {
    background: #E8192C;
    border: none;
    color: #FFFFFF;
    font-weight: bold;
    padding: 8px 22px;
    border-radius: 8px;
    font-size: 13px;
}
QPushButton#btn_primary:hover { background: #C41525; }
QPushButton#btn_primary:pressed { background: #A8101E; }
QPushButton#btn_primary:disabled { background: #5A0A12; color: #9A5060; }

/* ── 下载按钮（绿）── */
QPushButton#btn_download {
    background: #07C160;
    border: none;
    color: #FFFFFF;
    font-weight: bold;
    padding: 8px 24px;
    border-radius: 8px;
    font-size: 13px;
}
QPushButton#btn_download:hover { background: #06AD56; }
QPushButton#btn_download:pressed { background: #059A4C; }
QPushButton#btn_download:disabled { background: #0A3020; color: #2A6040; }

/* ── 危险按钮 ── */
QPushButton#btn_danger {
    color: #E8192C;
    background: transparent;
    border: 1px solid #3A3B42;
}
QPushButton#btn_danger:hover {
    background: #3D0A10;
    border-color: #E8192C;
}

/* ── 蓝色按钮 ── */
QPushButton#btn_link {
    color: #4A8FD4;
    background: transparent;
    border: 1px solid #3A3B42;
}
QPushButton#btn_link:hover {
    background: #0D2340;
    border-color: #4A8FD4;
}

/* ── 筛选按钮 ── */
QPushButton#btn_filter {
    background: #E8192C;
    border: none;
    color: #FFFFFF;
    font-weight: bold;
    padding: 4px 14px;
    border-radius: 6px;
    font-size: 12px;
}
QPushButton#btn_filter:hover { background: #C41525; }

/* ── 筛选栏 ── */
QFrame#filterbar {
    background: #1A1B1F;
    border-bottom: 1px solid #3A3B42;
}

/* ── 底部 ── */
QFrame#footer {
    background: #1E1F23;
    border-top: 1px solid #3A3B42;
}

/* ── 卡片 ── */
QFrame#card {
    background: #1E1F23;
    border: 1px solid #3A3B42;
    border-radius: 12px;
}
QFrame#card_selected {
    background: #1E1F23;
    border: 2px solid #E8192C;
    border-radius: 12px;
}
QFrame#card_downloaded {
    background: #19191D;
    border: 1px solid #2A2B30;
    border-radius: 12px;
}

/* ── 卡片内标签 ── */
QLabel#card_title {
    font-size: 13px;
    font-weight: bold;
    color: #F0F0F2;
    background: transparent;
}
QLabel#card_title_dim {
    font-size: 13px;
    font-weight: bold;
    color: #3A3B42;
    background: transparent;
}
QLabel#badge_red {
    font-size: 11px;
    font-weight: bold;
    background: #3D0A10;
    color: #E8192C;
    border-radius: 10px;
    padding: 2px 8px;
}
QLabel#badge_blue {
    font-size: 11px;
    font-weight: bold;
    background: #0D2340;
    color: #4A8FD4;
    border-radius: 10px;
    padding: 2px 8px;
}
QLabel#badge_gray {
    font-size: 11px;
    background: #26272C;
    color: #5A5B65;
    border-radius: 10px;
    padding: 2px 8px;
}
QLabel#badge_green {
    font-size: 11px;
    font-weight: bold;
    background: #0A2E1A;
    color: #07C160;
    border-radius: 10px;
    padding: 2px 8px;
}
QLabel#link_lbl {
    font-size: 11px;
    color: #4A8FD4;
    background: transparent;
}
QLabel#chk_off {
    font-size: 12px;
    color: #3A3B42;
    background: transparent;
    padding: 6px 12px;
}
QLabel#chk_on {
    font-size: 12px;
    font-weight: bold;
    color: #E8192C;
    background: #3D0A10;
    border-radius: 0 0 11px 11px;
    padding: 6px 12px;
}

/* ── 滚动条 ── */
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical {
    background: transparent;
    width: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3A3B42;
    border-radius: 3px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: #4A4B52; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

/* ── 进度条 ── */
QProgressBar {
    border: none;
    background: #26272C;
    border-radius: 2px;
    height: 3px;
    font-size: 0px;
}
QProgressBar::chunk {
    background: #E8192C;
    border-radius: 2px;
}

/* ── 右键菜单 ── */
QMenu {
    background: #26272C;
    border: 1px solid #3A3B42;
    border-radius: 8px;
    padding: 4px;
    font-family: "Microsoft YaHei UI";
    font-size: 12px;
    color: #F0F0F2;
}
QMenu::item {
    padding: 7px 16px;
    border-radius: 5px;
    color: #F0F0F2;
}
QMenu::item:selected { background: #2E2F35; }
QMenu::separator {
    height: 1px;
    background: #3A3B42;
    margin: 3px 8px;
}

/* ── 弹窗 ── */
QMessageBox {
    background: #1E1F23;
    color: #F0F0F2;
}
QMessageBox QLabel {
    color: #F0F0F2;
    font-size: 13px;
    background: transparent;
}
QMessageBox QPushButton {
    min-width: 80px;
    padding: 6px 16px;
}

/* ── 文件选择对话框 ── */
QFileDialog {
    background: #1E1F23;
    color: #F0F0F2;
}
"""
