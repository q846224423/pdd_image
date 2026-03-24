"""
platforms/bilibili.py
B站爬虫 — 抓取搜索结果视频封面图
"""
import asyncio
from playwright.async_api import async_playwright

from config import USER_DATA_DIR
from utils import parse_likes
from platforms.base import BasePlatform


class BilibiliPlatform(BasePlatform):
    NAME = "B站"
    ID   = "bilibili"
    ICON = "📺"

    async def fetch(self, keyword: str, max_count: int) -> list[dict]:
        results = []
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR + "_bilibili",
                headless=False,
                channel="msedge",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            await page.goto(
                f"https://search.bilibili.com/all?keyword={keyword}&order=click"
            )
            await asyncio.sleep(6)

            # 动态滚动，够数量就停
            for _ in range(50):
                _cur = await page.query_selector_all(".bili-video-card, .video-item")
                if len(_cur) >= max_count:
                    break
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(2)

            items = await page.query_selector_all(
                ".bili-video-card, .video-item"
            )

            items = items[:max_count]  # 截取到指定数量

            for index, item in enumerate(items):
                try:
                    title_el = await item.query_selector(
                        ".bili-video-card__info--tit, .title"
                    )
                    title = await title_el.inner_text() if title_el else f"video_{index}"
                    title = title.strip()

                    # 播放量当做点赞数
                    play_el = await item.query_selector(
                        ".bili-video-card__stats--item:first-child span, .play-count"
                    )
                    play_count = await play_el.inner_text() if play_el else "0"
                    play_count = play_count.strip()

                    # 弹幕数
                    dm_el = await item.query_selector(
                        ".bili-video-card__stats--item:nth-child(2) span"
                    )
                    dm_count = await dm_el.inner_text() if dm_el else "0"

                    # 封面图
                    img_el = await item.query_selector(
                        ".bili-video-card__image--wrap img, img.cover"
                    )
                    img_url = ""
                    if img_el:
                        img_url = (
                                await img_el.get_attribute("src") or
                                await img_el.get_attribute("data-src") or ""
                        )
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url

                    # 视频链接
                    link_el = await item.query_selector("a.bili-video-card__image--wrap, a")
                    note_url = ""
                    if link_el:
                        href = await link_el.get_attribute("href") or ""
                        note_url = (
                            "https:" + href if href.startswith("//")
                            else "https://www.bilibili.com" + href if href.startswith("/")
                            else href
                        )

                    if img_url:
                        results.append({
                            "title":        title,
                            "likes":        play_count,
                            "likes_int":    parse_likes(play_count),
                            "comments":     dm_count,
                            "url":          img_url,
                            "note_url":     note_url,
                            "publish_time": "",
                            "platform":     self.ID,
                        })
                except Exception:
                    continue

            await context.close()
        return results
