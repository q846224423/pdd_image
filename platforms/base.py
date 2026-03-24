"""
platforms/base.py
平台爬虫基类，所有平台都继承此类并实现 fetch() 方法
"""
from abc import ABC, abstractmethod


class BasePlatform(ABC):
    """
    所有平台爬虫的统一接口。
    每个平台实现 fetch() 方法，返回统一格式的数据列表。
    """

    # 平台唯一标识，用于 UI 下拉框显示
    NAME    = ""    # 如 "小红书"
    ID      = ""    # 如 "xiaohongshu"
    ICON    = ""    # 如 "📕"

    @abstractmethod
    async def fetch(self, keyword: str, max_count: int, db: dict = None) -> list[dict]:
        """
        抓取搜索结果，返回统一格式列表：
        [
          {
            "title":        str,
            "likes":        str,   # 原始字符串，如 "1.2万"
            "likes_int":    int,
            "comments":     str,
            "url":          str,   # 图片直链
            "note_url":     str,   # 原帖/商品链接
            "publish_time": str,   # 相对时间或日期
            "platform":     str,   # 平台 ID
          },
          ...
        ]
        """
        ...
