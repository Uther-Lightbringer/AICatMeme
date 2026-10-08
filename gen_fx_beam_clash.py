"""双猫对波特效包：frames/*.png(1080x1080 RGBA) + audio.wav
时间轴(30fps, 75帧=2.5s):
  0-14帧   充能: 左右猫口/爪前光点渐亮, 粒子内吸
  15-30帧  释放: 两道水平光束对射(左蓝右金), 逐渐增粗
  31-56帧  碰撞: 中点白闪→3层金环扩散→12条放射光→30粒子四溅
  57-74帧  余波: 环与粒子渐暗
适配 dialogue 布局(左猫中心x=290, 右猫x=790, 波口高度y=470)
"""
import os, math, random, wave, struct
from PIL import Image, ImageDraw, ImageFilter

ROOT = "/opt/AICatMeme/fx/beam_clash"
FRAMES_DIR = os.path.join(ROOT, "frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

W = H = 1080
FPS = 30
N = 75
LX, RX, Y = 290, 790, 470   # 左猫口/右猫口/波高度

random.seed(42)

def glow_draw(base, draw_fn, blur=18, core=True, alpha=255):
    """draw_fn在透明层上画形状 → 高斯模糊发光层 + 实心亮核 双层叠加"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    draw_fn(d)
    blurred = layer.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 255:
        blurred.putalpha(blurred.getchannel("A").point(lambda a: int(a * alpha / 255)))
    base.alpha_composite(blurred)
    if core:
        base.alpha_composite(layer)
    return base

def lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))

def ease_out(t):
    return 1 - (1 - t) ** 2

# 粒子系统(爆炸时初始化)
particles = []

def render_frame(f):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    t = f / FPS

    # ---------- 阶段1: 充能 (0 - 0.5s) ----------
    if t < 0.5:
        p = t / 0.5
        r = int(lerp(6, 34, ease_out(p)))
        for cx, col in [(LX, (90, 180, 255)), (RX, (255, 190, 80))]:
            glow_draw(img, lambda dd, cx=cx, r=r, col=col: dd.ellipse(
                [cx - r, Y - r, cx + r, Y + r], fill=col + (255,)), blur=26)
        # 吸入粒子
        for i in range(10):
            ang = random.uniform(0, 2 * math.pi)
            dist = lerp(150, 40, p)
            side = LX if i % 2 == 0 else RX
            col = (90, 180, 255) if i % 2 == 0 else (255, 190, 80)
            px_, py_ = side + math.cos(ang) * dist, Y + math.sin(ang) * dist * 0.6
            d.ellipse([px_ - 4, py_ - 4, px_ + 4, py_ + 4], fill=col + (200,))

    # ---------- 阶段2: 光束对射 (0.5 - 1.0s) ----------
    elif t < 1.0:
        p = (t - 0.5) / 0.5
        mid = (LX + RX) // 2
        half = int(lerp(60, (mid - LX) * 0.95, ease_out(p)))
        for x0, x1, col in [(LX, LX + half, (90, 180, 255)), (RX, RX - half, (255, 190, 80))]:
            def _beam(dd, x0=x0, x1=x1, col=col, p=p):
                wid = int(lerp(10, 56, p))
                dd.line([x0, Y, x1, Y], fill=col + (230,), width=wid)
                dd.line([x0, Y, x1, Y], fill=(255, 255, 255, 220), width=max(8, wid // 2))
                # 流动亮斑
                for k in range(3):
                    bx = int(lerp(x0, x1, (p * 2 + k / 3) % 1.0))
                    dd.ellipse([bx - 16, Y - int(wid*0.45), bx + 16, Y + int(wid*0.45)], fill=(255, 255, 255, 170))
            glow_draw(img, _beam, blur=12)

    # ---------- 阶段3: 碰撞爆炸 (1.0 - 1.9s) ----------
    elif t < 1.9:
        p = (t - 1.0) / 0.9
        cx = (LX + RX) // 2
        if not particles:
            for i in range(30):
                ang = random.uniform(0, 2 * math.pi)
                sp = random.uniform(160, 520)
                particles.append([ang, sp, random.uniform(4, 9),
                                  random.choice([(90, 180, 255), (255, 190, 80), (255, 255, 255), (255, 120, 60)])])
        # 白闪(前3帧)
        if p < 0.12:
            flash = Image.new("RGBA", (W, H), (255, 255, 255, int(235 * (1 - p / 0.12))))
            img.alpha_composite(flash)
        # 3层冲击环
        for layer_i in range(3):
            delay = layer_i * 0.08
            pp = (p - delay) / (1 - delay)
            if pp <= 0: continue
            r = int(10 + 460 * ease_out(pp))
            wid = int(lerp(26, 4, pp))
            a = int(lerp(255, 0, pp) * (1 - layer_i * 0.18))
            col = [(255, 220, 130), (255, 170, 70), (255, 120, 50)][layer_i]
            glow_draw(img, lambda dd, r=r, wid=wid, col=col, a=a: dd.ellipse(
                [cx - r, Y - r, cx + r, Y + r], outline=col + (a,), width=wid),
                blur=10, core=False)
        # 12条放射光
        for i in range(12):
            ang = i * math.pi / 6 + p * 0.4
            ln = 60 + 340 * ease_out(p)
            x2, y2 = cx + math.cos(ang) * ln, Y + math.sin(ang) * ln
            a = int(220 * (1 - p))
            d.line([cx, Y, x2, y2], fill=(255, 230, 170, a), width=5)
            d.line([cx, Y, x2, y2], fill=(255, 255, 255, a), width=2)
        # 中心亮核
        core_r = int(lerp(60, 130, p))
        glow_draw(img, lambda dd, r=core_r: dd.ellipse(
            [cx - r, Y - r, cx + r, Y + r], fill=(255, 240, 200, int(230 * (1 - p * 0.8)))),
            blur=30, core=False)
        # 粒子
        for ang, sp, size, col in particles:
            dist = sp * p
            px_, py_ = cx + math.cos(ang) * dist, Y + math.sin(ang) * dist + 0.5 * 220 * p * p
            a = int(255 * (1 - p))
            d.ellipse([px_ - size, py_ - size, px_ + size, py_ + size], fill=col + (a,))

    # ---------- 阶段4: 余波 (1.9 - 2.5s) ----------
    else:
        p = (t - 1.9) / 0.6
        cx = (LX + RX) // 2
        r = int(470 + 260 * ease_out(p))
        a = int(140 * (1 - p))
        glow_draw(img, lambda dd, r=r, a=a: dd.ellipse(
            [cx - r, Y - r, cx + r, Y + r], outline=(255, 200, 120, a), width=14),
            blur=24, core=False)
        for ang, sp, size, col in particles:
            dist = sp * 0.9 + sp * 0.1 * p
            px_, py_ = cx + math.cos(ang) * dist, Y + math.sin(ang) * dist + 0.5 * 220 * 0.9 * 0.9
            a = int(180 * (1 - p))
            d.ellipse([px_ - size, py_ - size, px_ + size, py_ + size], fill=col + (a,))
        # 烟尘
        if p < 0.6:
            for i in range(8):
                ang = i * math.pi / 4
                dist = 180 + 90 * p
                sx, sy = cx + math.cos(ang) * dist, Y + math.sin(ang) * dist * 0.5 + 60
                rr = int(30 + 40 * p)
                glow_draw(img, lambda dd, sx=sx, sy=sy, rr=rr, p=p: dd.ellipse(
                    [sx - rr, sy - rr, sx + rr, sy + rr], fill=(200, 200, 200, int(60 * (1 - p)))),
                    blur=20, core=False)

    img.save(os.path.join(FRAMES_DIR, f"{f:04d}.png"))

for f in range(N):
    render_frame(f)
print("frames done:", N)

# ================= 音效: 充能sweep + 爆炸thump+noise =================
SR = 44100
def gen_audio():
    total = int(2.5 * SR)
    buf = [0.0] * total
    # 段1: 0-0.5s 频率sweep 150->700Hz
    for i in range(int(0.5 * SR)):
        t = i / SR
        fq = 150 + 550 * (t / 0.5)
        buf[i] += 0.35 * math.sin(2 * math.pi * fq * t)
    # 段2: 1.0-1.9s 噪声爆发 + 55Hz thump
    import random as _r
    _r.seed(1)
    for i in range(int(0.9 * SR)):
        j = int(1.0 * SR) + i
        t = i / SR
        noise = _r.uniform(-1, 1)
        env_n = math.exp(-6 * t)
        env_t = math.exp(-10 * t)
        buf[j] += 0.7 * noise * env_n + 0.8 * math.sin(2 * math.pi * 55 * t) * env_t
        # 爆点后0.15s加高频碎响
        if t < 0.15:
            buf[j] += 0.4 * noise * math.exp(-30 * t) * math.sin(2 * math.pi * 900 * t)
    # 归一化
    peak = max(abs(v) for v in buf) or 1.0
    buf = [int(v / peak * 30000) for v in buf]
    w = wave.open(os.path.join(ROOT, "audio.wav"), "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(struct.pack("<" + "h" * len(buf), *buf))
    w.close()
    print("audio done")

gen_audio()
