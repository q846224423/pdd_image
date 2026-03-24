"""
platforms/taobao.py
淘宝/天猫爬虫 — 抓取商品主图和销量
"""
import asyncio
from playwright.async_api import async_playwright

from config import USER_DATA_DIR
from utils import parse_likes
from platforms.base import BasePlatform


class TaobaoPlatform(BasePlatform):
    NAME = "淘宝"
    ID   = "taobao"
    ICON = "🛒"

    async def fetch(self, keyword: str, max_count: int) -> list[dict]:
        results = []
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR + "_taobao",
                headless=False,
                channel="msedge",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            await page.goto(
                f"https://s.taobao.com/search?q={keyword}&sort=sale-desc"
            )
            await asyncio.sleep(8)

            # 动态滚动，够数量就停
            for _ in range(50):
                _cur = await page.query_selector_all(".item.J_MouserOnverReq, [data-item-id], .m-itemlist .item")
                if len(_cur) >= max_count:
                    break
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(2)

            items = await page.query_selector_all(
                ".item.J_MouserOnverReq, [data-item-id], .m-itemlist .item"
            )

            items = items[:max_count]  # 截取到指定数量

            for index, item in enumerate(items):
                try:
                    # 商品名
                    title_el = await item.query_selector(
                        ".title, .item-title, [data-spm='title'] a"
                    )
                    title = await title_el.inner_text() if title_el else f"item_{index}"
                    title = title.strip()[:50]

                    # 销量当点赞
                    sale_el = await item.query_selector(
                        ".deal-cnt, .sale-count, .realSales"
                    )
                    sale_count = "0"
                    if sale_el:
                        sale_count = (await sale_el.inner_text()).strip()
                        sale_count = sale_count.replace("人付款", "").replace("已售", "").strip()

                    # 商品主图
                    img_el = await item.query_selector(
                        ".pic img, .item-pic img, img.main-pic"
                    )
                    img_url = ""
                    if img_el:
                        img_url = (
                                await img_el.get_attribute("src") or
                                await img_el.get_attribute("data-src") or ""
                        )
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url

                    # 商品链接
                    link_el = await item.query_selector(".pic a, a.item-click-target")
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
                            "likes":        sale_count,
                            "likes_int":    parse_likes(sale_count),
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
