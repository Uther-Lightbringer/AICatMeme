#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_ref_style.py — 完全参照「猫meme日记」参考图风格的渲染器

参考图特征（逐像素取样确认）：
  · 名字：亮黄填充 #F8E225 + 黑色粗描边，紧贴猫头下方
  · 台词：白字 + 黑描边，位于画面上方（约顶部15%）
  · 无任何半透明底框/黑底条
  · 字很大：字高约占画面高度 11~12%
  · 猫很小：角色占画面高度 35~45%，坐在中下部
  · 横屏 16:9 为主，方形 1:1 亦可

用法：
  python3 render_ref_style.py            # 方形 1080x1080
  python3 render_ref_style.py --land      # 横屏 1920x1080
"""
import sys, os, glob, tempfile, argparse, subprocess
sys.path.insert(0, "/opt/AICatMeme")
os.chdir("/opt/AICatMeme")

from core.config import EMOTION_FOLDER, BG_FOLDER, FONT_PATH

# 用 Black(900) 字重做加粗效果；缺失时回落到原字体
FONT_BOLD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "NotoSansSC_Black.ttf")
if not os.path.exists(FONT_BOLD):
    FONT_BOLD = FONT_PATH
from core.text_style import STYLE_REF, STYLE_REF_WHITE, text_layers
from utils.draw_utils import wrap_text
import imageio_ffmpeg

FFMPEG = "/opt/ffmpeg-bin/ffmpeg" if os.path.exists("/opt/ffmpeg-bin/ffmpeg") else imageio_ffmpeg.get_ffmpeg_exe()

def ffp(p):
    return p.replace('\\', '/').replace(':', '\\:')

def wf(d, name, text):
    fp = os.path.join(d, name)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(text)
    return ffp(fp)

# ---------- 参照比例（相对画面高度） ----------
NAME_SIZE_RATIO = 0.115   # 名字字高 ≈ 11.5% 画面高
DIA_SIZE_RATIO  = 0.115   # 台词字高 ≈ 11.5% 画面高
CAT_HEIGHT_RATIO = 0.52   # 猫占画面高度 ≈ 52%（放大）
DIA_TOP_RATIO   = 0.10    # 台词顶端 ≈ 10% 画面高（上方）
CAT_BOTTOM_RATIO = 0.88   # 猫底 ≈ 88% 画面高（下方留一点）

SCENES = [
    {"place": "home",     "chars": [("前女友猫", "disdain",   "十年之期已到，退婚！"),
                                     ("废柴猫",   "pitiful",   "莫欺少年穷……")]},
    {"place": "forest",   "chars": [("废柴猫",   "astonished", "石缝里竟有金光？！")]},
    {"place": "rooftop",  "chars": [("废柴猫",   "striving",   "熬个通宵，居然筑基了？")]},
    {"place": "stage",    "chars": [("对手猫",   "showoff",    "筑基也配上台？"),
                                     ("废柴猫",   "smirk",      "一招，够了。")]},
    {"place": "theater",  "chars": [("长老猫",   "shocked",    "此子竟已结丹？！"),
                                     ("废柴猫",   "majestic",   "晚辈侥幸而已。")]},
    {"place": "shop",     "chars": [("富豪猫",   "disdain",    "穷猫也敢竞宝？"),
                                     ("废柴猫",   "laughing",   "这摊，我全包了。")]},
    {"place": "Mountain", "chars": [("废柴猫",   "painful",    "天劫？正好给我淬体！")]},
    {"place": "village",  "chars": [("废柴猫",   "brave",      "一猫，当关。")]},
    {"place": "fantacy",  "chars": [("废柴猫",   "cheering",   "十日，我成神了！")]},
    {"place": "stage",    "chars": [("废柴猫",   "showoff",    "十日成神，下一部演赘婿")]},
]

def frames_of(emotion):
    d = os.path.join(EMOTION_FOLDER, emotion, "frames")
    fs = sorted(glob.glob(os.path.join(d, "*.png")))
    if fs:
        return fs, os.path.join(EMOTION_FOLDER, emotion, "audio.mp3")
    # 兜底
    for fb in ("blank", "happy"):
        d2 = os.path.join(EMOTION_FOLDER, fb, "frames")
        fs2 = sorted(glob.glob(os.path.join(d2, "*.png")))
        if fs2:
            return fs2, os.path.join(EMOTION_FOLDER, fb, "audio.mp3")
    raise FileNotFoundError(f"无情绪帧: {emotion}")

def render(landscape=False, out="/opt/AICatMeme/output/shiri_ref.mp4"):
    W, H = (1920, 1080) if landscape else (1080, 1080)
    name_size = int(H * NAME_SIZE_RATIO)
    dia_size = int(H * DIA_SIZE_RATIO)
    cat_h = int(H * CAT_HEIGHT_RATIO)
    dia_y0 = int(H * DIA_TOP_RATIO)
    cat_bottom = int(H * CAT_BOTTOM_RATIO)

    tmp = tempfile.mkdtemp(prefix="refstyle_")
    scene_files = []

    for si, sc in enumerate(SCENES):
        bgs = glob.glob(os.path.join(BG_FOLDER, f"{sc['place']}.*"))
        if not bgs:
            raise FileNotFoundError(f"背景缺失: {sc['place']}")
        bg = bgs[0]
        bg_is_img = bg.lower().endswith(('.png', '.jpg', '.jpeg'))

        chars = []
        for (nm, emo, txt) in sc["chars"]:
            fs, au = frames_of(emo)
            chars.append(dict(name=nm, emo=emo, text=txt, frames=fs, audio=au))

        # 每只猫的时长
        for c in chars:
            c["dur"] = max(2.6, len(c["frames"]) / 30.0)
        total = max(c["dur"] for c in chars) + 0.6

        n = len(chars)
        # 横向站位：把猫排在中下部，等分但留边距
        slot = W / n
        cat_w = int(cat_h)  # 素材是正方形，等比

        cmd = [FFMPEG, "-y"]
        if bg_is_img:
            cmd += ["-loop", "1", "-framerate", "24", "-i", bg]
        else:
            cmd += ["-stream_loop", "-1", "-i", bg]

        # 逐层 overlay：从 bg 开始，依次叠加每只猫
        filters = []
        texts = []
        filters.append(f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,trim=duration={total}[bgv]")
        prev = "bgv"
        input_idx = 1
        for i, c in enumerate(chars):
            d = os.path.dirname(c["frames"][0])
            st = int(os.path.basename(c["frames"][0]).split('.')[0])
            pat = os.path.join(d, "%04d.png")
            cmd += ["-framerate", "30", "-start_number", str(st), "-i", pat]
            vidx = input_idx; input_idx += 1
            if c["audio"] and os.path.exists(c["audio"]):
                cmd += ["-i", c["audio"]]
            else:
                cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
            aidx = input_idx; input_idx += 1

            cx = int(slot * i + slot / 2)
            ox = int(cx - cat_w / 2)
            oy = cat_bottom - cat_h

            nf = len(c["frames"])
            # 先裁掉四周空白（猫在方形帧里偏下、只占约46%高），再等比缩放到目标高度
            # 裁右下偏中的内容区，使可见的猫真正占满目标高度
            filters.append(
                f"[{vidx}:v]crop=iw*0.66:ih*0.62:iw*0.17:ih*0.36,"
                f"scale=-1:{cat_h},setsar=1,loop=loop=-1:size={nf}:start=0,fps=30,"
                f"trim=duration={total},setpts=PTS-STARTPTS[catseq{i}]")
            bob = "8*sin(2*PI*t/2.5)"
            filters.append(
                f"[{prev}][catseq{i}]overlay=x={ox}:y='{oy}+{bob}':enable='between(t,0,{total})'[v{i}]")
            prev = f"v{i}"

            # 音频混入
            filters.append(f"[{aidx}:a]atrim=duration={total},asetpts=PTS-STARTPTS[aud{i}]")

        # ---- 文字（参照图：名字=黄+黑边 贴猫头下沿；台词=白+黑边 顶部左对齐堆叠） ----
        # 注意：drawtext 是视频滤镜，必须串进视频链，不能并列成独立 filter
        # 名字：逐只猫，居中贴在其正下方
        text_chain = []
        for i, c in enumerate(chars):
            cx = int(slot * i + slot / 2)
            name_y = cat_bottom + int(H * 0.005)
            nm_txt = wf(tmp, f"nm_{si}_{i}.txt", c["name"])
            for layer in text_layers(STYLE_REF, ffp(FONT_BOLD), nm_txt,
                                     f"{cx}-text_w/2", name_y, name_size,
                                     enable=f"between(t,0,{total})"):
                text_chain.append(layer)

        # 台词：像参考图那样，在顶部左侧竖向堆叠（所有角色的台词合成一段）
        # 按字号估算每行最大字数，避免超出画面宽度
        max_chars = max(4, int(W * 0.88 / dia_size))
        all_lines = []
        for c in chars:
            all_lines.extend(wrap_text(c["text"], max_chars).split("\n"))
        dia_body = "\n".join(all_lines)
        dia_txt = wf(tmp, f"dia_{si}.txt", dia_body)
        for layer in text_layers(STYLE_REF_WHITE, ffp(FONT_BOLD), dia_txt,
                                 f"{int(W*0.05)}", dia_y0, dia_size,
                                 enable=f"between(t,0,{total})",
                                 extra=f":line_spacing={int(dia_size*0.35)}"):
            text_chain.append(layer)

        # 把文字链接到视频链尾部
        if text_chain:
            filters.append(f"[{prev}]" + ",".join(text_chain) + "[vtext]")
            prev = "vtext"

        # 音频合并
        a_inputs = "".join(f"[aud{i}]" for i in range(len(chars)))
        if len(chars) > 1:
            filters.append(f"{a_inputs}amix=inputs={len(chars)}:duration=longest[aout]")
        else:
            filters.append("[aud0]acopy[aout]")

        filter_complex = ";".join(filters)
        out_scene = os.path.join(tmp, f"scene_{si}.mp4")
        cmd += ["-filter_complex", filter_complex, "-map", f"[{prev}]", "-map", "[aout]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                "-c:a", "aac", "-shortest", out_scene]
        print(f"🎬 场景 {si+1}/{len(SCENES)}: {sc['place']}")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-2500:])
            raise SystemExit(f"场景 {si+1} 渲染失败")
        scene_files.append(out_scene)

    # 拼接
    concat_txt = os.path.join(tmp, "concat.txt")
    with open(concat_txt, "w", encoding='utf-8') as f:
        for sf in scene_files:
            f.write(f"file '{sf}'\n")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt,
                    "-c", "copy", out], check=True)
    print("✅ 完成:", out)
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--land", action="store_true")
    ap.add_argument("--out", default="/opt/AICatMeme/output/shiri_ref.mp4")
    a = ap.parse_args()
    render(landscape=a.land, out=a.out)
