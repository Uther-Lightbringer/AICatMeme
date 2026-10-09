"""
image_assets.py — 静态图片素材支持（AICatMeme 集成层）

原版 AICatMeme 只认 `meme/<英文情绪名>/frames/*.png` 这种「成品序列帧」素材，
用户扔一张 PNG/JPG 进去没法用。

本模块解决的问题：**让用户直接放静态图片，项目自动把它变成会动的序列帧。**

用法（两种素材布局都支持）：

1. 单图角色（推荐，最省事）：
       image_assets/<角色名>/<表情>.png
   例如 image_assets/chen/blank.png、image_assets/chen/anxious.png
   角色名可以是中文（阿尘）也可以是英文。

2. 多帧角色（用户自己切好帧）：
       image_assets/<角色名>/<表情>/0001.png, 0002.png ...
   已存在的序列帧会原样使用，不做任何处理。

3. 全局共用角色（不区分表情，一个名字对应一张图）：
       image_assets/<角色名>.png

设计要点：
- **磁盘友好**：生成的序列帧默认 540×540（场景中最多放大到约 620px，够用），
  比 1080 原图省 4× 空间（服务器常年 95%+ 磁盘占用）。
- **缓存**：同一张图 + 同一组动画参数只生成一次，第二次直接复用。
- **动画**：正弦"呼吸"微动（上下浮动 + 左右轻摆 + 轻微缩放），
  首尾帧数值一致，循环播放无缝。静态图不会是一张死图。
"""

import os
import glob
import math
import hashlib

# 素材根目录（相对项目根）
ASSET_DIRNAME = "image_assets"

# 生成帧的边长（正方形）。场景里最大显示约 620px，540 足够且省磁盘。
SPRITE_SIZE = 540

# 动画参数
DEFAULT_FRAMES = 150          # 每个表情序列的帧数（150 帧 = 5 秒 @30fps）
BOB_AMPLITUDE = 16            # 上下浮动幅度（像素）
SWAY_AMPLITUDE = 8            # 左右摇摆幅度（像素）
SCALE_AMPLITUDE = 0.014       # 呼吸缩放幅度（±1.4%）


def _asset_root():
    """素材根目录绝对路径（项目根/image_assets）"""
    from core.config import ROOT_DIR
    return os.path.join(ROOT_DIR, ASSET_DIRNAME)


def _safe_name(name):
    """角色/表情名做文件系统安全化（保留中文，去掉路径分隔符等）"""
    bad = ['/', '\\', '..', '\x00', ':', '*', '?', '"', '<', '>', '|']
    out = name
    for b in bad:
        out = out.replace(b, '_')
    return out.strip() or '_'


def is_image_asset(name):
    """判断某个 emotion 字段值是否指向图片素材库（存在同名目录或图片文件）"""
    root = _asset_root()
    if not os.path.isdir(root):
        return False
    safe = _safe_name(name)
    if os.path.isdir(os.path.join(root, safe)):
        return True
    for ext in ('.png', '.jpg', '.jpeg', '.webp', '.PNG', '.JPG', '.JPEG'):
        if os.path.exists(os.path.join(root, safe + ext)):
            return True
    return False


def _source_image(role, emotion):
    """
    定位源图片。返回 (kind, payload)：
      ('seq', frames_list)  —— 已经是序列帧
      ('img', 图片路径)      —— 单张静态图
      (None, None)          —— 找不到
    """
    root = _asset_root()
    role_s = _safe_name(role)
    emo_s = _safe_name(emotion)

    # 1) image_assets/<role>/<emotion>/ 目录 → 序列帧
    seq_dir = os.path.join(root, role_s, emo_s)
    seq = sorted(glob.glob(os.path.join(seq_dir, "*.png"))) + \
        sorted(glob.glob(os.path.join(seq_dir, "*.jpg")))
    if seq:
        return ('seq', seq)

    # 2) image_assets/<role>/<emotion>.(png|jpg|...) → 单图
    for ext in ('.png', '.jpg', '.jpeg', '.webp', '.PNG', '.JPG'):
        p = os.path.join(root, role_s, emo_s + ext)
        if os.path.exists(p):
            return ('img', p)

    # 3) image_assets/<role>/ 下只有一张图 → 就用它（不区分表情的简易模式）
    role_dir = os.path.join(root, role_s)
    if os.path.isdir(role_dir):
        imgs = sorted(glob.glob(os.path.join(role_dir, "*.png"))) + \
            sorted(glob.glob(os.path.join(role_dir, "*.jpg"))) + \
            sorted(glob.glob(os.path.join(role_dir, "*.webp")))
        if imgs:
            return ('img', imgs[0])

    # 4) image_assets/<emotion>.(png|jpg) → 全局单图（role 名即文件名）
    for ext in ('.png', '.jpg', '.jpeg', '.webp'):
        p = os.path.join(root, role_s + ext)
        if os.path.exists(p):
            return ('img', p)

    return (None, None)


def _cache_key(src_path, n_frames):
    """缓存键 = 源文件内容哈希 + 动画参数"""
    h = hashlib.md5()
    try:
        with open(src_path, 'rb') as f:
            h.update(f.read())
    except Exception:
        h.update(src_path.encode('utf-8'))
    h.update(f"|{n_frames}|{BOB_AMPLITUDE}|{SWAY_AMPLITUDE}|{SCALE_AMPLITUDE}".encode())
    return h.hexdigest()[:16]


def _animate(src_path, out_dir, n_frames=DEFAULT_FRAMES):
    """把单张静态图生成为「呼吸浮动」序列帧，写入 out_dir。"""
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)

    im = Image.open(src_path)
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    # 统一缩放到 SPRITE_SIZE 正方形画布（等比缩放后居中，不拉伸变形）
    w0, h0 = im.size
    scale0 = SPRITE_SIZE / max(w0, h0)
    nw0, nh0 = max(1, round(w0 * scale0)), max(1, round(h0 * scale0))
    base = im.resize((nw0, nh0), Image.LANCZOS)

    # 预生成缩放变体（避免每帧重复 resize，1080 图上这是性能杀手）
    variants = {}
    for k in range(-8, 9):
        sc = 1.0 + k * (SCALE_AMPLITUDE / 8)
        variants[k] = base.resize((max(1, int(nw0 * sc)), max(1, int(nh0 * sc))),
                                  Image.BILINEAR)

    canvas_size = SPRITE_SIZE
    for i in range(n_frames):
        t = i / n_frames
        k = int(round(8 * math.sin(2 * math.pi * t)))
        sway = int(SWAY_AMPLITUDE * math.sin(2 * math.pi * t * 2))
        bob = int(BOB_AMPLITUDE * math.sin(2 * math.pi * t))
        im2 = variants[k]
        nw, nh = im2.size
        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        # 原图在画布内居中，再叠加上浮动偏移
        cx = (canvas_size - nw) // 2 + sway
        cy = (canvas_size - nh) // 2 + bob
        # 若偏移导致越界，裁剪到画布内的部分再贴（保护画布不崩）
        if cx >= 0 and cy >= 0:
            canvas.alpha_composite(im2, (cx, cy))
        else:
            sx = -cx if cx < 0 else 0
            sy = -cy if cy < 0 else 0
            cropped = im2.crop((sx, sy, nw, nh))
            canvas.alpha_composite(cropped, (max(0, cx), max(0, cy)))
        canvas.save(os.path.join(out_dir, f"{i + 1:04d}.png"))
    return n_frames


def resolve_assets(role, emotion, n_frames=DEFAULT_FRAMES):
    """
    对外主入口：给定角色名 + 表情名，返回可用帧序列的**绝对路径列表**。

    - 已是序列帧 → 原样返回
    - 单张静态图 → 生成/复用缓存的动画序列后返回
    - 找不到 → 抛 FileNotFoundError（由上层决定是否回落）
    """
    kind, payload = _source_image(role, emotion)
    if kind is None:
        raise FileNotFoundError(f"图片素材库中找不到：角色='{role}' 表情='{emotion}'")

    if kind == 'seq':
        return payload

    # 单图 → 动画化 + 缓存
    src = payload
    key = _cache_key(src, n_frames)
    cache_dir = os.path.join(_asset_root(), ".cache", key)
    frames = sorted(glob.glob(os.path.join(cache_dir, "*.png")))
    if len(frames) == n_frames:
        return frames
    _animate(src, cache_dir, n_frames)
    return sorted(glob.glob(os.path.join(cache_dir, "*.png")))


def list_roles():
    """列出素材库里所有角色名（供 UI / 调试用）"""
    root = _asset_root()
    if not os.path.isdir(root):
        return []
    out = []
    for name in sorted(os.listdir(root)):
        if name.startswith('.'):
            continue
        p = os.path.join(root, name)
        if os.path.isdir(p):
            out.append(name)
        elif os.path.splitext(name)[1].lower() in ('.png', '.jpg', '.jpeg', '.webp'):
            out.append(os.path.splitext(name)[0])
    return out
