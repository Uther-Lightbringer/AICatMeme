"""赛亚人对波 V2: fx/beam_clash/{frames,audio.wav}
时间轴(30fps, 105帧=3.5s), 口位 LX=290/RX=790, 口高 Y=470, 撞点基准 CX=540:
  P1 0-18帧   蓄力: 大口径能量球+吸入粒子+地面微震
  P2 18-30帧  出波: 锥形波(口小->撞点粗)快速冲出
  P3 30-69帧  僵持: 撞点球sin脉动, 蓝金撞点X轴来回拉锯(±45px),
                双向火花对喷, 每0.4s气浪环, 电弧
  P4 69-90帧  突破: 白闪->核心球暴增->3层粗环->12条放射->30粒子四溅
  P5 90-105帧 余波
"""
import os, math, random, wave, struct
from PIL import Image, ImageDraw, ImageFilter

ROOT = "/opt/AICatMeme/fx/beam_clash"
FRAMES_DIR = os.path.join(ROOT, "frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

W = H = 1080
FPS = 30
N = 105
LX, RX, Y, CX = 290, 790, 470, 540
random.seed(7)

BLUE = (80, 170, 255)
GOLD = (255, 190, 70)
WHITE = (255, 255, 255)

def lerp(a, b, t): return a + (b - a) * max(0.0, min(1.0, t))
def ease_out(t): return 1 - (1 - max(0.0, min(1.0, t))) ** 2
def ease_in(t): return max(0.0, min(1.0, t)) ** 2

def layer_of(base, fn, blur=16, core=True, alpha=255):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fn(d)
    if blur:
        b = layer.filter(ImageFilter.GaussianBlur(blur))
        if alpha < 255:
            b.putalpha(b.getchannel("A").point(lambda a: int(a * alpha / 255)))
        base.alpha_composite(b)
    if core:
        base.alpha_composite(layer)
    return base

# 火花粒子池: [x, y, vx, vy, size, life, maxlife, col]
sparks = []

def render(f):
    t = f / FPS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ============ P1 蓄力 0-0.6s ============
    charge_r = 0
    if t < 0.6:
        p = t / 0.6
        charge_r = lerp(10, 52, ease_out(p))
        for cx, col in [(LX, BLUE), (RX, GOLD)]:
            layer_of(img, lambda dd, cx=cx, r=charge_r, col=col: dd.ellipse(
                [cx - r, Y - r, cx + r, Y + r], fill=col + (255,)), blur=30)
            # 内脉动白核
            rr = charge_r * (0.45 + 0.12 * math.sin(2 * math.pi * 8 * t))
            layer_of(img, lambda dd, cx=cx, r=rr: dd.ellipse(
                [cx - r, Y - r, cx + r, Y + r], fill=WHITE + (235,)), blur=8, core=True)
        # 吸入粒子
        for i in range(14):
            ang = random.uniform(0, 2 * math.pi)
            dist = lerp(210, 58, ease_out(p))
            side = LX if i % 2 == 0 else RX
            col = BLUE if i % 2 == 0 else GOLD
            px_, py_ = side + math.cos(ang) * dist, Y + math.sin(ang) * dist * 0.55
            d.ellipse([px_ - 5, py_ - 5, px_ + 5, py_ + 5], fill=col + (210,))

    # ============ P2/P3 出波+僵持 0.6-2.3s ============
    clash_x = CX
    if 0.6 <= t < 2.3:
        if t < 1.0:
            p = (t - 0.6) / 0.4
            tip = lerp(80, (CX - LX) * 0.98, ease_out(p))
        else:
            # 僵持: 撞点拉锯
            tip = (CX - LX) + 45 * math.sin(2 * math.pi * 0.9 * (t - 1.0))
        for side_x, tip_dir, col, opp in [(LX, 1, BLUE, GOLD), (RX, -1, GOLD, BLUE)]:
            x1 = side_x + tip_dir * tip
            w0, w1 = 14, int(lerp(50, 64, min(1, tip / 250)))
            # 外层柔光
            layer_of(img, lambda dd, x0=side_x, x1=x1, w0=w0, w1=w1, col=col: dd.polygon(
                [(x0, Y - w0 * 1.6), (x1, Y - w1 * 1.6), (x1, Y + w1 * 1.6), (x0, Y + w0 * 1.6)],
                fill=col + (110,)), blur=24, core=False)
            # 主体(近白核心)
            layer_of(img, lambda dd, x0=side_x, x1=x1, w0=w0, w1=w1, col=col: dd.polygon(
                [(x0, Y - w0), (x1, Y - w1), (x1, Y + w1), (x0, Y + w0)], fill=col + (235,)),
                blur=8, core=True)
            layer_of(img, lambda dd, x0=side_x, x1=x1, w0=w0 * 0.4, w1=w1 * 0.55: dd.polygon(
                [(x0, Y - w0), (x1, Y - w1), (x1, Y + w1), (x0, Y + w0)], fill=WHITE + (230,)),
                blur=4, core=True)
            # 流动亮斑(沿波冲向撞点)
            flow = ((t * 2.2) % 1.0)
            for k in range(3):
                fx_ = lerp(x0 if False else side_x, x1, (flow + k / 3) % 1.0)
                r = int(lerp(8, 26, 0.5))
                d.ellipse([fx_ - r, Y - r * 0.8, fx_ + r, Y + r * 0.8], fill=WHITE + (150,))
        clash_x = LX + tip  # 左波前沿即撞点

    # ============ P3 撞点球+僵持细节 1.0-2.3s ============
    if 1.0 <= t < 2.3:
        pulse = 0.55 + 0.45 * math.sin(2 * math.pi * 2.6 * (t - 1.0))
        r = int(lerp(30, 62, pulse))
        # 外圈双色混合弧
        layer_of(img, lambda dd, r=r: dd.ellipse(
            [clash_x - r, Y - r, clash_x + r, Y + r],
            outline=(200, 225, 255, 200), width=10), blur=10, core=False)
        # 核心白球
        layer_of(img, lambda dd, r=r * 0.8: dd.ellipse(
            [clash_x - r, Y - r, clash_x + r, Y + r], fill=WHITE + (245,)), blur=14, core=True)
        # 电弧: 2条zigzag
        for i in range(2):
            pts = [(clash_x, Y)]
            nseg = 5
            xcur = clash_x
            for s in range(nseg):
                xcur += (38 if i == 0 else -38)
                pts.append((xcur, Y + random.uniform(-30, 30)))
            d.line(pts, fill=WHITE + (170,), width=3)
        # 火花对喷: 撞点两侧向后喷
        for _ in range(3):
            side = random.choice([-1, 1])
            col = BLUE if side < 0 else GOLD
            sp = random.uniform(140, 340)
            vy = random.uniform(-120, 120)
            sparks.append([clash_x, Y, side * sp, vy, random.uniform(3, 7), 0.55, 0.55, col])
        # 气浪环: 每0.4s一发
        cyc = (t - 1.0) % 0.4
        rr = int(20 + 200 * ease_out(cyc / 0.4))
        a = int(150 * (1 - cyc / 0.4))
        layer_of(img, lambda dd, rr=rr, a=a, cx=clash_x: dd.ellipse(
            [cx - rr, Y - rr * 0.42, cx + rr, Y + rr * 0.42],
            outline=(235, 240, 255, a), width=8), blur=8, core=False)
        # 地面被气流吹起的尘埃(撞点下方)
        for i in range(4):
            ang = math.pi + i * math.pi / 4
            dist = 60 + 90 * ((t * 1.5) % 1)
            gx, gy = clash_x + math.cos(ang) * dist * 1.2, Y + 120 + math.sin(ang) * dist * 0.3
            d.ellipse([gx - 6, gy - 4, gx + 6, gy + 4], fill=(210, 205, 195, int(120 * (1 - (t * 1.5) % 1))))

    # 火花更新(任何阶段spawn的都在这里推进)
    alive = []
    for s in sparks:
        s[4] = s[4]; s[0] += s[2] / FPS; s[1] += s[3] / FPS; s[5] += 1 / FPS
        s[3] += 320 / FPS  # 重力
        if s[5] < s[6]:
            a = int(255 * (1 - s[5] / s[6]))
            d.ellipse([s[0] - s[4], s[1] - s[4], s[0] + s[4], s[1] + s[4]], fill=s[7] + (a,))
            d.ellipse([s[0] - s[4] * 0.4, s[1] - s[4] * 0.4, s[0] + s[4] * 0.4, s[1] + s[4] * 0.4],
                      fill=WHITE + (a,))
            alive.append(s)
    sparks.clear(); sparks.extend(alive)

    # ============ P4 突破爆炸 2.3-3.0s ============
    if 2.3 <= t < 3.0:
        p = (t - 2.3) / 0.7
        cx = clash_x if clash_x else CX
        if p < 0.18:  # 白闪
            fl = Image.new("RGBA", (W, H), WHITE + (int(245 * (1 - p / 0.18)),))
            img.alpha_composite(fl)
        # 核心球暴增
        r = int(lerp(62, 210, ease_out(p)))
        layer_of(img, lambda dd, r=r, p=p: dd.ellipse(
            [CX - r, Y - r, CX + r, Y + r],
            fill=(255, 240, 205, int(235 * (1 - p * 0.75)))), blur=34, core=False)
        layer_of(img, lambda dd, r=r * 0.55, p=p: dd.ellipse(
            [CX - r, Y - r, CX + r, Y + r],
            fill=WHITE + (int(245 * (1 - p * 0.6)),)), blur=10, core=False)
        # 3层粗环
        for li in range(3):
            pp = (p - li * 0.1) / (1 - li * 0.1)
            if pp <= 0: continue
            rr = int(20 + 520 * ease_out(pp))
            wid = int(lerp(40, 6, pp))
            a = int(lerp(255, 0, pp) * (1 - li * 0.15))
            col = [(255, 225, 150), (255, 180, 80), (255, 130, 60)][li]
            layer_of(img, lambda dd, rr=rr, wid=wid, col=col, a=a: dd.ellipse(
                [CX - rr, Y - rr, CX + rr, Y + rr], outline=col + (a,), width=wid),
                blur=6, core=False)
        # 12条粗放射光
        for i in range(12):
            ang = i * math.pi / 6 + p * 0.35
            ln = 80 + 420 * ease_out(p)
            x2, y2 = CX + math.cos(ang) * ln, Y + math.sin(ang) * ln
            a = int(230 * (1 - p))
            d.line([CX, Y, x2, y2], fill=(255, 235, 180, a), width=12)
            d.line([CX, Y, x2, y2], fill=WHITE + (a,), width=5)
        # 30粒子四溅
        if p < 0.5:
            for i in range(30):
                ang = i * math.pi * 2 / 30 + random.uniform(-0.15, 0.15)
                sp = random.uniform(200, 620)
                dist = sp * ease_out(p / 0.5) + sp * 0.3 * (p / 0.5)
                px_, py_ = CX + math.cos(ang) * dist, Y + math.sin(ang) * dist + 0.5 * 300 * (p / 0.5) ** 2
                a = int(255 * (1 - p / 0.5))
                col = random.choice([BLUE, GOLD, WHITE, (255, 120, 60)])
                d.ellipse([px_ - 8, py_ - 8, px_ + 8, py_ + 8], fill=col + (a,))

    # ============ P5 余波 3.0-3.5s ============
    elif t >= 3.0:
        p = (t - 3.0) / 0.5
        r = int(540 + 300 * ease_out(p))
        a = int(120 * (1 - p))
        layer_of(img, lambda dd, r=r, a=a: dd.ellipse(
            [CX - r, Y - r, CX + r, Y + r], outline=(255, 205, 130, a), width=16),
            blur=20, core=False)

    img.save(os.path.join(FRAMES_DIR, f"{f:04d}.png"))

for f in range(N):
    render(f)
print("frames done:", N)

# ================= 音效: 蓄力->僵持嗡鸣->爆发 =================
SR = 44100
def gen_audio():
    total = int(3.5 * SR)
    buf = [0.0] * total
    rnd = random.Random(3)
    # P1 蓄力 0-0.6: 120->320 sweep + 底噪渐强
    for i in range(int(0.6 * SR)):
        t = i / SR
        fq = 120 + 200 * (t / 0.6)
        buf[i] += 0.4 * math.sin(2 * math.pi * fq * t) * (0.3 + 0.7 * t / 0.6)
    # P2/P3 僵持嗡鸣 0.6-2.3: 90Hz基频+20Hz抖动+电流噪声
    for i in range(int(0.6 * SR), int(2.3 * SR)):
        t = i / SR
        wob = math.sin(2 * math.pi * 22 * (t - 0.6))
        buf[i] += 0.5 * math.sin(2 * math.pi * (95 + 18 * wob) * t)
        buf[i] += 0.18 * rnd.uniform(-1, 1) * (0.5 + 0.5 * wob)
        # 偶发"噼啪"
        if rnd.random() < 0.0008:
            for k in range(40):
                if i + k < len(buf):
                    buf[i + k] += 0.35 * math.sin(2 * math.pi * 1400 * k / SR) * math.exp(-k / 12)
    # P4 爆发 2.31-3.2
    for i in range(int(0.9 * SR)):
        j = int(2.31 * SR) + i
        t = i / SR
        buf[j] += 0.75 * rnd.uniform(-1, 1) * math.exp(-5.5 * t)
        buf[j] += 0.9 * math.sin(2 * math.pi * 55 * t) * math.exp(-9 * t)
        if t < 0.2:
            buf[j] += 0.45 * rnd.uniform(-1, 1) * math.exp(-25 * t)
        # 余震低频晃
        buf[j] += 0.3 * math.sin(2 * math.pi * 38 * t) * math.exp(-2.5 * t)
    peak = max(abs(v) for v in buf) or 1.0
    buf = [int(v / peak * 30000) for v in buf]
    w = wave.open(os.path.join(ROOT, "audio.wav"), "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(struct.pack("<" + "h" * len(buf), *buf))
    w.close()
    print("audio done")

gen_audio()
