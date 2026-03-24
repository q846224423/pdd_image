"""
utils.py
通用工具函数：URL 哈希、点赞数解析、相对时间转换
"""
import hashlib
import re


def url_hash(url: str) -> str:
    """
    对 URL 取 MD5 作为去重 key。
    小红书图片 URL 主路径含动态签名每次不同，
    取最后一段文件名（如 abc123.jpg）作为稳定标识。
    """
    base = url.split("?")[0].rstrip("/")
    # 取路径最后一段（文件名部分），去掉扩展名
    filename = base.split("/")[-1].split(".")[0]
    # 如果文件名够长（32位哈希），直接用它；否则用完整 base
    key = filename if len(filename) >= 16 else base
    return hashlib.md5(key.encode()).hexdigest()


def note_hash(note_url: str) -> str:
    """用笔记原帖 URL 做去重 key，比图片 URL 更稳定"""
    base = note_url.split("?")[0].rstrip("/")
    return hashlib.md5(base.encode()).hexdigest()


def parse_likes(s: str) -> int:
    """把'1.2万'等字符串转为整数"""
    s = str(s).strip()
    try:
        if "万" in s:
            return int(float(s.replace("万", "")) * 10000)
        return int(s)
    except Exception:
        return 0


def relative_days(pt: str) -> int:
    """
    把相对时间字符串转为大约天数：
    '刚刚' / '2小时前' -> 0
    '3天前'            -> 3
    '2周前'            -> 14
    '1个月前'          -> 30
    '1年前'            -> 365
    无法解析           -> 9999
    """
    if not pt:
        return 9999
    pt = pt.strip()
    if "刚刚" in pt or "小时" in pt or "分钟" in pt:
        return 0
    m = re.search(r"(\d+)\s*天", pt)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*周", pt)
    if m:
        return int(m.group(1)) * 7
    m = re.search(r"(\d+)\s*个?月", pt)
    if m:
        return int(m.group(1)) * 30
    m = re.search(r"(\d+)\s*年", pt)
    if m:
        return int(m.group(1)) * 365
    return 9999
