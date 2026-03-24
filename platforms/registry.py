"""
platforms/registry.py
平台注册表 — 统一管理所有可用平台
新增平台只需在这里注册一行，其他平台暂时注释保留，后续开放取消注释即可
"""
from platforms.xiaohongshu import XiaohongshuPlatform
from platforms.douyin      import DouyinPlatform      # 暂未开放
from platforms.bilibili    import BilibiliPlatform    # 暂未开放
from platforms.weibo       import WeiboPlatform       # 暂未开放
from platforms.taobao      import TaobaoPlatform      # 暂未开放
from platforms.jingdong    import JingdongPlatform    # 暂未开放

# 当前开放的平台
ALL_PLATFORMS = [
    XiaohongshuPlatform(),
    # DouyinPlatform(),
    # BilibiliPlatform(),
    # WeiboPlatform(),
    # TaobaoPlatform(),
    # JingdongPlatform(),
]

PLATFORM_MAP     = {p.ID: p for p in ALL_PLATFORMS}
PLATFORM_OPTIONS = [f"{p.ICON} {p.NAME}" for p in ALL_PLATFORMS]


def get_platform(display_name: str):
    """根据下拉框显示文字找到对应平台实例"""
    for p in ALL_PLATFORMS:
        if f"{p.ICON} {p.NAME}" == display_name:
            return p
    return ALL_PLATFORMS[0]
