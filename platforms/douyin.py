"""
platforms/douyin.py
抖音爬虫 — 抓取搜索结果中的视频封面图
"""
import asyncio
from playwright.async_api import async_playwright

from config import USER_DATA_DIR
from utils import parse_likes
from platforms.base import BasePlatform


class DouyinPlatform(BasePlatform):
    NAME = "抖音"
    ID   = "douyin"
    ICON = "🎵"

    async def fetch(self, keyword: str, max_count: int) -> list[dict]:
        results = []
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR + "_douyin",
                headless=False,
                channel="msedge",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            await page.goto(
                f"https://www.douyin.com/search/{keyword}?type=video"
            )
            await asyncio.sleep(8)

            # 动态滚动，够数量就停
            for _ in range(50):
                _cur = await page.query_selector_all("li.search-result-card, div.video-card, [data-e2e='search-video-card']")
                if len(_cur) >= max_count:
                    break
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(2)

            # 抖音搜索结果视频卡片
            items = await page.query_selector_all(
                "li.search-result-card, div.video-card, [data-e2e='search-video-card']"
            )

            items = items[:max_count]  # 截取到指定数量

            for index, item in enumerate(items):
                try:
                    # 标题
                    title_el = await item.query_selector(
                        "p.video-title, .title, [data-e2e='search-card-desc']"
                    )
                    title = await title_el.inner_text() if title_el else f"video_{index}"
                    title = title.strip()

                    # 点赞数
                    like_el = await item.query_selector(
                        ".like-count, .video-like-count, [data-e2e='like-count']"
                    )
                    like_count = await like_el.inner_text() if like_el else "0"
                    like_count = like_count.strip()

                    # 封面图
                    img_el = await item.query_selector("img.cover, img.poster, img")
                    img_url = ""
                    if img_el:
                        img_url = (
                                await img_el.get_attribute("src") or
                                await img_el.get_attribute("data-src") or ""
                        )
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url

                    # 视频链接
                    link_el = await item.query_selector("a")
                    note_url = ""
                    if link_el:
                        href = await link_el.get_attribute("href") or ""
                        note_url = (
                            "https://www.douyin.com" + href
                            if href.startswith("/") else href
                        )

                    if img_url:
                        results.append({
                            "title":        title,
                            "likes":        like_count,
                            "likes_int":    parse_likes(like_count),
                            "comments":     "0",
                            "url":          img_url,
                            "note_url":     note_url,
                            "publish_time": "",
                            "platform":     self.ID,
                        })
                except Exception:
                    continue

            await context.close()
        return results
