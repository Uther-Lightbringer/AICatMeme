"""生成简洁'空框'版天台背景：大字留白、无遮挡物，替换原杂乱 rooftop.jpg"""
from PIL import Image, ImageDraw, ImageFilter
import random

W = H = 1080
img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img)

# 1. 天空渐变：顶部浅灰蓝 -> 地平线暖灰
for y in range(0, 560):
    t = y / 560
    r = int(196 - 40 * t); g = int(205 - 35 * t); b = int(220 - 25 * t)
    d.line([(0, y), (W, y)], fill=(r, g, b))

# 2. 远景城市剪影（很淡，一抹即止，不抢字）
skyline = [(0, 300), (90, 300), (90, 210), (150, 210), (150, 260), (240, 260),
           (240, 180), (330, 180), (330, 250), (430, 250), (430, 205), (520, 205),
           (520, 265), (640, 265), (640, 190), (760, 190), (760, 240), (880, 240),
           (880, 200), (1080, 200), (1080, 300)]
d.polygon([(x, y) for x, y in skyline], fill=(150, 158, 172))
d.polygon([(x, y + 220) for x, y in skyline], fill=(168, 174, 186))  # 远一层

# 3. 露台地面：暖灰石砖，简单横缝
d.rectangle([0, 560, W, H], fill=(176, 168, 156))
for y in range(600, H, 90):
    d.line([(0, y), (W, y)], fill=(160, 152, 140), width=3)
random.seed(7)
for y in range(560, H, 90):
    for x in range(0, W, 120):
        off = random.choice([0, 45, 90])
        d.line([(x + off, y), (x + off, y + 90)], fill=(160, 152, 140), width=3)

# 4. 铁艺围栏：纤细竖杆 + 顶杆（画面1/3高处一根，其余留白）
rail_top = 470
d.rectangle([0, rail_top, W, rail_top + 14], fill=(58, 60, 66))          # 顶杆
d.rectangle([0, rail_top + 34, W, rail_top + 44], fill=(58, 60, 66))      # 腰杆
for x in range(10, W, 42):
    d.rectangle([x, rail_top, x + 5, rail_top + 150], fill=(58, 60, 66))  # 竖杆
    d.line([(x + 2, rail_top + 8), (x + 2, rail_top + 22)], fill=(58, 60, 66), width=4)

# 5. 两盆边缘绿植（只在最左右角落，不碰中区字/猫）
def pot(cx):
    d.polygon([(cx - 46, H - 60), (cx + 46, H - 60), (cx + 32, H - 160), (cx - 32, H - 160)],
              fill=(120, 96, 78))
    for dx, r in [(-28, 46), (10, 54), (36, 42)]:
        d.ellipse([cx + dx - r, H - 235 - r, cx + dx + r, H - 235 + r], fill=(86, 122, 76))
pot(90); pot(990)

# 6. 轻噪点去掉塑料感 + 轻微暗角
img = img.filter(ImageFilter.GaussianBlur(0.6))
vig = Image.new("L", (W, H), 0)
vd = ImageDraw.Draw(vig)
vd.ellipse([-260, -260, W + 260, H + 260], fill=90)
black = Image.new("RGB", (W, H), (20, 22, 26))
img = Image.composite(black, img, vig.point(lambda v: 255 - v))

img.save("/opt/AICatMeme/backgrounds/rooftop.jpg", quality=90)
print("ok", img.size)
