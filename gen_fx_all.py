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

# ============================================================ 音频配方
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
}

RENDERERS = {
    "fire_burst": (render_fire, 2.0, (90, 60, 30)),
    "freeze": (render_freeze, 2.0, None),
    "thunder_strike": (render_thunder, 2.0, None),
    "slash": (render_slash, 1.5, None),
    "shield": (render_shield, 2.0, None),
    "summon": (render_summon, 3.0, None),
    "screen_flash": (render_flash, 1.5, None),
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
