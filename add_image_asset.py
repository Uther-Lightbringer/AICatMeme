#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_image_asset.py — 往图片素材库添加素材的辅助脚本

用法：
    # 单图角色（最常用）：一张图 = 一个表情
    python3 add_image_asset.py --role 阿尘 --emotion blank --image /path/to/head.png
    # 同一个角色的多张图 = 多个表情
    python3 add_image_asset.py --role 阿尘 --emotion anxious --image /path/a.png
    python3 add_image_asset.py --role 阿尘 --emotion majestic --image /path/b.png

    # 不区分表情：一个角色只放一张图（之后 emotion 可随便填，都会用它）
    python3 add_image_asset.py --role 老猫 --image /path/old.png

    # 已经是序列帧（用户自己切好）：
    python3 add_image_asset.py --role 阿尘 --emotion run --frames /path/seq_dir/

    # 查看现有素材库
    python3 add_image_asset.py --list

素材落地位置：
    image_assets/<role>/<emotion>.png            # 单图（会自动动画化）
    image_assets/<role>/<emotion>/0001.png ...   # 序列帧（原样使用）
    image_assets/<role>.png                      # 全局单图
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.image_assets import _asset_root, _safe_name, list_roles


def main():
    ap = argparse.ArgumentParser(description="AICatMeme 图片素材库管理")
    ap.add_argument("--role", help="角色名（中文/英文均可）")
    ap.add_argument("--emotion", default="", help="表情名（不填则作为该角色的默认图）")
    ap.add_argument("--image", help="单张图片路径（png/jpg/webp）")
    ap.add_argument("--frames", help="序列帧目录（目录下的 png 会被原样使用）")
    ap.add_argument("--list", action="store_true", help="列出当前素材库角色")
    args = ap.parse_args()

    root = _asset_root()
    os.makedirs(root, exist_ok=True)

    if args.list:
        roles = list_roles()
        if not roles:
            print(f"素材库为空（{root}）")
            return
        print(f"素材库：{root}")
        for r in roles:
            p = os.path.join(root, r)
            if os.path.isdir(p):
                items = sorted(os.listdir(p))
                print(f"  {r}/  → {items}")
            else:
                print(f"  {r}  (单图)")
        return

    if not args.role:
        ap.error("需要 --role（或用 --list 查看素材库）")

    role_s = _safe_name(args.role)
    emo_s = _safe_name(args.emotion) if args.emotion else ""

    if args.frames:
        # 序列帧：复制到 image_assets/<role>/<emotion>/
        if not emo_s:
            ap.error("序列帧模式需要 --emotion")
        dst = os.path.join(root, role_s, emo_s)
        os.makedirs(dst, exist_ok=True)
        srcs = sorted(
            [os.path.join(args.frames, f) for f in os.listdir(args.frames)
             if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        )
        if not srcs:
            ap.error(f"目录里没有图片：{args.frames}")
        for i, s in enumerate(srcs, 1):
            ext = os.path.splitext(s)[1].lower()
            shutil.copy(s, os.path.join(dst, f"{i:04d}{ext}"))
        print(f"✅ 已添加序列帧 {len(srcs)} 张 → {dst}")
        return

    if not args.image:
        ap.error("需要 --image 或 --frames")

    if not os.path.exists(args.image):
        ap.error(f"图片不存在：{args.image}")

    if emo_s:
        dst = os.path.join(root, role_s, emo_s + os.path.splitext(args.image)[1].lower())
    else:
        dst = os.path.join(root, role_s + os.path.splitext(args.image)[1].lower())
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(args.image, dst)
    print(f"✅ 已添加：{dst}")
    print("   渲染时用：{\"char\": \"%s\", \"emotion\": \"%s\"}" % (role_s, emo_s or "(任意)"))


if __name__ == "__main__":
    main()
