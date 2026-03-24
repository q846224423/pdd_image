"""
platforms/weibo.py
微博爬虫 — 抓取搜索结果中的图片内容
"""
import asyncio
from playwright.async_api import async_playwright

from config import USER_DATA_DIR
from utils import parse_likes
from platforms.base import BasePlatform


class WeiboPlatform(BasePlatform):
    NAME = "微博"
    ID   = "weibo"
    ICON = "🌐"

    async def fetch(self, keyword: str, max_count: int) -> list[dict]:
        results = []
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR + "_weibo",
                headless=False,
                channel="msedge",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            await page.goto(
                f"https://s.weibo.com/weibo?q={keyword}&Refer=index"
            )
            await asyncio.sleep(6)

            # 动态滚动，够数量就停
            for _ in range(50):
                _cur = await page.query_selector_all("div.card-wrap[mid], .card.m-panel")
                if len(_cur) >= max_count:
                    break
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(2)

            items = await page.query_selector_all(
                "div.card-wrap[mid], .card.m-panel"
            )

            items = items[:max_count]  # 截取到指定数量

            for index, item in enumerate(items):
                try:
                    # 微博正文
                    text_el = await item.query_selector(
                        "p.txt, .weibo-text, [node-type='feed_list_content']"
                    )
                    title = ""
                    if text_el:
                        title = (await text_el.inner_text()).strip()[:60]
                    if not title:
                        title = f"weibo_{index}"

                    # 点赞数
                    like_el = await item.query_selector(
                        ".pos em, [action-type='fl_like'] em, .woo-like-count"
                    )
                    like_count = await like_el.inner_text() if like_el else "0"
                    like_count = like_count.strip()

                    # 评论数
                    comment_el = await item.query_selector(
                        "[action-type='fl_comment'] em, .woo-comment-count"
                    )
                    comment_count = await comment_el.inner_text() if comment_el else "0"

                    # 发布时间
                    time_el = await item.query_selector("a.from, .time")
                    publish_time = ""
                    if time_el:
                        publish_time = (await time_el.inner_text()).strip()

                    # 图片（取第一张）
                    img_el = await item.query_selector(
                        ".media-piclist img, .pic-list img, img.media-image"
                    )
                    img_url = ""
                    if img_el:
                        img_url = (
                                await img_el.get_attribute("src") or
                                await img_el.get_attribute("data-src") or ""
                        )
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url
                        # 换成原图尺寸
                        img_url = img_url.replace("/thumb150/", "/large/").replace(
                            "/bmiddle/", "/large/"
                        )

                    # 帖子链接
                    link_el = await item.query_selector("a.from")
                    note_url = ""
                    if link_el:
                        href = await link_el.get_attribute("href") or ""
                        note_url = (
                            "https:" + href if href.startswith("//")
                            else href
                        )

                    if img_url:
                        results.append({
                            "title":        title,
                            "likes":        like_count,
                            "likes_int":    parse_likes(like_count),
                            "comments":     comment_count,
                            "url":          img_url,
                            "note_url":     note_url,
                            "publish_time": publish_time,
                            "platform":     self.ID,
                        })
                except Exception:
                    continue

            await context.close()
        return results
