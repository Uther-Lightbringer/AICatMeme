"""多特效总控生成器: fx/<name>/{frames,audio.wav}
已实现: fire_burst / freeze / thunder_strike / slash / shield / summon / screen_flash
每个特效都是 1080x1080 RGBA PNG序列@30fps + PIL/wave 合成音。
单猫场景猫中心x=540: 口/招高度y=560, 头顶y=430, 脚底y=880, 身中心y=620
"""
import os, math, random, wave, struct
from PIL import Image, ImageDraw, ImageFilter

FX_ROOT = "/opt/AICatMeme/fx"
W = H = 1080
FPS = 30
CX, MOUTH, HEAD, FOOT, BODY = 540, 560, 430, 880, 620

def lerp(a, b, t): return a + (b - a) * max(0.0, min(1.0, t))
def ease_out(t): return 1 - (1 - max(0.0, min(1.0, t))) ** 2

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

def save_frames(render, dur, out_dir):
    os.makedirs(os.path.join(out_dir, "frames"), exist_ok=True)
    n = int(dur * FPS)
    for f in range(n):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        render(f, f / FPS, img)
        img.save(os.path.join(out_dir, "frames", f"{f:04d}.png"))
    return n

def save_wav(path, gen, dur, sr=44100):
    buf = [0.0] * int(dur * sr)
    rnd = random.Random(int(dur * 1000))
    for i in range(len(buf)):
        buf[i] = gen(i / sr, rnd)
    peak = max(abs(v) for v in buf) or 1.0
    buf = [int(v / peak * 28000) for v in buf]
    w = wave.open(path, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(struct.pack("<" + "h" * len(buf), *buf))
    w.close()

# ============================================================ 火法
def render_fire(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(f * 7 + 1)
    if t < 0.5:  # 火球凝聚
        p = t / 0.5
        r = int(lerp(14, 60, ease_out(p)))
        for rr, col, al in [(r, (255, 80, 20), 200), (int(r*0.7), (255, 160, 40), 230), (int(r*0.4), (255, 240, 180), 245)]:
            layer_of(img, lambda dd, rr=rr, col=col, al=al: dd.ellipse(
                [CX-rr, MOUTH-rr, CX+rr, MOUTH+rr], fill=col+(al,)), blur=22, core=False)
        for _ in range(6):  # 火苗上窜
            fx_ = CX + rnd.uniform(-40, 40)
            d.line([fx_, MOUTH, fx_ + rnd.uniform(-14, 14), MOUTH - rnd.uniform(30, 80)],
                   fill=(255, 150, 50, 200), width=4)
    elif t < 1.0:  # 喷发
        p = (t - 0.5) / 0.5
        ln = int(lerp(60, 430, ease_out(p)))
        wid = int(lerp(50, 24, p))
        for i in range(6):  # 火焰舌头
            off = rnd.uniform(-30, 30)
            w2 = wid * rnd.uniform(0.5, 1.1)
            layer_of(img, lambda dd, ln=ln, w2=w2, off=off: dd.polygon(
                [(CX-14, MOUTH-10), (CX+14, MOUTH+10), (CX+14+ln, MOUTH+off+w2), (CX+14+ln, MOUTH+off-w2)],
                fill=(255, 120 + i*15, 30, 170)), blur=14, core=False)
        layer_of(img, lambda dd, ln=ln, wid=wid: dd.polygon(
            [(CX-16, MOUTH), (CX+16, MOUTH), (CX+16+ln, MOUTH+wid*0.5), (CX+16+ln, MOUTH-wid*0.5)],
            fill=(255, 230, 160, 230)), blur=8, core=True)
    elif t < 1.6:  # 命中爆炸
        p = (t - 1.0) / 0.6
        ex = CX + 450
        for rr, col in [(int(30+90*ease_out(p)), (255,90,30)), (int(20+130*ease_out(p)*0.8), (255,170,60))]:
            layer_of(img, lambda dd, rr=rr, col=col, ex=ex, p=p: dd.ellipse(
                [ex-rr, MOUTH-rr, ex+rr, MOUTH+rr], fill=col+(int(200*(1-p)),)), blur=20, core=False)
        for _ in range(20):
            ang = rnd.uniform(0, 2*math.pi); sp = rnd.uniform(100, 420)
            px_, py_ = ex + math.cos(ang)*sp*p, MOUTH + math.sin(ang)*sp*p
            r = rnd.uniform(3, 8)
            d.ellipse([px_-r, py_-r, px_+r, py_+r], fill=(255, rnd.randint(120,220), 40, int(255*(1-p))))
    elif t < 2.0:  # 余烟
        p = (t - 1.6) / 0.4
        for i in range(5):
            gy = MOUTH + 20 - p * 120
            gx = CX + 450 + rnd.uniform(-80, 80)
            r = int(20 + 30 * p)
            layer_of(img, lambda dd, gx=gx, gy=gy, r=r, p=p: dd.ellipse(
                [gx-r, gy-r, gx+r, gy+r], fill=(120, 110, 105, int(70*(1-p)))), blur=16, core=False)

# ============================================================ 冰封
def render_freeze(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(f * 11 + 2)
    if t < 0.8:  # 冰棱从脚底上蔓延
        p = t / 0.8
        top = FOOT - int(430 * ease_out(p))
        for x in range(CX-320, CX+320, 26):
            h = rnd.uniform(0.5, 1.0)
            ty = FOOT - int((FOOT - top) * h * rnd.uniform(0.7, 1))
            layer_of(img, lambda dd, x=x, ty=ty: dd.polygon(
                [(x-10, FOOT), (x+10, FOOT), (x+3, ty), (x-3, ty)], fill=(170, 220, 255, 220)),
                blur=3, core=True)
            d.ellipse([x-4, ty-6, x+4, ty+6], fill=(235, 250, 255, 240))
    elif t < 1.4:  # 冰塑封裹
        p = (t - 0.8) / 0.6
        a = int(150 * min(1, p * 2))
        layer_of(img, lambda dd, a=a: dd.rounded_rectangle(
            [CX-260, HEAD-40, CX+260, FOOT-10], radius=90, fill=(150, 210, 255, a)), blur=6, core=False)
        for _ in range(26):  # 冰晶闪点
            fx_ = CX + rnd.uniform(-250, 250); fy_ = HEAD + rnd.uniform(-30, 430)
            r = rnd.uniform(3, 9)
            d.ellipse([fx_-r, fy_-r, fx_+r, fy_+r], fill=(240, 252, 255, rnd.randint(180, 255)))
    else:  # 霜雾+碎冰飘落
        p = (t - 1.4) / 0.6
        for _ in range(4):
            gx = CX + rnd.uniform(-200, 200); gy = HEAD + ((t * 90) % 400)
            r = int(16 + 20 * p)
            layer_of(img, lambda dd, gx=gx, gy=gy, r=r, p=p: dd.ellipse(
                [gx-r, gy-r, gx+r, gy+r], fill=(200, 230, 255, int(60*(1-p)))), blur=14, core=False)
        for _ in range(14):
            fx_ = CX + rnd.uniform(-260, 260); fy_ = HEAD + rnd.uniform(0, 450) + t * 130
            r = rnd.uniform(2, 5)
            d.ellipse([fx_-r, fy_-r, fx_+r, fy_+r], fill=(235, 250, 255, int(230*(1-p*0.6))))

# ============================================================ 雷劫
def _bolt(d, x, y, ang, ln, wid, depth):
    if depth == 0 or ln < 14:
        d.line([x, y, x + math.cos(ang)*ln, y + math.sin(ang)*ln], fill=(255,255,255,255), width=wid)
        return
    for _ in range(2):
        mid = ln * 0.5
        mx, my = x + math.cos(ang)*mid, y + math.sin(ang)*mid
        _bolt(d, x, y, ang, mid, wid, depth-1)
        bang = ang + random.uniform(-0.7, 0.7)
        _bolt(d, mx, my, bang, ln*0.6, max(1, wid-1), depth-1)

def render_thunder(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(900 + f)
    if t < 0.5:  # 聚云+小子闪
        p = t / 0.5
        layer_of(img, lambda dd, p=p: dd.ellipse(
            [CX-330, 20, CX+330, 220], fill=(60, 60, 90, int(150+60*p))), blur=26, core=False)
        if rnd.random() < 0.5:
            for _ in range(3):
                d.line([CX-60, 90, CX+60, 90], fill=(200, 210, 255, 120), width=2)
    elif t < 0.8:  # 主闪+分形闪电
        layer_of(img, lambda dd: dd.ellipse(
            [CX-330, 20, CX+330, 220], fill=(150, 160, 255, 200)), blur=26, core=False)
        random.seed(42)
        _bolt(d, CX, 160, math.pi/2, 300, 8, 4)
        # 落点强闪
        layer_of(img, lambda dd: dd.ellipse(
            [CX-160, HEAD-160, CX+160, HEAD+160], fill=(240, 245, 255, 235)), blur=30, core=False)
    elif t < 1.2:  # 冲击环
        p = (t - 0.8) / 0.4
        rr = int(30 + 420 * ease_out(p))
        layer_of(img, lambda dd, rr=rr, p=p: dd.ellipse(
            [CX-rr, HEAD+40-rr, CX+rr, HEAD+40+rr], outline=(190, 210, 255, int(230*(1-p))), width=20),
            blur=8, core=False)
        for _ in range(14):
            ang = rnd.uniform(0, 2*math.pi); sp = rnd.uniform(80, 380)
            px_, py_ = CX + math.cos(ang)*sp*p, HEAD+40 + math.sin(ang)*sp*p
            r = rnd.uniform(2, 6)
            d.line([px_, py_, px_-math.cos(ang)*22, py_-math.sin(ang)*22], fill=(220,230,255,int(220*(1-p))), width=3)
    else:  # 电蛇残留+余烬
        p = (t - 1.2) / 0.8
        random.seed(77)
        for _ in range(2):
            _bolt(d, CX, 160, math.pi/2 + rnd.uniform(-0.3, 0.3), 260, 4, 3)
        for _ in range(10):
            px_ = CX + rnd.uniform(-200, 200); py_ = HEAD + rnd.uniform(0, 300) + t * 60
            r = rnd.uniform(2, 5)
            d.ellipse([px_-r, py_-r, px_+r, py_+r], fill=(200, 220, 255, int(200*(1-p))))

# ============================================================ 剑气
def render_slash(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(500 + f)
    if t < 0.25:  # 蓄力白线
        p = t / 0.25
        layer_of(img, lambda dd, p=p: dd.arc(
            [CX-260-40*p, MOUTH-260-40*p, CX+260+40*p, MOUTH+260+40*p],
            start=200, end=340, fill=(255,255,255,int(200*p)), width=6), blur=6, core=True)
    elif t < 0.55:  # 月牙横扫
        p = (t - 0.25) / 0.3
        sweep = lerp(-0.9, 0.9, ease_out(p))
        ca, sa = math.cos(sweep*0.9), math.sin(sweep*0.9)
        # 三道月牙(残影)
        for k, alpha in [(2, 60), (1, 120), (0, 255)]:
            off = k * 0.12
            a2 = sweep - off
            x1 = CX - 300*math.cos(a2) - 90*math.sin(a2)
            y1 = MOUTH - 300*math.sin(a2) + 90*math.cos(a2)
            x2 = CX + 300*math.cos(a2) - 90*math.sin(a2)
            y2 = MOUTH + 300*math.sin(a2) + 90*math.cos(a2)
            layer_of(img, lambda dd, x1=x1, y1=y1, x2=x2, y2=y2, alpha=alpha: dd.arc(
                [min(x1,x2)-40, min(y1,y2)-40, max(x1,x2)+40, max(y1,y2)+40],
                start=a2*57-40, end=a2*57+40, fill=(255,255,255,alpha), width=26), blur=10, core=False)
        d.arc([CX-330, MOUTH-330, CX+330, MOUTH+330], start=sweep*57-8, end=sweep*57+8,
              fill=(255,255,255,255), width=6)
    elif t < 0.85:  # 切割线+火花
        p = (t - 0.55) / 0.3
        layer_of(img, lambda dd, p=p: dd.line(
            [CX-340, MOUTH+40, CX+340, MOUTH-40], fill=(255,255,255,int(220*(1-p))), width=8),
            blur=4, core=True)
        for _ in range(16):
            sx = CX + rnd.uniform(-330, 330); sy = MOUTH + rnd.uniform(-80, 80)
            r = rnd.uniform(2, 6)
            d.ellipse([sx-r, sy-r, sx+r, sy+r], fill=(255, 240, 200, int(240*(1-p))))
    else:  # 剑气残留
        p = (t - 0.85) / 0.65
        layer_of(img, lambda dd, p=p: dd.arc(
            [CX-300, MOUTH-300, CX+300, MOUTH+300], start=200, end=340,
            fill=(230, 240, 255, int(90*(1-p))), width=40), blur=18, core=False)

# ============================================================ 护盾
def render_shield(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(700 + f)
    cx, cy = CX, BODY
    if t < 0.6:  # 网格罩亮起
        p = ease_out(t / 0.6)
        R = int(300 * p)
        layer_of(img, lambda dd, R=R: dd.ellipse(
            [cx-R, cy-R*1.25, cx+R, cy+R*1.25], outline=(90, 180, 255, 210), width=10),
            blur=10, core=False)
        layer_of(img, lambda dd, R=R: dd.ellipse(
            [cx-R, cy-R*1.25, cx+R, cy+R*1.25], fill=(90, 180, 255, 40)), blur=18, core=False)
        a = int(150 * p)
        for ring in range(3):  # 六边形网格感: 同心圆+经纬线
            rr = R * (ring + 1) / 3
            d.ellipse([cx-rr, cy-rr*1.25, cx+rr, cy+rr*1.25], outline=(120, 200, 255, a//2), width=3)
        for k in range(-3, 4):  # 竖线
            d.line([cx+k*R/3, cy-R*1.25, cx+k*R/3, cy+R*1.25], fill=(120, 200, 255, a//3), width=2)
    elif t < 1.3:  # 受击波纹(右上撞击点)
        p = (t - 0.6) / 0.7
        R = 300
        hx, hy = cx + int(R*0.7*math.cos(0.6)), cy - int(R*1.25*math.sin(0.6))
        layer_of(img, lambda dd, R=R: dd.ellipse(
            [cx-R, cy-R*1.25, cx+R, cy+R*1.25], outline=(90, 180, 255, 170), width=10),
            blur=10, core=False)
        for ring in range(3):
            rr = 20 + 240 * ease_out(max(0, p - ring*0.15))
            if rr <= 20: continue
            layer_of(img, lambda dd, rr=rr, hx=hx, hy=hy, p=p, ring=ring: dd.ellipse(
                [hx-rr, hy-rr*0.8, hx+rr, hy+rr*0.8],
                outline=(200, 235, 255, int(220*(1-(p-ring*0.15)/0.85))), width=8),
                blur=6, core=False)
        layer_of(img, lambda dd: dd.ellipse([hx-26, hy-26, hx+26, hy+26], fill=(255,255,255,240)),
                 blur=16, core=True)
    else:  # 罩碎
        p = (t - 1.3) / 0.7
        R = 300
        if p < 0.4:
            for _ in range(8):  # 裂纹
                ang = rnd.uniform(0, 2*math.pi)
                d.line([cx, cy, cx+math.cos(ang)*R, cy+math.sin(ang)*R*1.25],
                       fill=(255,255,255,int(200*(1-p/0.4))), width=3)
        for frag in range(22):  # 碎裂飞散
            ang = frag * math.pi * 2 / 22
            dist = R * (0.6 + p * 0.8)
            fx_, fy_ = cx + math.cos(ang)*dist, cy + math.sin(ang)*dist*1.25
            r = rnd.uniform(4, 12)
            d.ellipse([fx_-r, fy_-r, fx_+r, fy_+r], fill=(140, 210, 255, int(230*(1-p))))

# ============================================================ 召唤阵
def render_summon(f, t, img):
    d = ImageDraw.Draw(img)
    cy = FOOT - 60
    rnd = random.Random(300 + f)
    if t < 1.0:  # 阵图亮起+旋转
        p = ease_out(t / 1.0)
        R = int(300 * p)
        a = int(220 * p)
        for rr in [R, int(R*0.7), int(R*0.4)]:
            layer_of(img, lambda dd, rr=rr, a=a: dd.ellipse(
                [CX-rr, cy-rr*0.42, CX+rr, cy+rr*0.42], outline=(160, 90, 255, a), width=8),
                blur=8, core=False)
        for i in range(12):  # 符文刻度
            ang = i * math.pi / 6 + t * 1.6
            x1 = CX + math.cos(ang) * R * 0.82
            y1 = cy + math.sin(ang) * R * 0.42 * 0.82
            x2 = CX + math.cos(ang) * R * 0.95
            y2 = cy + math.sin(ang) * R * 0.42 * 0.95
            d.line([x1, y1, x2, y2], fill=(220, 170, 255, a), width=6)
        layer_of(img, lambda dd, R=R, a=a: dd.ellipse(
            [CX-R*0.36, cy-R*0.36*0.42, CX+R*0.36, cy+R*0.36*0.42], outline=(255, 80, 200, a), width=6),
            blur=6, core=False)
    else:  # 光柱冲天+顶端炸开
        p = (t - 1.0) / 2.0
        h = max(20, int(760 * min(1, p * 1.6)))
        wid = int(150 * (1 - 0.4 * max(0, p - 0.5)))
        layer_of(img, lambda dd, h=h, wid=wid, p=p: dd.polygon(
            [(CX-wid, cy), (CX+wid, cy), (CX+wid*0.5, cy-h), (CX-wid*0.5, cy-h)],
            fill=(200, 130, 255, int(150*(1-0.5*max(0,p-0.4))))), blur=22, core=False)
        layer_of(img, lambda dd, h=h, wid=wid, p=p: dd.polygon(
            [(CX-wid*0.45, cy), (CX+wid*0.45, cy), (CX+wid*0.2, cy-h), (CX-wid*0.2, cy-h)],
            fill=(245, 220, 255, int(230*(1-0.4*max(0,p-0.3))))), blur=8, core=False)
        for _ in range(5):  # 上升符文
            uy = cy - ((t * 400) % h)
            ux = CX + rnd.uniform(-60, 60)
            d.ellipse([ux-8, uy-8, ux+8, uy+8], fill=(255, 220, 255, 220))
        if p > 0.45:  # 顶端炸开
            pp = (p - 0.45) / 0.55
            rr = int(40 + 380 * ease_out(pp))
            layer_of(img, lambda dd, rr=rr, pp=pp: dd.ellipse(
                [CX-rr, cy-760-rr, CX+rr, cy-760+rr],
                outline=(235, 170, 255, int(230*(1-pp))), width=22), blur=10, core=False)
            for i in range(14):
                ang = i * math.pi * 2 / 14
                px_ = CX + math.cos(ang) * 380 * ease_out(pp)
                py_ = cy - 760 + math.sin(ang) * 380 * ease_out(pp)
                r = rnd.uniform(4, 10)
                d.ellipse([px_-r, py_-r, px_+r, py_+r], fill=(240, 200, 255, int(240*(1-pp))))

# ============================================================ 受击闪屏(终局)
def render_flash(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(100 + f)
    if t < 0.5:  # 黑白频闪
        if (f // 2) % 2 == 0:
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, 210)))
        else:
            img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 120)))
    elif t < 0.65:  # 血红
        img.alpha_composite(Image.new("RGBA", (W, H), (200, 20, 20, 110)))
    else:  # 暗角收拢
        p = (t - 0.65) / 0.85
        vig = Image.new("L", (W, H), 0)
        vd = ImageDraw.Draw(vig)
        r_in = int(1080 * (1 - p))
        vd.ellipse([CX-r_in, 540-r_in, CX+r_in, 540+r_in], fill=255)
        img.alpha_composite(Image.composite(
            Image.new("RGBA", (W, H), (0, 0, 0, int(200*p))), Image.new("RGBA", (W, H), (0,0,0,0)), vig))

# ============================================================ 瞬移
def render_teleport(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(8000 + f)
    cy = BODY
    if t < 0.3:  # 原地虚影渐隐
        p = t / 0.3
        a = int(200 * (1 - p))
        layer_of(img, lambda dd, a=a: dd.rounded_rectangle(
            [CX-180, cy-320, CX+180, cy+240], radius=80, fill=(140, 200, 255, a)), blur=16, core=False)
        for _ in range(6):  # 闪烁残片
            fx_ = CX + rnd.uniform(-170, 170); fy_ = cy + rnd.uniform(-300, 220)
            d.rectangle([fx_-6, fy_-20, fx_+6, fy_+20], fill=(160, 210, 255, int(180*(1-p))))
    elif t < 0.8:  # 空间波纹+碎片
        p = (t - 0.3) / 0.5
        for ring in range(3):
            rr = int((40 + 260 * ease_out(max(0, p - ring*0.15))) * 1.0)
            if rr <= 40: continue
            layer_of(img, lambda dd, rr=rr, p=p, ring=ring: dd.ellipse(
                [CX-rr, cy-rr, CX+rr, cy+rr],
                outline=(120, 190, 255, int(220*(1-(p-ring*0.15)/0.85))), width=10),
                blur=8, core=False)
        for _ in range(18):  # 碎片向中心汇聚
            ang = rnd.uniform(0, 2*math.pi); dist = lerp(320, 60, ease_out(p))
            fx_ = CX + math.cos(ang)*dist; fy_ = cy + math.sin(ang)*dist*0.8
            r = rnd.uniform(3, 9)
            d.rectangle([fx_-r, fy_-r*2.4, fx_+r, fy_+r*2.4], fill=(150, 205, 255, int(230*p)))
    elif t < 1.2:  # 重组白闪
        p = (t - 0.8) / 0.4
        flash = Image.new("RGBA", (W, H), (200, 230, 255, int(230*(1-p))))
        img.alpha_composite(flash)
        for _ in range(8):
            fx_ = CX + rnd.uniform(-140, 140); fy_ = cy + rnd.uniform(-260, 200)
            r = rnd.uniform(4, 10)
            d.ellipse([fx_-r, fy_-r, fx_+r, fy_+r], fill=(255, 255, 255, int(220*(1-p))))
    else:  # 就位尘环
        p = (t - 1.2) / 0.8
        rr = int(80 + 260 * ease_out(p))
        layer_of(img, lambda dd, rr=rr, p=p: dd.ellipse(
            [CX-rr, cy+200-rr*0.4, CX+rr, cy+200+rr*0.4],
            outline=(160, 210, 255, int(160*(1-p))), width=8), blur=8, core=False)

# ============================================================ 治疗雨
def render_heal(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(4200 + f)
    # 绿色光点持续下降(全屏)
    for i in range(22):
        gx = 120 + (i * 137 + f * 3) % 840
        gy = (i * 173 + f * 11) % 900 + 60
        r = rnd.uniform(3, 8)
        d.line([gx, gy - 16, gx, gy], fill=(120, 255, 150, 150), width=3)
        layer_of(img, lambda dd, gx=gx, gy=gy, r=r: dd.ellipse(
            [gx-r, gy-r, gx+r, gy+r], fill=(140, 255, 170, 220)), blur=8, core=False)
    # 猫身环绕绿环
    p = min(1, t / 0.8)
    for ring in range(2):
        rr = int(lerp(120, 330, ease_out(p)) * (1 - ring * 0.25))
        layer_of(img, lambda dd, rr=rr, p=p: dd.ellipse(
            [CX-rr, BODY-rr, CX+rr, BODY+rr],
            outline=(100, 255, 150, int(180*p)), width=6), blur=12, core=False)
    # 上升粒子
    for _ in range(10):
        ux = CX + rnd.uniform(-200, 200)
        uy = FOOT - ((t * 320 + rnd.uniform(0, 400)) % 420)
        r = rnd.uniform(3, 7)
        d.ellipse([ux-r, uy-r, ux+r, uy+r], fill=(180, 255, 190, 220))
    # 结束脉冲
    if t > 1.9:
        pp = (t - 1.9) / 0.6
        rr = int(60 + 380 * ease_out(pp))
        layer_of(img, lambda dd, rr=rr, pp=pp: dd.ellipse(
            [CX-rr, BODY-rr, CX+rr, BODY+rr],
            outline=(140, 255, 170, int(220*(1-pp))), width=20), blur=10, core=False)

# ============================================================ 钞票雨
def render_money(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(3100 + f)
    for i in range(14):  # 旋转钞票
        bx = 100 + (i * 157 + f * 2) % 880
        by = (i * 191 + f * 9) % 900
        wdt, hgt = 46, 26
        rot = (i * 0.7 + t * 3) % (2 * math.pi)
        col = [(250, 220, 90), (160, 230, 150), (240, 240, 200)][i % 3]
        pts = []
        for (ox, oy) in [(-wdt, -hgt), (wdt, -hgt), (wdt, hgt), (-wdt, hgt)]:
            rx = ox * math.cos(rot) - oy * math.sin(rot) * 0.5
            ry = ox * math.sin(rot) + oy * math.cos(rot) * 0.5
            pts.append((bx + rx, by + ry))
        d.polygon(pts, fill=col + (235,), outline=(180, 150, 60, 255))
        d.text((bx - 8, by - 10), "¥", fill=(150, 120, 30, 255))
    for i in range(6):  # 金币弹跳
        cx_ = 300 + i * 100
        cy_ = 900 - abs(math.sin(t * 4 + i) * 260)
        r = 14
        d.ellipse([cx_-r, cy_-r, cx_+r, cy_+r], fill=(255, 200, 60, 255), outline=(200, 150, 30, 255))
        d.ellipse([cx_-r//2, cy_-r//2, cx_+r//2, cy_+r//2], fill=(255, 235, 150, 255))
    # 中央大¥金闪
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * 2 * t)
    layer_of(img, lambda dd, pulse=pulse: dd.text(
        (CX-40, BODY-70), "¥", fill=(255, 220, 100, int(200*pulse))), blur=10, core=False)

# ============================================================ 心动
def render_hearts(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(5500 + f)
    def heart(dd, x, y, s, col=(255, 90, 150), a=255):
        dd.ellipse([x-s, y-s*0.8, x, y], fill=col + (a,))
        dd.ellipse([x, y-s*0.8, x+s, y], fill=col + (a,))
        dd.polygon([(x-s*0.95, y-s*0.35), (x+s*0.95, y-s*0.35), (x, y+s*0.9)], fill=col + (a,))
    # 粉雾
    layer_of(img, lambda dd: dd.ellipse(
        [CX-400, BODY-400, CX+400, BODY+400], fill=(255, 130, 180, 60)), blur=40, core=False)
    # 爱心飘升
    for i in range(12):
        hx = CX + math.sin(t * 2 + i * 1.3) * rnd.uniform(60, 220)
        hy = BODY + 120 - ((t * 150 + i * 80) % 520)
        s = rnd.uniform(10, 26) * (1 + 0.15 * math.sin(2 * math.pi * 3 * t + i))
        heart(d, hx, hy, s, (255, rnd.randint(80, 160), rnd.randint(150, 200)), 220)
    # 中央大爱心(心跳双跳)
    beat = max(0, math.sin(2 * math.pi * 1.6 * t) ** 4)
    s = 56 + 26 * beat
    heart(d, CX, BODY - 100, s, (255, 70, 130), int(200 + 55 * beat))
    layer_of(img, lambda dd, s=s: heart(dd, CX, BODY - 100, s), blur=18, core=False)


# ============================================================ 怒焰
def render_anger(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(6600 + f)
    # 红色脉动暗角
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * 2.2 * t)
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-200, -200, W+200, H+200], fill=200)
    img.alpha_composite(Image.composite(
        Image.new("RGBA", (W, H), (120, 0, 0, int(120*pulse))),
        Image.new("RGBA", (W, H), (0, 0, 0, 0)), vig))
    # 黑红火焰从两侧上升
    for side in [-1, 1]:
        for i in range(7):
            fx_ = CX + side * rnd.uniform(140, 300)
            fh = rnd.uniform(120, 300) * (0.7 + 0.5*pulse)
            fy0 = FOOT - 40
            wob = math.sin(t * 8 + i) * 22
            pts = [(fx_-26, fy0), (fx_+wob, fy0 - fh*0.55), (fx_+wob*1.4, fy0 - fh)]
            layer_of(img, lambda dd, p=pts: dd.polygon(
                [p[0], (p[1][0]+14, p[1][1]), p[2], (p[1][0]-14, p[1][1])],
                fill=(20, 10, 30, 220)), blur=10, core=False)
            layer_of(img, lambda dd, p=pts: dd.polygon(
                [(p[0][0]*0.7+p[1][0]*0.3, p[0][1]), (p[1][0]+6, p[1][1]), (p[2][0]*0.6+p[1][0]*0.4, p[2][1])],
                fill=(200, 40, 30, 200)), blur=6, core=False)
    # 头顶青筋(#形)
    gx, gy = CX, HEAD - 60
    a = int(230 * (0.6 + 0.4*pulse))
    d.line([(gx-40, gy-26), (gx-14, gy)], fill=(255, 255, 255, a), width=6)
    d.line([(gx+40, gy-26), (gx+14, gy)], fill=(255, 255, 255, a), width=6)
    d.line([(gx-14, gy), (gx+14, gy)], fill=(255, 255, 255, a), width=6)
    # 地面龟裂
    for i in range(7):
        ang = math.pi + i * math.pi / 6
        ln = rnd.uniform(120, 300)
        d.line([CX, FOOT-10, CX+math.cos(ang)*ln, FOOT-10-math.sin(ang)*ln*0.3],
               fill=(40, 30, 30, 200), width=5)

# ============================================================ 晕眩
def render_dizzy(f, t, img):
    d = ImageDraw.Draw(img)
    # 头顶转星星(五角星绕头顶公转+自转)
    sx, sy, orbit = CX, HEAD - 90, 110
    for k in range(3):
        ang = t * 5 + k * math.pi * 2 / 3
        bx = sx + math.cos(ang) * orbit
        by = sy + math.sin(ang) * orbit * 0.5
        s = 20
        pts = []
        for i in range(10):
            rr = s if i % 2 == 0 else s * 0.45
            a2 = i * math.pi / 5 + t * 3
            pts.append((bx + math.cos(a2)*rr, by + math.sin(a2)*rr))
        d.polygon(pts, fill=(255, 230, 90, 240), outline=(200, 150, 20, 255))
    # 螺旋线
    for i in range(30):
        a2 = i * 0.45 + t * 6
        rr = 12 + i * 5
        x2 = sx + math.cos(a2) * rr
        y2 = sy + math.sin(a2) * rr * 0.6
        d.ellipse([x2-3, y2-3, x2+3, y2+3], fill=(255, 240, 130, 200))
    # 眩晕波纹
    p = (t % 1.0)
    rr = int(60 + 260 * p)
    layer_of(img, lambda dd, rr=rr, p=p: dd.ellipse(
        [sx-rr, sy-rr*0.6, sx+rr, sy+rr*0.6],
        outline=(255, 235, 120, int(150*(1-p))), width=8), blur=8, core=False)

# ============================================================ 陨石
def render_meteor(f, t, img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(7700 + f)
    if t < 1.0:  # 火球下落加速
        p = ease_out(t / 1.0) ** 1.6
        mx = lerp(200, CX, p)
        my = lerp(-60, FOOT - 60, p)
        r = int(lerp(30, 90, p))
        # 拖尾
        for i in range(10):
            tr = r * (1 - i * 0.08)
            tx = mx - (mx - 200) * i * 0.06
            ty = my + i * 55
            layer_of(img, lambda dd, tr=tr, tx=tx, ty=ty, i=i: dd.ellipse(
                [tx-tr, ty-tr, tx+tr, ty+tr], fill=(255, 150 - i*10, 40, int(180 - i*15))),
                blur=14, core=False)
        layer_of(img, lambda dd, r=r: dd.ellipse(
            [mx-r, my-r, mx+r, my+r], fill=(255, 210, 120, 240)), blur=18, core=False)
    elif t < 1.3:  # 落地白闪
        p = (t - 1.0) / 0.3
        img.alpha_composite(Image.new("RGBA", (W, H), (255, 220, 160, int(200*(1-p)))))
    else:  # 地面冲击+烟柱
        p = (t - 1.3) / 1.2
        for ring in range(3):
            rr = int(30 + 460 * ease_out(max(0, p - ring*0.12)))
            if rr <= 30: continue
            layer_of(img, lambda dd, rr=rr, p=p, ring=ring: dd.ellipse(
                [CX-rr, FOOT-rr*0.35, CX+rr, FOOT+rr*0.35],
                outline=(255, 180 - ring*30, 80, int(230*(1-max(0,p-ring*0.12)))), width=16),
                blur=8, core=False)
        for i in range(8):  # 碎石
            ang = -math.pi/2 + (i - 3.5) * 0.3
            dist = 120 + 380 * ease_out(p)
            fx_ = CX + math.cos(ang) * dist * 1.1
            fy_ = FOOT - 40 + math.sin(ang) * dist + 0.5 * 500 * p * p
            r = rnd.uniform(5, 12)
            d.ellipse([fx_-r, fy_-r, fx_+r, fy_+r], fill=(90, 70, 60, int(240*(1-p*0.7))))
        for i in range(6):  # 烟柱
            sx = CX + rnd.uniform(-90, 90)
            sy = FOOT - 60 - p * 260
            r = int(26 + 50 * p)
            layer_of(img, lambda dd, sx=sx, sy=sy, r=r, p=p: dd.ellipse(
                [sx-r, sy-r, sx+r, sy+r], fill=(110, 100, 95, int(90*(1-p)))), blur=18, core=False)

# ============================================================ 冲击推进
def render_punch(f, t, img):
    d = ImageDraw.Draw(img)
    if t < 0.3:  # 放射速度线
        p = t / 0.3
        for i in range(24):
            ang = i * math.pi / 12 + rnd_shift(f, i)
            ln = lerp(200, 620, ease_out(p))
            x2 = CX + math.cos(ang) * ln
            y2 = BODY + math.sin(ang) * ln
            d.line([CX + math.cos(ang)*120, BODY + math.sin(ang)*120, x2, y2],
                   fill=(255, 255, 255, int(200*p)), width=int(lerp(2, 7, p)))
    elif t < 0.5:  # 白闪+冲击环
        p = (t - 0.3) / 0.2
        img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(230*(1-p)))))
        rr = int(40 + 380 * ease_out(p))
        layer_of(img, lambda dd, rr=rr: dd.ellipse(
            [CX-rr, BODY-rr, CX+rr, BODY+rr], outline=(255, 240, 200, 230), width=18),
            blur=8, core=False)
    else:  # 重击震波+碎片
        p = (t - 0.5) / 1.0
        for ring in range(4):  # 多重扁环
            rr = int(50 + 300 * ease_out(max(0, p - ring*0.15)))
            if rr <= 50: continue
            layer_of(img, lambda dd, rr=rr, p=p, ring=ring: dd.ellipse(
                [CX-rr, BODY-rr*0.4, CX+rr, BODY+rr*0.4],
                outline=(255, 220, 150, int(210*(1-max(0,p-ring*0.15)))), width=10),
                blur=8, core=False)
        for i in range(16):
            ang = i * math.pi / 8
            dist = 100 + 420 * ease_out(p)
            fx_ = CX + math.cos(ang) * dist
            fy_ = BODY + math.sin(ang) * dist * 0.5
            r = 8 * (1 - p * 0.6)
            d.polygon([(fx_-r, fy_-r), (fx_+r, fy_-r*0.4), (fx_+r*0.3, fy_+r), (fx_-r*0.5, fy_+r*0.5)],
                      fill=(240, 230, 210, int(240*(1-p))))

def rnd_shift(f, i):
    return (i * 2654435761 % 360) * math.pi / 180


AUDIO = {
    "fire_burst": lambda t, r: (0.5*math.sin(2*math.pi*(120+200*min(t,0.5)/0.5)*t)*math.exp(-2*min(t,0.5))
                                + (0.9*r.uniform(-1,1)*math.exp(-4*max(0,t-1.0)) if t>=1.0 else 0)),
    "freeze": lambda t, r: 0.4*math.sin(2*math.pi*(600+800*min(t,0.8)/0.8)*t)*math.exp(-1.5*min(t,0.8))
                            + (0.35*r.uniform(-1,1)*math.exp(-6*max(0,t-1.4)) if t>=1.4 else 0),
    "thunder_strike": lambda t, r: (0.25*(r.uniform(-1,1))*math.exp(-3*min(t,0.5))
                                    if t<0.8 else (0.9*r.uniform(-1,1)*math.exp(-3*(t-0.8))
                                    + 0.8*math.sin(2*math.pi*45*(t-0.8))*math.exp(-6*(t-0.8))
                                    + 0.4*r.uniform(-1,1)*math.exp(-30*max(0,(t-0.8)-0.05)))),
    "slash": lambda t, r: 0.3*math.sin(2*math.pi*(300+900*min(t,0.25)/0.25)*t)*math.exp(-1*min(t,0.25))
                          + (0.7*math.sin(2*math.pi*(3000-2200*min(t-0.25,0.3)/0.3)*(t-0.25))*math.exp(-8*max(0,t-0.25)) if t>=0.25 else 0),
    "shield": lambda t, r: 0.35*math.sin(2*math.pi*180*t)*math.exp(-2.5*min(t,1.4))
                           + (0.6*math.sin(2*math.pi*520*(t-0.6))*math.exp(-10*(t-0.6)) if t>=0.6 else 0)
                           + (0.5*r.uniform(-1,1)*math.exp(-4*(t-1.3)) if t>=1.3 else 0),
    "summon": lambda t, r: 0.4*math.sin(2*math.pi*(60+90*min(t,1.0))*t)*math.exp(-1.2*min(t,1.0))
                           + (0.5*math.sin(2*math.pi*(140+120*min(t-1.0,2.0)/2.0)*(t-1.0)) if t>=1.0 else 0)
                           + (0.8*r.uniform(-1,1)*math.exp(-2.5*(t-2.45))+0.7*math.sin(2*math.pi*50*(t-2.45))*math.exp(-8*(t-2.45)) if t>=2.45 else 0),
    "screen_flash": lambda t, r: r.uniform(-1,1)*math.exp(-2.5*t)*(0.8 if t<0.5 else 0.5)
                                 + (0.8*math.sin(2*math.pi*40*t)*math.exp(-5*t) if t<0.7 else 0),
    "teleport": lambda t, r: (0.45*math.sin(2*math.pi*(300+900*min(t,0.3)/0.3)*t)*math.exp(-1*min(t,0.3))
                              + (0.5*math.sin(2*math.pi*(1400-1100*min(max(0,t-0.3),0.5)/0.5)*(t-0.3))*math.exp(-3*max(0,t-0.3)) if 0.3<=t<1.2 else 0)
                              + (0.55*(r.uniform(-1,1))*math.exp(-6*max(0,t-1.2)) if t>=1.2 else 0)),
    "heal": lambda t, r: (0.3*math.sin(2*math.pi*528*t) + 0.25*math.sin(2*math.pi*792*t)) * min(1, t/0.5)
                         + (0.5*math.sin(2*math.pi*440*t)*math.exp(-2*(t-1.9)) + 0.4*math.sin(2*math.pi*660*t)*math.exp(-3*(t-1.9)) if t>=1.9 else 0),
    "money_rain": lambda t, r: (0.0 if not (0.2 < (t*3) % 1.0 < 0.45) else 0.5*math.sin(2*math.pi*(2200+800*r.random())*t)*math.exp(-8*((t*3)%1.0-0.2)))
                              + 0.12*math.sin(2*math.pi*330*t),
    "hearts": lambda t, r: ((0.7*math.sin(2*math.pi*70*(t%0.75)) * (1 if t%0.75<0.2 else 0.2)) + 0.15*math.sin(2*math.pi*520*t)),
    "anger_flame": lambda t, r: 0.5*math.sin(2*math.pi*(40+30*math.sin(2*math.pi*2*t))*t)
                          + (0.4*r.uniform(-1,1)*math.exp(-3*max(0,t-0.5))*(0.4+0.6*math.sin(2*math.pi*8*t)) ),
    "dizzy": lambda t, r: 0.4*math.sin(2*math.pi*(380+260*math.sin(2*math.pi*2.5*t))*t)
                          + 0.15*math.sin(2*math.pi*1200*t)*math.exp(-2*((t*2)%1)),
    "meteor": lambda t, r: (0.4*(r.uniform(-1,1)+math.sin(2*math.pi*(900-500*t)*t)*0.6)*min(1,t/0.3)
                            + (0.85*r.uniform(-1,1)*math.exp(-4*(t-1.0)) + 0.8*math.sin(2*math.pi*50*(t-1.0))*math.exp(-6*(t-1.0)) + 0.4*r.uniform(-1,1)*math.exp(-20*max(0,(t-1.0)-0.05)) if t>=1.0 else 0)),
    "zoom_punch": lambda t, r: (0.5*math.sin(2*math.pi*(200+1200*min(t,0.3)/0.3)*t)*min(1,t/0.1)
                                + (0.85*math.sin(2*math.pi*65*(t-0.3))*math.exp(-7*(t-0.3)) + 0.6*r.uniform(-1,1)*math.exp(-6*(t-0.3)) + 0.5*math.sin(2*math.pi*1800*(t-0.3))*math.exp(-12*(t-0.3)) if t>=0.3 else 0)),
}

RENDERERS = {
    "fire_burst": (render_fire, 2.0, (90, 60, 30)),
    "freeze": (render_freeze, 2.0, None),
    "thunder_strike": (render_thunder, 2.0, None),
    "slash": (render_slash, 1.5, None),
    "shield": (render_shield, 2.0, None),
    "summon": (render_summon, 3.0, None),
    "screen_flash": (render_flash, 1.5, None),
    "teleport": (render_teleport, 2.0, None),
    "heal": (render_heal, 2.5, None),
    "money_rain": (render_money, 2.5, None),
    "hearts": (render_hearts, 2.0, None),
    "anger_flame": (render_anger, 2.0, None),
    "dizzy": (render_dizzy, 2.0, None),
    "meteor": (render_meteor, 2.5, None),
    "zoom_punch": (render_punch, 1.5, None),
}

if __name__ == "__main__":
    import sys
    names = sys.argv[1:] or list(RENDERERS)
    for name in names:
        render, dur, _ = RENDERERS[name]
        out = os.path.join(FX_ROOT, name)
        n = save_frames(render, dur, out)
        save_wav(os.path.join(out, "audio.wav"), AUDIO[name], dur)
        print(f"✅ {name}: {n}帧/{dur}s")
