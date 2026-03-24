"""
config.py
路径常量、配置文件读写、下载记录读写
"""
import json
import os

# ── 路径（以本文件所在目录为基准）──────────────────
_BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR      = os.path.join(_BASE_DIR, "trending_images")
USER_DATA_DIR = os.path.join(_BASE_DIR, "user_data")
CONFIG_FILE   = os.path.join(_BASE_DIR, "config.json")
DB_FILE       = os.path.join(_BASE_DIR, "downloaded.json")
LOGO_FILE     = os.path.join(_BASE_DIR, "logo.png")

os.makedirs(SAVE_DIR,      exist_ok=True)
os.makedirs(USER_DATA_DIR, exist_ok=True)


# ── 配置持久化 ─────────────────────────────────────
def load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(data: dict):
    try:
        cfg = load_config()
        cfg.update(data)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── 已下载记录（去重用）────────────────────────────
# 存储结构：{ "url_hash": { "title", "date", "path" } }
def load_db() -> dict:
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_db(db: dict):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
