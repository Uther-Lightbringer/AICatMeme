"""
text_style.py — 统一文字样式工厂（猫meme漫画描边风）

背景：ffmpeg 的 drawtext 只支持**单层描边**（borderw + bordercolor）。
参考"猫meme日记"等成品视频，主流样式是**三层**：黄字填充 + 红描边 + 黑外描边
（漫画/表情包那种醒目感）。

实现技巧：对**同一段文字叠加多个 drawtext**，每个用不同粗细的 borderw，
从**外到内**依次绘制（先画最粗的黑边、再画中等的红边、最后画黄字填充），
后面的 pass 盖住前面 pass 的内部，最终形成多层色环。

用法：
    from core.text_style import name_text, dialogue_text, title_text
    texts.append(name_text(font, txtfile, x_expr, y, fontsize, enable))
"""

# 调色板（从参考成品逐像素取样确认）
# 名字：纯深黄填充，无描边
# 台词：纯白填充，无描边
YELLOW = "0xF5B700"      # 深黄填充（更饱和、更深，不透明）
GOLD = "0xFFD24A"        # 金色填充（名字用）
RED = "0xD00B09"         # 备用红描边
BLACK = "black"
WHITE = "0xFFFFFF"       # 纯白（不透明）

# 预设：样式
STYLE_MEME = "meme"       # 黄字+红边+黑边（备用，漫画风）
STYLE_PLAIN = "plain"     # 白字+黑边+半透明底条（原项目默认）
STYLE_TITLE = "title"     # 黄字+黑边（标题大字）
STYLE_REF = "ref"         # 完全参照参考图：黄字黑边（名字）
STYLE_REF_WHITE = "ref_white"  # 完全参照参考图：白字黑边（台词）


def _layers(style, font, txtfile, x, y, fontsize, extra="", enable=None):
    """
    返回该样式对应的 drawtext 列表（按绘制顺序：外→内）。
    x/y 支持表达式（如 "290-text_w/2"）；enable 为可选时间窗表达式。
    """
    en = f":enable='{enable}'" if enable else ""
    common = f"fontfile='{font}':expansion=none:textfile='{txtfile}':x={x}:y={y}:fontsize={fontsize}"

    if style == STYLE_MEME:
        # 三层：黑边(最粗) → 红边(中) → 黄填充
        base_bw = max(4, round(fontsize * 0.16))     # 黑边 ≈ 字号16%
        red_bw = max(3, round(fontsize * 0.09))      # 红边 ≈ 字号9%
        return [
            f"drawtext={common}:fontcolor={YELLOW}:borderw={base_bw}:bordercolor={BLACK}{extra}{en}",
            f"drawtext={common}:fontcolor={YELLOW}:borderw={red_bw}:bordercolor={RED}{extra}{en}",
            f"drawtext={common}:fontcolor={YELLOW}{extra}{en}",
        ]

    if style == STYLE_TITLE:
        base_bw = max(4, round(fontsize * 0.14))
        return [
            f"drawtext={common}:fontcolor={YELLOW}:borderw={base_bw}:bordercolor={BLACK}{extra}{en}",
            f"drawtext={common}:fontcolor={YELLOW}{extra}{en}",
        ]

    if style == STYLE_REF:
        # 名字：纯黄填充，无轮廓
        return [
            f"drawtext={common}:fontcolor={YELLOW}{extra}{en}",
        ]

    if style == STYLE_REF_WHITE:
        # 台词：纯白填充，无轮廓
        return [
            f"drawtext={common}:fontcolor={WHITE}{extra}{en}",
        ]

    # STYLE_PLAIN：白字 + 黑边 + 半透明底条（原行为）
    return [
        f"drawtext={common}:fontcolor={WHITE}:borderw=3:bordercolor={BLACK}:"
        f"box=1:boxcolor=black@0.45:boxborderw=16{extra}{en}"
    ]


def text_layers(style, font, txtfile, x, y, fontsize, extra="", enable=None):
    return _layers(style, font, txtfile, x, y, fontsize, extra=extra, enable=enable)


# 便捷封装 ---------------------------------------------------------------

def name_text(font, txtfile, x, y, fontsize, style=STYLE_MEME, enable=None, extra=""):
    """角色名（默认漫画三层描边）"""
    return _layers(style, font, txtfile, x, y, fontsize, extra=extra, enable=enable)


def dialogue_text(font, txtfile, x, y, fontsize, style=STYLE_MEME, enable=None,
                  line_spacing=None, extra=""):
    """台词（默认漫画三层描边）"""
    if line_spacing is not None:
        extra = f"{extra}:line_spacing={line_spacing}"
    return _layers(style, font, txtfile, x, y, fontsize, extra=extra, enable=enable)


def title_text(font, txtfile, x, y, fontsize, style=STYLE_TITLE, enable=None, extra=""):
    """标题（默认黄字黑边大字）"""
    return _layers(style, font, txtfile, x, y, fontsize, extra=extra, enable=enable)
