"""
scraper.py
爬虫核心：用 Playwright 驱动 Edge 抓取小红书搜索结果
"""
import asyncio
from playwright.async_api import async_playwright

from config import USER_DATA_DIR
from utils import parse_likes


async def fetch_image_data(keyword: str, scroll_times: int) -> list[dict]:
    """
    抓取小红书搜索关键词的图片数据。

    返回列表，每项：
    {
        "title":        str,
        "likes":        str,   # 原始字符串，如 "1.2万"
        "likes_int":    int,   # 转换后整数
        "comments":     str,
        "url":          str,   # 图片直链
        "note_url":     str,   # 笔记原帖链接
        "publish_time": str,   # 相对时间，如 "3天前"
    }
    """
    images_data = []

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            channel="msedge",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        await page.goto(
            f"https://www.xiaohongshu.com/search_result?keyword={keyword}"
        )
        await asyncio.sleep(8)

        for _ in range(scroll_times):
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(2)

        notes = await page.query_selector_all("section.note-item")

        for index, note in enumerate(notes):
            try:
                title_el = await note.query_selector(".title span")
                title = await title_el.inner_text() if title_el else f"image_{index}"

                like_el = await note.query_selector(".like-wrapper span.count")
                like_count = await like_el.inner_text() if like_el else "0"

                comment_el = await note.query_selector(".comments-wrapper span.count")
                comment_count = await comment_el.inner_text() if comment_el else "0"

                # 相对发布时间（直接从搜索结果页读，不进详情页）
                time_el = await note.query_selector(
                    ".time-wrapper span, .note-item-top .time, span.time"
                )
                publish_time = ""
                if time_el:
                    publish_time = (await time_el.inner_text()).strip()

                link_el = await note.query_selector("a.cover")
                note_url = ""
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href:
                        note_url = (
                            "https://www.xiaohongshu.com" + href
                            if href.startswith("/") else href
                        )

                img_el = await note.query_selector("a.cover img")
                if img_el:
                    img_url = await img_el.get_attribute("src")
                    if img_url:
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url
                        images_data.append({
                            "title":        title,
                            "likes":        like_count,
                            "likes_int":    parse_likes(like_count),
                            "comments":     comment_count,
                            "url":          img_url,
                            "note_url":     note_url,
                            "publish_time": publish_time,
                        })
            except Exception:
                continue

        await context.close()

    return images_data
