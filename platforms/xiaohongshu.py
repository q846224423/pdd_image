"""
platforms/xiaohongshu.py
小红书爬虫 — 进详情页抓全部图片
"""
import asyncio
from playwright.async_api import async_playwright

from config import USER_DATA_DIR
from utils import parse_likes, url_hash
from platforms.base import BasePlatform


class XiaohongshuPlatform(BasePlatform):
    NAME = "小红书"
    ID   = "xiaohongshu"
    ICON = "📕"

    async def fetch(self, keyword: str, max_count: int, db: dict = None) -> list[dict]:
        db = db or {}
        results = []
        seen_urls = set()

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                channel="msedge",
                viewport={"width": 1280, "height": 720}
            )

            # ── 第一步：搜索结果页收集帖子基本信息 ──
            search_page = await context.new_page()
            await search_page.goto(
                f"https://www.xiaohongshu.com/search_result?keyword={keyword}"
            )
            await asyncio.sleep(8)

            notes_info = []   # 收集帖子列表

            for scroll_i in range(50):
                notes = await search_page.query_selector_all("section.note-item")

                for note in notes:
                    try:
                        # 先用封面 URL 做快速去重判断
                        img_el = await note.query_selector("a.cover img")
                        if not img_el:
                            continue
                        cover_url = await img_el.get_attribute("src") or ""
                        if not cover_url:
                            continue
                        if cover_url.startswith("//"):
                            cover_url = "https:" + cover_url

                        cover_hash = url_hash(cover_url)
                        if cover_hash in seen_urls:
                            continue
                        seen_urls.add(cover_hash)

                        # 帖子链接
                        link_el = await note.query_selector("a.cover")
                        note_url = ""
                        if link_el:
                            href = await link_el.get_attribute("href") or ""
                            note_url = (
                                "https://www.xiaohongshu.com" + href
                                if href.startswith("/") else href
                            )

                        if not note_url:
                            continue

                        # 标题、点赞、评论
                        title_el = await note.query_selector(".title span")
                        title = (await title_el.inner_text()).strip() if title_el else ""

                        like_el = await note.query_selector(".like-wrapper span.count")
                        like_count = await like_el.inner_text() if like_el else "0"

                        comment_el = await note.query_selector(".comments-wrapper span.count")
                        comment_count = await comment_el.inner_text() if comment_el else "0"

                        time_el = await note.query_selector(
                            ".time-wrapper span, .note-item-top .time, span.time"
                        )
                        publish_time = ""
                        if time_el:
                            publish_time = (await time_el.inner_text()).strip()

                        notes_info.append({
                            "title":        title,
                            "likes":        like_count,
                            "likes_int":    parse_likes(like_count),
                            "comments":     comment_count,
                            "cover_url":    cover_url,
                            "note_url":     note_url,
                            "publish_time": publish_time,
                        })

                    except Exception:
                        continue

                # 收集够足够的帖子（多收一些，进详情页后图片会更多）
                if len(notes_info) >= max_count:
                    break

                await search_page.mouse.wheel(0, 2000)
                await asyncio.sleep(2.5)

            await search_page.close()

            # ── 第二步：逐个进详情页抓全部图片 ──
            detail_page = await context.new_page()

            for note_data in notes_info:
                if len(results) >= max_count:
                    break

                try:
                    await detail_page.goto(note_data["note_url"], timeout=15000)
                    await asyncio.sleep(3)

                    # 抓详情页内所有图片
                    # 小红书详情页图片常见选择器
                    img_urls = []
                    for sel in [
                        ".swiper-slide img",
                        ".image-view img",
                        ".note-slider img",
                        ".carousel img",
                        "div.swiper img",
                        ".media-container img",
                    ]:
                        els = await detail_page.query_selector_all(sel)
                        if els:
                            for el in els:
                                src = (
                                        await el.get_attribute("src") or
                                        await el.get_attribute("data-src") or ""
                                )
                                if src:
                                    if src.startswith("//"):
                                        src = "https:" + src
                                    if src not in img_urls:
                                        img_urls.append(src)
                            if img_urls:
                                break

                    # 如果详情页没抓到，至少用封面
                    if not img_urls:
                        img_urls = [note_data["cover_url"]]

                    # 每张图作为独立条目
                    total_imgs = len(img_urls)
                    for i, img_url in enumerate(img_urls):
                        h = url_hash(img_url)

                        # 跳过已下载
                        if h in db:
                            continue

                        # 多张图时标题加序号
                        title = note_data["title"]
                        if total_imgs > 1:
                            title = f"{title} ({i+1}/{total_imgs})"

                        results.append({
                            "title":        title,
                            "likes":        note_data["likes"],
                            "likes_int":    note_data["likes_int"],
                            "comments":     note_data["comments"],
                            "url":          img_url,
                            "note_url":     note_data["note_url"],
                            "publish_time": note_data["publish_time"],
                            "platform":     self.ID,
                        })

                        if len(results) >= max_count:
                            break

                except Exception:
                    # 进详情页失败，用封面兜底
                    cover_url = note_data["cover_url"]
                    h = url_hash(cover_url)
                    if h not in db:
                        results.append({
                            "title":        note_data["title"],
                            "likes":        note_data["likes"],
                            "likes_int":    note_data["likes_int"],
                            "comments":     note_data["comments"],
                            "url":          cover_url,
                            "note_url":     note_data["note_url"],
                            "publish_time": note_data["publish_time"],
                            "platform":     self.ID,
                        })
                    continue

            await detail_page.close()
            await context.close()

        return results[:max_count]
