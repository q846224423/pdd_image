"""
platforms/jingdong.py
京东爬虫 — 抓取商品主图和评论数
"""
import asyncio
from playwright.async_api import async_playwright

from config import USER_DATA_DIR
from utils import parse_likes
from platforms.base import BasePlatform


class JingdongPlatform(BasePlatform):
    NAME = "京东"
    ID   = "jingdong"
    ICON = "🔴"

    async def fetch(self, keyword: str, max_count: int) -> list[dict]:
        results = []
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR + "_jingdong",
                headless=False,
                channel="msedge",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            await page.goto(
                f"https://search.jd.com/Search?keyword={keyword}&enc=utf-8&wq={keyword}&pvid=1"
            )
            await asyncio.sleep(6)

            # 动态滚动，够数量就停
            for _ in range(50):
                _cur = await page.query_selector_all("#J_goodsList li.gl-item, .goods-list li")
                if len(_cur) >= max_count:
                    break
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(2)

            items = await page.query_selector_all(
                "#J_goodsList li.gl-item, .goods-list li"
            )

            items = items[:max_count]  # 截取到指定数量

            for index, item in enumerate(items):
                try:
                    # 商品名
                    title_el = await item.query_selector(
                        ".p-name em, .p-name a"
                    )
                    title = await title_el.inner_text() if title_el else f"item_{index}"
                    title = title.strip()[:50]

                    # 评论数
                    comment_el = await item.query_selector(".p-commit strong a")
                    comment_count = await comment_el.inner_text() if comment_el else "0"
                    comment_count = comment_count.strip()

                    # 商品主图
                    img_el = await item.query_selector(".p-img img")
                    img_url = ""
                    if img_el:
                        img_url = (
                                await img_el.get_attribute("src") or
                                await img_el.get_attribute("data-lazy-img") or
                                await img_el.get_attribute("data-src") or ""
                        )
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url

                    # 商品链接
                    link_el = await item.query_selector(".p-img a")
                    note_url = ""
                    if link_el:
                        href = await link_el.get_attribute("href") or ""
                        note_url = (
                            "https:" + href if href.startswith("//")
                            else "https://item.jd.com" + href if href.startswith("/")
                            else href
                        )

                    if img_url:
                        results.append({
                            "title":        title,
                            "likes":        comment_count,
                            "likes_int":    parse_likes(comment_count),
                            "comments":     comment_count,
                            "url":          img_url,
                            "note_url":     note_url,
                            "publish_time": "",
                            "platform":     self.ID,
                        })
                except Exception:
                    continue

            await context.close()
        return results
