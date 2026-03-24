"""
crop_photos.py
智能裁剪工具 — 将已下载的图片裁剪为5寸和7寸打印尺寸
双击运行即可，无需额外安装依赖

尺寸说明（300 DPI 打印分辨率）：
  5寸 (3R)  89×127mm  →  1051×1500 px
  7寸 (5R)  127×178mm →  1500×2102 px
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageFilter

# ── 打印尺寸配置（宽×高，单位 px，300DPI）──────────
SIZES = {
    "5寸": (1051, 1500),
    "7寸": (1500, 2102),
}

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def get_energy_map(img: Image.Image) -> list:
    """用 Pillow 内置滤镜计算图片各列/行的边缘能量"""
    gray = img.convert("L").filter(ImageFilter.FIND_EDGES)
    w, h = gray.size
    pixels = gray.load()

    col_energy = [0] * w
    row_energy = [0] * h

    for x in range(w):
        for y in range(h):
            v = pixels[x, y]
            col_energy[x] += v
            row_energy[y] += v

    return col_energy, row_energy


def sliding_window_max(energy: list, window: int) -> int:
    """滑动窗口找能量最大的起始位置"""
    total = len(energy)
    if total <= window:
        return 0

    cur = sum(energy[:window])
    best_val = cur
    best_idx = 0

    for i in range(1, total - window + 1):
        cur = cur - energy[i - 1] + energy[i + window - 1]
        if cur > best_val:
            best_val = cur
            best_idx = i

    return best_idx


def smart_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    智能裁剪：
    1. 等比缩放，使图片刚好覆盖目标尺寸
    2. 用边缘能量检测内容最密集区域
    3. 以内容中心为基准裁剪
    """
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio    = src_w / src_h

    if src_ratio > target_ratio:
        scale = target_h / src_h
    else:
        scale = target_w / src_w

    new_w = max(int(src_w * scale), target_w)
    new_h = max(int(src_h * scale), target_h)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    col_energy, row_energy = get_energy_map(img)

    crop_x = sliding_window_max(col_energy, target_w)
    crop_y = sliding_window_max(row_energy, target_h)

    # 限制在合法范围
    crop_x = min(crop_x, new_w - target_w)
    crop_y = min(crop_y, new_h - target_h)

    cropped = img.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))
    if cropped.size != (target_w, target_h):
        cropped = cropped.resize((target_w, target_h), Image.LANCZOS)
    return cropped


def crop_folder(src_dir: str):
    src_path = Path(src_dir)
    if not src_path.exists():
        print(f"[错误] 文件夹不存在：{src_dir}")
        return

    img_files = [f for f in src_path.rglob("*") if f.suffix.lower() in IMG_EXTS]

    # 排除已生成的 5寸/7寸 子目录
    img_files = [f for f in img_files if f.parent.name not in SIZES]

    if not img_files:
        print(f"[提示] 没有找到图片：{src_dir}")
        return

    total = len(img_files)
    print(f"\n找到 {total} 张图片，开始裁剪...\n")

    ok = fail = skip = 0
    for i, img_path in enumerate(img_files, 1):
        print(f"[{i}/{total}] {img_path.name}", end="  ")
        try:
            img = Image.open(img_path).convert("RGB")
            any_done = False

            for size_name, (tw, th) in SIZES.items():
                out_dir = img_path.parent / size_name
                out_dir.mkdir(exist_ok=True)
                out_path = out_dir / (img_path.stem + ".jpg")

                if out_path.exists():
                    continue

                cropped = smart_crop(img, tw, th)
                cropped.save(
                    out_path, "JPEG",
                    quality=95,
                    dpi=(300, 300),
                    subsampling=0,
                )
                any_done = True

            if any_done:
                print("✓")
                ok += 1
            else:
                print("已跳过（已裁剪过）")
                skip += 1

        except Exception as e:
            print(f"✗  {e}")
            fail += 1

    print(f"\n完成！成功 {ok} 张，跳过 {skip} 张，失败 {fail} 张")
    print(f"裁剪结果保存在各日期文件夹下的 5寸/ 和 7寸/ 子目录")


if __name__ == "__main__":
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()

    folder = filedialog.askdirectory(
        title="选择要裁剪的图片文件夹（选择下载根目录即可）"
    )

    if not folder:
        sys.exit(0)

    print(f"目标文件夹：{folder}")
    print(f"裁剪尺寸：5寸 {SIZES['5寸']}px  7寸 {SIZES['7寸']}px  @ 300DPI")

    crop_folder(folder)

    messagebox.showinfo(
        "裁剪完成",
        f"裁剪完成！\n\n"
        f"结果保存在所选文件夹下的：\n"
        f"  📁 5寸/\n"
        f"  📁 7寸/\n\n"
        f"分辨率：300 DPI，可直接送打印店"
    )
