import asyncio
import os
import platform as _platform
import random
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from io import BytesIO

import requests
from PIL import Image, ImageDraw as PILDraw, ImageFilter

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea,
    QFrame, QGridLayout, QProgressBar, QCheckBox,
    QFileDialog, QMessageBox, QApplication,
    QSizePolicy, QSpacerItem, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QPixmap, QImage, QCursor, QColor

from config import SAVE_DIR, load_config, save_config, load_db, save_db
from utils import url_hash, note_hash, parse_likes, relative_days
from ui.styles import QSS, C
from ui.widgets import HoverPreview, ClickableLabel, pil_to_pixmap
from platforms.registry import PLATFORM_OPTIONS, get_platform, PLATFORM_MAP, ALL_PLATFORMS

class FetchThread(QThread):
    finished = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, platform_obj, keywords, max_count, min_likes, db):
        super().__init__()
        self.platform_obj = platform_obj
        self.keywords     = keywords
        self.max_count    = max_count
        self.min_likes    = min_likes
        self.db           = db

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            all_data, seen = [], set()
            for kw in self.keywords:
                results = loop.run_until_complete(
                    self.platform_obj.fetch(kw, self.max_count, self.db))
                for item in results:
                    h = url_hash(item["url"])
                    item["_hash"] = h
                    if h not in seen:
                        seen.add(h)
                        item["already_downloaded"] = False
                        all_data.append(item)
            all_data = [d for d in all_data if d["likes_int"] >= self.min_likes]
            self.finished.emit(all_data)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            loop.close()

PRINT_SIZES = {
    "5寸": (1051, 1500),
    "7寸": (1500, 2102),
}

def smart_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio    = src_w / src_h

    if src_ratio > target_ratio:
        scale = target_h / src_h
    else:
        scale = target_w / src_w

    new_w = max(int(src_w * scale), target_w)
    new_h = max(int(src_h * scale), target_h)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    gray = img.convert("L").filter(ImageFilter.FIND_EDGES)
    pixels = gray.load()
    col_e = [sum(pixels[x, y] for y in range(new_h)) for x in range(new_w)]
    row_e = [sum(pixels[x, y] for x in range(new_w)) for y in range(new_h)]

    def best_offset(energy, total, window):
        if total <= window:
            return 0
        cur = sum(energy[:window])
        best_v, best_i = cur, 0
        for i in range(1, total - window + 1):
            cur = cur - energy[i-1] + energy[i+window-1]
            if cur > best_v:
                best_v, best_i = cur, i
        return min(best_i, total - window)

    cx = best_offset(col_e, new_w, target_w)
    cy = best_offset(row_e, new_h, target_h)

    cropped = img.crop((cx, cy, cx + target_w, cy + target_h))

    if cropped.size != (target_w, target_h):
        cropped = cropped.resize((target_w, target_h), Image.LANCZOS)

    return cropped

class ImageLoadThread(QThread):
    loaded = pyqtSignal(str, object)

    def __init__(self, url, headers):
        super().__init__()
        self.url     = url
        self.headers = headers

    def run(self):
        try:
            res = requests.get(self.url, headers=self.headers, timeout=8)
            res.raise_for_status()
            pil = Image.open(BytesIO(res.content)).convert("RGB")
            self.loaded.emit(self.url, pil)
        except Exception:
            self.loaded.emit(self.url, None)

class DownloadThread(QThread):
    progress   = pyqtSignal(int, int)
    finished   = pyqtSignal(int, int, int)
    db_updated = pyqtSignal(str, dict)

    def __init__(self, items, save_dir, headers, db, crop_sizes=None):
        super().__init__()
        self.items       = items
        self.save_dir    = save_dir
        self.headers     = headers
        self.db          = dict(db)
        self.crop_sizes  = crop_sizes or []

    def run(self):
        ok = skipped = fail = 0
        os.makedirs(self.save_dir, exist_ok=True)
        for i, data in enumerate(self.items, 1):
            self.progress.emit(i, len(self.items))
            h = data.get("_hash") or (note_hash(data["note_url"]) if data.get("note_url") else url_hash(data["url"]))
            if h in self.db:
                path = self.db[h].get("path", "")
                if path and os.path.exists(path):
                    skipped += 1
                    continue
            try:
                time.sleep(random.uniform(0.3, 1.0))

                headers = {
                    **self.headers,
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                }
                res = requests.get(data["url"], headers=headers, timeout=15)

                if res.status_code == 200:
                    content_type = res.headers.get("Content-Type", "")
                    if "image" not in content_type and not res.content[:4] in [
                        b"\xff\xd8\xff\xe0",
                        b"\xff\xd8\xff\xe1",
                        b"\xff\xd8\xff\xdb",
                        b"\x89PNG",
                        b"RIFF",
                        b"GIF8",
                    ]:
                        fail += 1
                        continue

                    try:
                        pil_check = Image.open(BytesIO(res.content))
                        pil_check.verify()
                    except Exception:
                        fail += 1
                        continue

                    pil_img = Image.open(BytesIO(res.content)).convert("RGB")

                    safe = "".join(
                        c for c in data["title"] if c.isalnum() or c in "_ "
                    ).strip() or f"img_{data['likes']}"
                    date_dir = os.path.join(self.save_dir,
                                            datetime.now().strftime("%Y-%m-%d"))
                    os.makedirs(date_dir, exist_ok=True)
                    path = os.path.join(date_dir, f"{safe}_{data['likes']}.jpg")

                    pil_img.save(path, "JPEG", quality=95, subsampling=0)

                    self.db_updated.emit(h, {
                        "title": data["title"],
                        "date":  datetime.now().strftime("%Y-%m-%d"),
                        "path":  path,
                    })
                    if self.crop_sizes:
                        try:
                            pil = pil_img
                            for size_name in self.crop_sizes:
                                if size_name not in PRINT_SIZES:
                                    continue
                                tw, th = PRINT_SIZES[size_name]
                                size_dir = os.path.join(date_dir, size_name)
                                os.makedirs(size_dir, exist_ok=True)
                                crop_path = os.path.join(size_dir, f"{safe}_{data['likes']}.jpg")
                                cropped = smart_crop(pil, tw, th)
                                cropped.save(
                                    crop_path, "JPEG",
                                    quality=95,
                                    dpi=(300, 300),
                                    subsampling=0,
                                )
                        except Exception:
                            pass
                    ok += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
        self.finished.emit(ok, skipped, fail)

class CardWidget(QFrame):
    THUMB = 115

    def __init__(self, data, placeholder_px, pil_cache,
                 hover_preview, on_copy, on_single_dl, parent=None):
        super().__init__(parent)
        self.data          = data
        self.pil_cache     = pil_cache
        self.hover_preview = hover_preview
        self.on_copy       = on_copy
        self.on_single_dl  = on_single_dl
        self._selected     = False
        self._already      = data.get("already_downloaded", False)

        self.setObjectName("card_downloaded" if self._already else "card")
        self.setFixedHeight(162)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        top = QWidget()
        top.setStyleSheet("background:transparent;")
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(0)

        self.img_lbl = QLabel()
        self.img_lbl.setFixedSize(self.THUMB, self.THUMB)
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setStyleSheet(
            "background:#2E2F35;"
            "border-top-left-radius:11px;"
        )
        self.img_lbl.setPixmap(self._fit_px(placeholder_px))
        self.img_lbl.setScaledContents(False)
        self.img_lbl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.img_lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.img_lbl.customContextMenuRequested.connect(self._ctx_menu)
        self.img_lbl.enterEvent = self._img_enter
        self.img_lbl.leaveEvent = self._img_leave
        top_lay.addWidget(self.img_lbl)

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(12, 10, 12, 6)
        body_lay.setSpacing(5)

        if self._already:
            pill = QLabel(" ✓ 已下载 ")
            pill.setObjectName("badge_gray")
            pill.setFixedWidth(56)
            body_lay.addWidget(pill)

        self.title_lbl = QLabel(data["title"])
        self.title_lbl.setObjectName(
            "card_title_dim" if self._already else "card_title")
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.title_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        body_lay.addWidget(self.title_lbl)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(5)
        badge_row.setContentsMargins(0, 0, 0, 0)

        def mk_badge(text, name):
            b = QLabel(text)
            b.setObjectName(name)
            return b

        badge_row.addWidget(mk_badge(f"❤ {data['likes']}", "badge_red"))
        if data.get("comments") and data["comments"] != "0":
            badge_row.addWidget(mk_badge(f"💬 {data['comments']}", "badge_blue"))
        if data.get("publish_time"):
            badge_row.addWidget(mk_badge(f"📅 {data['publish_time']}", "badge_gray"))
        pid = data.get("platform", "")
        if pid and pid in PLATFORM_MAP:
            p = PLATFORM_MAP[pid]
            badge_row.addWidget(mk_badge(f"{p.ICON} {p.NAME}", "badge_gray"))
        badge_row.addStretch()
        body_lay.addLayout(badge_row)

        if data.get("note_url"):
            lk = ClickableLabel("🔗 打开原帖")
            lk.setObjectName("link_lbl")
            lk.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            lk.clicked.connect(lambda: webbrowser.open(data["note_url"]))
            body_lay.addWidget(lk)

        body_lay.addStretch()
        top_lay.addWidget(body, stretch=1)
        lay.addWidget(top, stretch=1)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background:#2E2F35; max-height:1px; border:none;")
        lay.addWidget(div)

        self.chk = ClickableLabel("○  选择下载")
        self.chk.setObjectName("chk_off")
        self.chk.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chk.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.chk.clicked.connect(self._toggle)
        lay.addWidget(self.chk)

    def _fit_px(self, px):
        return px.scaled(self.THUMB, self.THUMB,
                         Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)

    def _toggle(self):
        self._selected = not self._selected
        if self._selected:
            self.setObjectName("card_selected")
            self.chk.setObjectName("chk_on")
            self.chk.setText("●  已选择下载")
        else:
            self.setObjectName("card_downloaded" if self._already else "card")
            self.chk.setObjectName("chk_off")
            self.chk.setText("○  选择下载")
        for w in [self, self.chk]:
            w.style().unpolish(w)
            w.style().polish(w)

    def is_selected(self): return self._selected

    def set_image(self, pil_img):
        if pil_img is None:
            return
        thumb = pil_img.copy()
        thumb.thumbnail((self.THUMB, self.THUMB), Image.LANCZOS)
        self.img_lbl.setPixmap(self._fit_px(pil_to_pixmap(thumb)))

    def _img_enter(self, _):
        pil = self.pil_cache.get(self.data["url"])
        if pil:
            self.hover_preview.trigger(pil, QCursor.pos())

    def _img_leave(self, _):
        self.hover_preview.hide_preview()

    def _ctx_menu(self, pos):
        m = QMenu(self)

        m.addAction("🔍  预览大图",     self._big_preview)
        m.addAction("🔗  复制图片链接", lambda: self.on_copy(self.data["url"]))
        if self.data.get("note_url"):
            m.addSeparator()
            m.addAction("📖  打开原帖",
                        lambda: webbrowser.open(self.data["note_url"]))
            m.addAction("📋  复制帖子链接",
                        lambda: self.on_copy(self.data["note_url"]))
        m.addSeparator()
        m.addAction("⬇  单独下载此图", lambda: self.on_single_dl(self.data))
        m.exec(self.img_lbl.mapToGlobal(pos))

    def _big_preview(self):
        pil = self.pil_cache.get(self.data["url"])
        if not pil:
            return
        from PyQt6.QtWidgets import QDialog
        dlg = QDialog()
        dlg.setWindowTitle("大图预览")
        dlg.setStyleSheet("background:#111111;")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lbl = QLabel()
        screen = QApplication.primaryScreen().geometry()
        prev = pil.copy()
        prev.thumbnail(
            (int(screen.width() * .85), int(screen.height() * .85)),
            Image.LANCZOS)
        lbl.setPixmap(pil_to_pixmap(prev))
        lay.addWidget(lbl)
        dlg.adjustSize()
        dlg.exec()

class MainWindow(QMainWindow):
    COLS = 2

    def __init__(self):
        super().__init__()
        self.setWindowTitle("选品图片抓取器")
        self.resize(980, 800)
        self.setStyleSheet(QSS)
        self.setMinimumSize(760, 600)

        self.images_data   = []
        self.filtered_data = []
        self.card_widgets  = []
        self.pil_cache     = {}
        self.img_threads   = []
        self.fetch_thread  = None
        self.dl_thread     = None
        self.db            = load_db()
        cfg                = load_config()
        self.save_dir      = cfg.get("save_dir", SAVE_DIR)
        self.sort_asc        = False
        self.hide_downloaded = False
        self._cur_platform_idx = 0

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.xiaohongshu.com/"
        }

        self.hover_preview = HoverPreview()

        root = QWidget()
        self.setCentralWidget(root)
        root_lay = QHBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        sidebar = self._build_sidebar()
        root_lay.addWidget(sidebar)

        main_w = QWidget()
        main_w.setStyleSheet("background:#16171A;")
        self._main_lay = QVBoxLayout(main_w)
        self._main_lay.setContentsMargins(0, 0, 0, 0)
        self._main_lay.setSpacing(0)
        root_lay.addWidget(main_w, stretch=1)

        self._build_topbar()
        self._build_searchbar()
        self._build_filterbar()
        self._build_gallery()
        self._build_footer()
        self._center()

    def _build_sidebar(self):
        sb = QFrame()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(C["sidebar_w"])
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(8, 14, 8, 14)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        def divider():
            d = QFrame()
            d.setFrameShape(QFrame.Shape.HLine)
            d.setStyleSheet("background:#E8E9EC; max-height:1px; border:none; margin:4px 4px;")
            return d

        lay.addWidget(divider())

        self._sb_btns = []
        for i, p in enumerate(ALL_PLATFORMS):
            btn = QPushButton(p.ICON)
            btn.setObjectName("sb_btn_active" if i == 0 else "sb_btn")
            btn.setFixedSize(36, 36)
            btn.setToolTip(p.NAME)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, idx=i: self._switch_platform(idx))
            lay.addWidget(btn)
            self._sb_btns.append(btn)

        lay.addWidget(divider())
        lay.addStretch()

        setting_btn = QPushButton("⚙")
        setting_btn.setObjectName("sb_btn")
        setting_btn.setFixedSize(36, 36)
        setting_btn.setToolTip("设置")
        setting_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        lay.addWidget(setting_btn)

        return sb

    def _switch_platform(self, idx):
        self._cur_platform_idx = idx
        for i, btn in enumerate(self._sb_btns):
            btn.setObjectName("sb_btn_active" if i == idx else "sb_btn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        p = ALL_PLATFORMS[idx]
        self.platform_lbl.setText(f"{p.ICON}  {p.NAME}")

    def _build_topbar(self):
        frm = QFrame()
        frm.setObjectName("topbar")
        frm.setFixedHeight(56)
        lay = QHBoxLayout(frm)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(8)

        title = QLabel("选品图片抓取器")
        title.setObjectName("title_lbl")
        lay.addWidget(title)

        sub = QLabel("by Ralo")
        sub.setObjectName("sub_lbl")
        lay.addWidget(sub)

        lay.addStretch()

        self.status_pill = QLabel("● 就绪")
        self.status_pill.setObjectName("status_pill")
        lay.addWidget(self.status_pill)

        self._main_lay.addWidget(frm)

    def _set_status(self, text, busy=False):
        self.status_pill.setText(f"{'◌' if busy else '●'}  {text}")
        self.status_pill.setObjectName(
            "status_pill_busy" if busy else "status_pill")
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

    def _build_searchbar(self):
        frm = QFrame()
        frm.setObjectName("searchbar")
        lay = QHBoxLayout(frm)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(12)

        p_wrap = self._field_wrap("平台")
        self.platform_lbl = QLabel(f"{ALL_PLATFORMS[0].ICON}  {ALL_PLATFORMS[0].NAME}")
        self.platform_lbl.setFixedWidth(130)
        self.platform_lbl.setStyleSheet("background:#26272C; border:1px solid #3A3B42; border-radius:8px; padding:7px 12px; font-size:13px; color:#F0F0F2;")
        p_wrap.layout().addWidget(self.platform_lbl)
        lay.addWidget(p_wrap)

        kw_wrap = self._field_wrap("关键词（逗号分隔）")
        self.kw_entry = QLineEdit("奶油风装饰画")
        self.kw_entry.setMinimumWidth(200)
        kw_wrap.layout().addWidget(self.kw_entry)
        lay.addWidget(kw_wrap, stretch=1)

        sc_wrap = self._field_wrap("抓取数量")
        self.scroll_entry = QLineEdit("30")
        self.scroll_entry.setFixedWidth(64)
        sc_wrap.layout().addWidget(self.scroll_entry)
        lay.addWidget(sc_wrap)

        lk_wrap = self._field_wrap("最低点赞")
        self.likes_entry = QLineEdit("0")
        self.likes_entry.setFixedWidth(72)
        lk_wrap.layout().addWidget(self.likes_entry)
        lay.addWidget(lk_wrap)

        self.search_btn = QPushButton("▶  开始抓取")
        self.search_btn.setObjectName("btn_primary")
        self.search_btn.setFixedHeight(36)
        self.search_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.search_btn.clicked.connect(self._start_search)
        lay.addWidget(self.search_btn)

        self._main_lay.addWidget(frm)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.hide()
        self._main_lay.addWidget(self.progress)

    def _field_wrap(self, label_text):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label_text.upper())
        lbl.setObjectName("field_lbl")
        lay.addWidget(lbl)
        return w

    def _build_filterbar(self):
        self.filter_frm = QFrame()
        self.filter_frm.setObjectName("filterbar")
        self.filter_frm.setFixedHeight(42)
        self.filter_frm.hide()

        lay = QHBoxLayout(self.filter_frm)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(8)

        self.result_lbl = QLabel()
        self.result_lbl.setObjectName("result_lbl")
        lay.addWidget(self.result_lbl)
        lay.addStretch()

        def mk_small_entry(w, ph=""):
            e = QLineEdit()
            e.setFixedWidth(w)
            e.setFixedHeight(28)
            if ph:
                e.setPlaceholderText(ph)
            return e

        def muted(text):
            l = QLabel(text)
            l.setStyleSheet("color:#606168;font-size:11px;background:transparent;")
            return l

        self.f_likes = mk_small_entry(52, "点赞")
        lay.addWidget(self.f_likes)
        lay.addWidget(muted("点赞"))

        self.f_days = mk_small_entry(44, "天数")
        lay.addWidget(self.f_days)
        lay.addWidget(muted("天内"))

        def mk_btn(text, name, slot):
            b = QPushButton(text)
            if name:
                b.setObjectName(name)
            b.setFixedHeight(28)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.clicked.connect(slot)
            return b

        self.hide_dl_btn = QPushButton("隐藏已下载")
        self.hide_dl_btn.setFixedHeight(28)
        self.hide_dl_btn.setCheckable(True)
        self.hide_dl_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.hide_dl_btn.toggled.connect(self._on_hide_downloaded_toggle)
        self.hide_dl_btn.setStyleSheet("""
            QPushButton {
                background: #26272C;
                border: 1px solid #3A3B42;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
                color: #9A9BA8;
            }
            QPushButton:checked {
                background: #0A2E1A;
                border: 1px solid #07C160;
                color: #07C160;
                font-weight: bold;
            }
            QPushButton:hover { background: #2E2F35; }
        """)
        lay.addWidget(self.hide_dl_btn)
        lay.addWidget(mk_btn("筛选", "btn_filter", self._apply_filter))
        lay.addWidget(mk_btn("⇅ 点赞", None, self._toggle_sort))
        lay.addWidget(mk_btn("⇅ 时间", None, self._toggle_sort_time))

        self._main_lay.addWidget(self.filter_frm)

    def _build_gallery(self):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background:#16171A;")

        self.gallery_w = QWidget()
        self.gallery_w.setStyleSheet("background:#16171A;")
        self.gallery_lay = QGridLayout(self.gallery_w)
        self.gallery_lay.setContentsMargins(14, 14, 14, 14)
        self.gallery_lay.setSpacing(10)
        self.gallery_lay.setColumnStretch(0, 1)
        self.gallery_lay.setColumnStretch(1, 1)

        self.scroll.setWidget(self.gallery_w)
        self._main_lay.addWidget(self.scroll, stretch=1)

    def _build_footer(self):
        frm = QFrame()
        frm.setObjectName("footer")
        lay = QVBoxLayout(frm)
        lay.setContentsMargins(20, 10, 20, 10)
        lay.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(8)

        def ghost(text, slot, obj=None):
            b = QPushButton(text)
            if obj:
                b.setObjectName(obj)
            b.setFixedHeight(32)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.clicked.connect(slot)
            return b

        row1.addWidget(ghost("全选",    self._select_all))
        row1.addWidget(ghost("取消全选", self._deselect_all))

        self.dl_status = QLabel()
        self.dl_status.setStyleSheet(
            "color:#606168;font-size:11px;background:transparent;")
        row1.addWidget(self.dl_status)
        row1.addStretch()

        size_style = """
            QCheckBox {
                color: #9A9BA8;
                font-size: 12px;
                spacing: 5px;
                background: transparent;
            }
            QCheckBox:checked { color: #07C160; font-weight: bold; }
            QCheckBox::indicator {
                width: 14px; height: 14px;
                border: 1px solid #3A3B42;
                border-radius: 3px;
                background: #26272C;
            }
            QCheckBox::indicator:checked {
                background: #07C160;
                border-color: #07C160;
            }
        """
        self.chk_5cun = QCheckBox("5寸")
        self.chk_7cun = QCheckBox("7寸")
        self.chk_5cun.setStyleSheet(size_style)
        self.chk_7cun.setStyleSheet(size_style)
        self.chk_5cun.setToolTip("裁剪为 5寸打印尺寸 (89×127mm)")
        self.chk_7cun.setToolTip("裁剪为 7寸打印尺寸 (127×178mm)")
        row1.addWidget(self.chk_5cun)
        row1.addWidget(self.chk_7cun)
        row1.addSpacing(8)

        self.dl_btn = QPushButton("⬇  下载选中图片")
        self.dl_btn.setObjectName("btn_download")
        self.dl_btn.setFixedHeight(36)
        self.dl_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dl_btn.clicked.connect(self._download_selected)
        row1.addWidget(self.dl_btn)
        lay.addLayout(row1)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background:#2E2F35; max-height:1px; border:none;")
        lay.addWidget(div)

        row2 = QHBoxLayout()
        row2.setSpacing(8)

        path_icon = QLabel("📁")
        path_icon.setStyleSheet("color:#606168;font-size:13px;background:transparent;")
        row2.addWidget(path_icon)

        self.path_entry = QLineEdit(self.save_dir)
        self.path_entry.setObjectName("path_entry")
        self.path_entry.setReadOnly(True)
        self.path_entry.setFixedHeight(30)
        row2.addWidget(self.path_entry, stretch=1)

        row2.addWidget(ghost("更改", self._pick_folder))
        row2.addWidget(ghost("打开", self._open_folder, "btn_link"))

        self.db_lbl = QLabel()
        self.db_lbl.setStyleSheet(
            "color:#606168;font-size:11px;background:transparent;")
        row2.addWidget(self.db_lbl)
        self._refresh_db_label()

        row2.addStretch()
        row2.addWidget(ghost("清除记录", self._clear_db, "btn_danger"))
        lay.addLayout(row2)

        self._main_lay.addWidget(frm)

    def _refresh_db_label(self):
        self.db_lbl.setText(f"历史记录：{len(self.db)} 张")

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2)

    def _start_search(self):
        raw_kw = self.kw_entry.text().strip()
        if not raw_kw:
            QMessageBox.warning(self, "提示", "请输入搜索关键词！")
            return
        try:
            max_count = int(self.scroll_entry.text().strip())
            if max_count <= 0:
                max_count = 30
        except ValueError:
            QMessageBox.warning(self, "提示", "抓取数量必须是整数！")
            return
        try:
            min_likes = parse_likes(self.likes_entry.text().strip() or "0")
        except Exception:
            min_likes = 0

        keywords = [k.strip() for k in
                    raw_kw.replace("，", ",").split(",") if k.strip()]
        platform_obj = ALL_PLATFORMS[self._cur_platform_idx]

        self.search_btn.setEnabled(False)
        self._set_status("正在抓取，请稍候…", busy=True)
        self.progress.show()

        for i in reversed(range(self.gallery_lay.count())):
            w = self.gallery_lay.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.card_widgets.clear()
        self.pil_cache.clear()

        self.fetch_thread = FetchThread(
            platform_obj, keywords, max_count, min_likes, self.db)
        self.fetch_thread.finished.connect(self._on_fetch_done)
        self.fetch_thread.error.connect(self._on_fetch_error)
        self.fetch_thread.start()

    def _on_fetch_done(self, data):
        self.progress.hide()
        self.search_btn.setEnabled(True)
        self.images_data   = data
        self.filtered_data = list(data)

        total     = len(data)
        new_cnt   = sum(1 for d in data if not d["already_downloaded"])
        dup_cnt   = total - new_cnt

        self._set_status(f"共 {total} 张  ·  新增 {new_cnt}  ·  重复 {dup_cnt}")
        self.result_lbl.setText(
            f"共 {total} 条结果  ·  新增 {new_cnt} 张  ·  重复 {dup_cnt} 张")
        self.filter_frm.show()
        self._build_cards(self.filtered_data)

    def _on_fetch_error(self, msg):
        self.progress.hide()
        self.search_btn.setEnabled(True)
        self._set_status(f"抓取失败：{msg}", busy=False)

    def _build_cards(self, data_list):
        for i in reversed(range(self.gallery_lay.count())):
            w = self.gallery_lay.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.card_widgets.clear()

        placeholder_px = QPixmap(CardWidget.THUMB, CardWidget.THUMB)
        placeholder_px.fill(QColor("#2E2F35"))

        for idx, data in enumerate(data_list):
            row, col = divmod(idx, self.COLS)
            card = CardWidget(
                data, placeholder_px, self.pil_cache,
                self.hover_preview,
                on_copy=self._copy,
                on_single_dl=lambda d: self._download_list([d])
            )
            self.gallery_lay.addWidget(card, row, col)
            self.card_widgets.append(card)

            t = ImageLoadThread(data["url"], self.headers)
            t.loaded.connect(self._on_img_loaded)
            t.start()
            self.img_threads.append(t)

    def _on_img_loaded(self, url, pil_img):
        if pil_img is None:
            return
        self.pil_cache[url] = pil_img
        for card in self.card_widgets:
            if card.data["url"] == url:
                card.set_image(pil_img)
                break

    def _toggle_sort(self):
        self.sort_asc = not self.sort_asc
        self.filtered_data.sort(
            key=lambda x: x["likes_int"], reverse=not self.sort_asc)
        self._build_cards(self.filtered_data)

    def _toggle_sort_time(self):
        self.filtered_data.sort(
            key=lambda d: relative_days(d.get("publish_time", "")))
        self._build_cards(self.filtered_data)

    def _on_hide_downloaded_toggle(self, checked):
        self.hide_downloaded = checked
        self._apply_filter()

    def _apply_filter(self):
        try:
            mn = parse_likes(self.f_likes.text().strip() or "0")
        except Exception:
            mn = 0
        max_days = None
        try:
            raw = self.f_days.text().strip()
            if raw:
                max_days = int(raw)
        except Exception:
            pass

        def ok_time(d):
            if max_days is None:
                return True
            pt = d.get("publish_time", "")
            return relative_days(pt) <= max_days if pt else True

        self.filtered_data = [
            d for d in self.images_data
            if d["likes_int"] >= mn
               and ok_time(d)
               and (not self.hide_downloaded or not d.get("already_downloaded", False))
        ]
        self._build_cards(self.filtered_data)

    def _select_all(self):
        for c in self.card_widgets:
            if not c.is_selected():
                c._toggle()

    def _deselect_all(self):
        for c in self.card_widgets:
            if c.is_selected():
                c._toggle()

    def _copy(self, text):
        QApplication.clipboard().setText(text)
        self._set_status("✅ 已复制到剪贴板")

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择保存文件夹", self.save_dir)
        if folder:
            self.save_dir = folder
            self.path_entry.setText(folder)
            save_config({"save_dir": folder})
            self._set_status("✅ 保存目录已更改")

    def _open_folder(self):
        os.makedirs(self.save_dir, exist_ok=True)
        sys_name = _platform.system()
        if sys_name == "Windows":  os.startfile(self.save_dir)
        elif sys_name == "Darwin": subprocess.Popen(["open", self.save_dir])
        else:                      subprocess.Popen(["xdg-open", self.save_dir])

    def _clear_db(self):
        reply = QMessageBox.question(
            self, "确认", "清除后之前下载的图片会被视为新图，确定吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear()
            save_db(self.db)
            self._refresh_db_label()
            self._set_status("✅ 去重记录已清除")

    def _download_selected(self):
        sel = [c.data for c in self.card_widgets if c.is_selected()]
        if not sel:
            QMessageBox.warning(self, "提示", "请先勾选要下载的图片！")
            return
        self._download_list(sel)

    def _download_list(self, items):
        self.dl_btn.setEnabled(False)
        self.dl_btn.setText("下载中…")
        crop_sizes = []
        if self.chk_5cun.isChecked(): crop_sizes.append("5寸")
        if self.chk_7cun.isChecked(): crop_sizes.append("7寸")
        self.dl_thread = DownloadThread(
            items, self.save_dir, self.headers, self.db, crop_sizes)
        self.dl_thread.progress.connect(
            lambda cur, tot: self.dl_status.setText(f"正在下载 {cur}/{tot}…"))
        self.dl_thread.db_updated.connect(
            lambda h, rec: self.db.update({h: rec}))
        self.dl_thread.finished.connect(self._on_dl_done)
        self.dl_thread.start()

    def _on_dl_done(self, ok, skipped, fail):
        self.dl_btn.setEnabled(True)
        self.dl_btn.setText("⬇  下载选中图片")
        self.dl_status.setText(
            f"✅ 新下载 {ok}  ⏭ 跳过 {skipped}  ❌ 失败 {fail}")
        save_db(self.db)
        self.db = load_db()
        self._refresh_db_label()
        if ok:
            date_dir = os.path.join(
                self.save_dir, datetime.now().strftime("%Y-%m-%d"))
            QMessageBox.information(
                self, "下载完成",
                f"新下载：{ok} 张\n跳过重复：{skipped} 张\n失败：{fail} 张\n\n保存至：{date_dir}")
        elif skipped:
            QMessageBox.information(self, "提示", f"所选 {skipped} 张均已下载过。")
        else:
            QMessageBox.warning(self, "提示", "全部下载失败，请检查网络")
