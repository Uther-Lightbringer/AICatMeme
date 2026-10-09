import os
import glob
import tempfile
import concurrent.futures
import subprocess
from utils.draw_utils import wrap_text
from core.config import EMOTION_FOLDER, BG_FOLDER, FONT_PATH, FX_FOLDER
import imageio_ffmpeg

# 动态获取当前 Python 环境自带的 ffmpeg 绝对路径
FFMPEG_EXE = "/opt/ffmpeg-bin/ffmpeg" if os.path.exists("/opt/ffmpeg-bin/ffmpeg") else imageio_ffmpeg.get_ffmpeg_exe()

def ff_path(path):
    """把 Windows 路径转换为 FFmpeg 滤镜能识别的安全格式（转义冒号和反斜杠）"""
    return path.replace('\\', '/').replace(':', '\\:')

def write_text_file(temp_dir, filename, text):
    """FFmpeg drawtext 传长文本容易引发引号冲突，最稳妥的做法是把台词写进临时 txt 文件"""
    filepath = os.path.join(temp_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    return ff_path(filepath)

def image_seq_input(png_list):
    """返回 (pattern, start_number)：用 image2 demuxer 直读 PNG 序列，比 concat 稳"""
    d = os.path.dirname(png_list[0])
    start = int(os.path.basename(png_list[0]).split('.')[0])
    return os.path.join(d, "%04d.png"), start


_name_y_cache = {}

def name_y_for(frame_path, scale, y_shift=0, gap=58):
    """角色名紧贴猫头顶：读素材alpha实际头顶位置，按缩放/位移推算drawtext的y"""
    key = (frame_path, scale, y_shift)
    if key in _name_y_cache:
        return _name_y_cache[key]
    from PIL import Image
    im = Image.open(frame_path)
    w, h = im.size
    try:
        top = im.getchannel('A').getbbox()[1]
    except Exception:
        top = 0
    scaled_h = round(h * scale / w)
    cat_top = (1080 - scaled_h) / 2 + y_shift
    val = max(20, int(cat_top + (top / h) * scaled_h - gap))
    _name_y_cache[key] = val
    return val


def create_image_concat_file(png_list, temp_dir, prefix, fps=30):
    """生成 FFmpeg 专用的图片序列 concat 文本，完美规避 Windows 下 glob 支持不稳定的坑"""
    txt_path = os.path.join(temp_dir, f"{prefix}_concat.txt")
    dur = 1.0 / fps
    with open(txt_path, 'w', encoding='utf-8') as f:
        for png in png_list:
            safe_path = png.replace('\\', '/')
            f.write(f"file '{safe_path}'\n")
            f.write(f"duration {dur}\n")
        if png_list:
            safe_last_png = png_list[-1].replace('\\', '/')
            f.write(f"file '{safe_last_png}'\n")
    return txt_path


def process_multi_scene_ffmpeg(index, scene, temp_dir):
    """multi 模式：N 只猫同屏 + 位移进出场。
    每只猫配 at(说话秒) / entrance / exit。
    layout: flat=横向等分(默认) | depth=前后排(近大远小, 后排缩小上移)。
    """
    temp_output = os.path.join(temp_dir, f"scene_{index}.mp4")
    n_all = len(scene['characters'])
    print(f"🔄 [FFmpeg] multi 场景 {index+1}: {scene['title']} ({n_all}只猫, layout={scene.get('layout','flat')})")

    bg_files = glob.glob(os.path.join(BG_FOLDER, f"{scene['place']}.*"))
    if not bg_files:
        raise FileNotFoundError(f"找不到背景素材: {scene['place']}")
    bg_path = bg_files[0]
    bg_is_image = bg_path.lower().endswith(('.png', '.jpg', '.jpeg'))

    cats = []
    for c in scene['characters']:
        frames, audio = resolve_character_frames(c)
        cats.append({'c': c, 'frames': frames, 'audio': audio})

    for ca in cats:
        ca['at'] = float(ca['c'].get('at', 0) or 0)
        ca['dur'] = len(ca['frames']) / 30.0
    total = max(ca['at'] + ca['dur'] for ca in cats) + 0.8

    n = len(cats)
    layout = scene.get('layout', 'flat') or 'flat'
    slot_w = 1080.0 / n
    base_scale = int(slot_w * 0.68)

    # --- 站位：flat 全员等分同层；depth 偶数index后排(缩小/上移)，奇数前排(放大/下移) ---
    for i, ca in enumerate(cats):
        ca['x'] = int(i * slot_w + slot_w / 2)
        ca['row'] = (0 if i % 2 == 0 else 1) if (layout == 'depth' and n >= 2) else 0
        if layout == 'depth' and ca['row'] == 0:
            ca['scale'] = int(base_scale * 0.78)
            ca['y_shift'] = -150
        elif layout == 'depth':
            ca['scale'] = int(base_scale * 0.92)
            ca['y_shift'] = 90
        else:
            ca['scale'] = base_scale
            ca['y_shift'] = 0

    def _sgn(v):
        return f"+{v}" if v >= 0 else f"-{abs(v)}"

    def _xy_expr(ca):
        at, dur, x = ca['at'], ca['dur'], ca['x']
        ent = ca['c'].get('entrance', 'none') or 'none'
        ext = ca['c'].get('exit', 'none') or 'none'
        xoff_in = -500 if ent == 'left' else (500 if ent == 'right' else 0)
        yoff_in = 500 if ent == 'bottom' else (-500 if ent == 'top' else 0)
        xoff_out = -600 if ext == 'left' else (600 if ext == 'right' else 0)
        yoff_out = -600 if ext == 'top' else (600 if ext == 'bottom' else 0)
        ybase = f"((H-h)/2{_sgn(ca['y_shift'])})"
        xexpr = f"({x}{_sgn(xoff_in)}*(1-min(max((t-{at}+0.6)/0.6,0),1)){_sgn(xoff_out)}*max(0,(t-{at+dur})/0.6))"
        yexpr = f"({ybase}{_sgn(yoff_in)}*(1-min(max((t-{at}+0.6)/0.6,0),1)){_sgn(yoff_out)}*max(0,(t-{at+dur})/0.6))"
        return xexpr, yexpr

    cmd = [FFMPEG_EXE, "-y"]
    if bg_is_image:
        cmd.extend(["-loop", "1", "-framerate", "24", "-i", bg_path])
    else:
        cmd.extend(["-stream_loop", "-1", "-i", bg_path])

    filters = []
    texts = []
    a_labels = []
    in_idx = 1
    for i, ca in enumerate(cats):
        pat, st = image_seq_input(ca['frames'])
        cmd.extend(["-framerate", "30", "-start_number", str(st), "-i", pat])
        ca['anim_i'] = in_idx; in_idx += 1
        # 静态层已移除：改为动态序列循环填满整幕，避免"定格帧叠动态帧"的双影
        if ca['audio']:
            cmd.extend(["-i", ca['audio']])
        else:
            cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
        ca['aud_i'] = in_idx; in_idx += 1
        filters.append(f"[{ca['anim_i']}:v]scale={ca['scale']}:-1,setsar=1[a{i}]")

        x, at, dur = ca['x'], ca['at'], ca['dur']
        win_s = max(0, at - 0.7)
        win_e = min(total, at + dur + 0.7)
        name_txt = write_text_file(temp_dir, f"mn_{index}_{i}.txt", ca['c']['name'])
        dia_txt = write_text_file(temp_dir, f"md_{index}_{i}.txt", wrap_text(f"*{ca['c']['text']}", 12))
        ca['name_y'] = name_y_for(ca['frames'][0], ca['scale'], ca['y_shift'])
        texts.append(f"drawtext=fontfile='{ff_path(FONT_PATH)}':expansion=none:textfile='{name_txt}':x={x}-text_w/2:y={ca['name_y']}:fontsize=44:fontcolor=yellow:borderw=3:bordercolor=black:box=1:boxcolor=black@0.45:boxborderw=16:enable='between(t,{win_s},{win_e})'")
        dia_y = 1080 - 210 + (-80 if (layout == 'depth' and ca['row'] == 0) else 0)
        texts.append(f"drawtext=fontfile='{ff_path(FONT_PATH)}':expansion=none:textfile='{dia_txt}':x={x}-text_w/2:y={dia_y}:fontsize=48:fontcolor=white:borderw=3:bordercolor=black:box=1:boxcolor=black@0.45:boxborderw=16:enable='between(t,{at},{at+min(dur,2.8)})'")

        delay_ms = int(at * 1000)
        filters.append(f"[{ca['aud_i']}:a]atrim=duration={at+dur},adelay={delay_ms}|{delay_ms},asetpts=PTS-STARTPTS[aa{i}]")
        a_labels.append(f"[aa{i}]")

    # --- 合成：depth 下后排(row0)先画当底层，前排(row1)后画盖上面 ---
    filters.append(f"[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,setsar=1,trim=duration={total}[bg]")
    order = sorted(range(n), key=lambda i: cats[i]['row'])
    prev_v = "bg"
    for seq, i in enumerate(order):
        ca = cats[i]
        at, dur = ca['at'], ca['dur']
        win_s = max(0, at - 0.7)
        win_e = min(total, at + dur + 0.7)
        xexpr, yexpr = _xy_expr(ca)
        # 动态序列循环填满从入场前到退场后的整个窗口，取代原来的静态垫底层
        nf = len(ca['frames'])
        filters.append(f"[a{i}]loop=loop=-1:size={nf}:start=0,fps=30,trim=duration={total},setpts=PTS-STARTPTS[al{i}]")
        filters.append(f"[{prev_v}][al{i}]overlay=x='{xexpr}':y='{yexpr}':enable='between(t,{win_s},{win_e})'[va{seq}]")
        prev_v = f"va{seq}"

    # 特效: 对波(可选, 帧按 dialogue 双猫口位 290/790 绘制)
    fx_name = (scene.get('fx') or 'none').strip()
    fx_on = fx_name not in ('', 'none') and os.path.isdir(os.path.join(FX_FOLDER, fx_name))
    if fx_on:
        fx_dir = os.path.join(FX_FOLDER, fx_name)
        fx_frames = sorted(glob.glob(os.path.join(fx_dir, "frames", "*.png")))
        if not fx_frames:
            raise FileNotFoundError(f"特效包缺帧: {fx_dir}/frames/")
        fx_pat, fx_start = image_seq_input(fx_frames)
        cmd.extend(["-framerate", "30", "-start_number", str(fx_start), "-i", fx_pat])
        fx_i = in_idx; in_idx += 1
        fx_audio = os.path.join(fx_dir, "audio.wav")
        if not os.path.exists(fx_audio):
            fx_audio = os.path.join(fx_dir, "audio.mp3")
        cmd.extend(["-i", fx_audio] if os.path.exists(fx_audio) else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
        fx_aud_i = in_idx; in_idx += 1
        fx_dur = len(fx_frames) / 30.0
        fx_at = float(scene.get('fx_at') or 0) or max(0.0, total - fx_dur - 0.6)
        fx_boom = float(scene.get('fx_boom', 2.45) or 0)
        print(f"⚡ [FX] {fx_name} at={fx_at:.1f}s dur={fx_dur:.1f}s")
        filters.append(f"[{fx_i}:v]setpts=PTS+{fx_at}/TB[fxv]")
        filters.append(f"[{prev_v}][fxv]overlay=x=0:y=0:eof_action=pass[vfx]")
        shk = (",scale=1120:1120,setsar=1,crop=1080:1080:"
               f"x='(in_w-out_w)/2+16*sin(2*PI*20*(t-{fx_at+fx_boom}))*between(t,{fx_at+fx_boom-0.25},{fx_at+fx_boom+0.5})':"
               f"y='(in_h-out_h)/2+13*sin(2*PI*17*(t-{fx_at+fx_boom}))*between(t,{fx_at+fx_boom-0.25},{fx_at+fx_boom+0.5})'")
        filters.append(f"[vfx]{','.join(texts)}{shk}[vout]")
        fx_delay = int(fx_at * 1000)
        filters.append(f"[{fx_aud_i}:a]atrim=duration={fx_dur},adelay={fx_delay}|{fx_delay},asetpts=PTS-STARTPTS[af]")
        filters.append(f"{''.join(a_labels)}[af]amix=inputs={n+1}:duration=longest:normalize=0[aout]")
    else:
        filters.append(f"[{prev_v}]{','.join(texts)}[vout]")
        filters.append(f"{''.join(a_labels)}amix=inputs={n}:duration=longest:normalize=0[aout]")

    cmd.extend(["-filter_complex", ";".join(filters)])
    cmd.extend(["-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-threads", "2",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                "-r", "24", "-t", str(total), temp_output])
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"❌ multi FFmpeg 错误:\n{result.stderr[-2000:]}")
        raise RuntimeError(f"multi 场景渲染失败: {scene['title']}")
    return temp_output


def process_single_scene_ffmpeg(index, scene, temp_dir):
    """
    独立构建并执行纯 FFmpeg 命令行，极速渲染单个场景
    """
    if scene.get('scene_type') == 'multi' or len(scene.get('characters', [])) > 2:
        return process_multi_scene_ffmpeg(index, scene, temp_dir)
    temp_output = os.path.join(temp_dir, f"scene_{index}.mp4")
    print(f"🔄 [FFmpeg] 正在全速处理场景 {index+1}: {scene['title']}")

    # 1. 获取背景
    bg_files = glob.glob(os.path.join(BG_FOLDER, f"{scene['place']}.*"))
    if not bg_files:
        raise FileNotFoundError(f"找不到背景素材: {scene['place']}")
    bg_path = bg_files[0]
    bg_is_image = bg_path.lower().endswith(('.png', '.jpg', '.jpeg'))

    # 字幕和字体配置
    font_safe = ff_path(FONT_PATH)
    title_txt = write_text_file(temp_dir, f"title_{index}.txt", scene['title'])
    
    chars = scene['characters']
    stype = scene['scene_type']

    def get_emo_assets(c_or_emo):
        if isinstance(c_or_emo, dict):
            return resolve_character_frames(c_or_emo)
        return resolve_character_frames({'name': '', 'emotion': c_or_emo, 'char': ''})

    # --- 开始构建 FFmpeg 指令 ---
    cmd = [FFMPEG_EXE, "-y"]

    # 输入 0: 背景
    if bg_is_image:
        cmd.extend(["-loop", "1", "-framerate", "24", "-i", bg_path])
    else:
        cmd.extend(["-stream_loop", "-1", "-i", bg_path])

    filters = []
    texts = []
    
    # 基础文字滤镜参数（去掉了背景框，加上黑色描边）
    title_filter = f"drawtext=fontfile='{font_safe}':expansion=none:textfile='{title_txt}':x=(w-text_w)/2:y=50:fontsize=75:fontcolor=yellow:borderw=4:bordercolor=black"
    
    if stype == 'single' and len(chars) > 0:
        frames, audio = get_emo_assets(chars[0])
        dur = len(frames) / 30.0
        concat_txt = create_image_concat_file(frames, temp_dir, f"single_{index}")
        pat, start = image_seq_input(frames)
        # 输入 1 & 2: 序列与音频
        cmd.extend(["-framerate", "30", "-start_number", str(start), "-i", pat])
        cmd.extend(["-i", audio] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])

        # 特效包(可选, 输入3=帧 4=音频)
        fx_name = (scene.get('fx') or 'none').strip()
        fx_on = fx_name not in ('', 'none') and os.path.isdir(os.path.join(FX_FOLDER, fx_name))
        if fx_on:
            fx_dir = os.path.join(FX_FOLDER, fx_name)
            fx_frames = sorted(glob.glob(os.path.join(fx_dir, "frames", "*.png")))
            if not fx_frames:
                raise FileNotFoundError(f"特效包缺帧: {fx_dir}/frames/")
            fx_pat, fx_start = image_seq_input(fx_frames)
            cmd.extend(["-framerate", "30", "-start_number", str(fx_start), "-i", fx_pat])
            fx_audio = os.path.join(fx_dir, "audio.wav")
            if not os.path.exists(fx_audio):
                fx_audio = os.path.join(fx_dir, "audio.mp3")
            cmd.extend(["-i", fx_audio] if os.path.exists(fx_audio) else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
            fx_i, fx_aud_i = 3, 4
            fx_dur = len(fx_frames) / 30.0
            fx_at = float(scene.get('fx_at') or 0) or max(0.0, dur - fx_dur - 0.6)
            fx_boom = float(scene.get('fx_boom', 2.45) or 0)
            print(f"⚡ [FX] {fx_name} at={fx_at:.1f}s dur={fx_dur:.1f}s")

        # 构建滤镜链
        filters.append(f"[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,setsar=1,trim=duration={dur}[bg]")
        filters.append(f"[1:v]scale=750:-1,setsar=1[anim]")
        filters.append(f"[bg][anim]overlay=(W-w)/2:(H-h)/2[v1]")
        
        # 构建文字
        name_txt = write_text_file(temp_dir, f"name_{index}.txt", chars[0]['name'])
        dialogue = wrap_text(f"*{chars[0]['text']}", 20)  # 修改为 20 字符换行
        dialogue_txt = write_text_file(temp_dir, f"dial_{index}.txt", dialogue)
        
        texts.append(title_filter)
        # 单人场景：名字紧贴猫头顶（按素材alpha头顶位置推算），台词保留在底部
        name_y = name_y_for(frames[0], 750, 0)
        texts.append(f"drawtext=fontfile='{font_safe}':expansion=none:textfile='{name_txt}':x=(w-text_w)/2:y={name_y}:fontsize=52:fontcolor=yellow:borderw=3:bordercolor=black:box=1:boxcolor=black@0.45:boxborderw=16")
        texts.append(f"drawtext=fontfile='{font_safe}':expansion=none:textfile='{dialogue_txt}':x=(w-text_w)/2:y=1080-220:fontsize=52:fontcolor=white:borderw=3:bordercolor=black:box=1:boxcolor=black@0.45:boxborderw=16:line_spacing=-30")
        
        if fx_on:
            filters.append(f"[{fx_i}:v]setpts=PTS+{fx_at}/TB[fxv]")
            filters.append(f"[v1][fxv]overlay=x=0:y=0:eof_action=pass[v1fx]")
            shk = (",scale=1120:1120,setsar=1,crop=1080:1080:"
                   f"x='(in_w-out_w)/2+16*sin(2*PI*20*(t-{fx_at+fx_boom}))*between(t,{fx_at+fx_boom-0.25},{fx_at+fx_boom+0.5})':"
                   f"y='(in_h-out_h)/2+13*sin(2*PI*17*(t-{fx_at+fx_boom}))*between(t,{fx_at+fx_boom-0.25},{fx_at+fx_boom+0.5})'")
            filters.append(f"[v1fx]{','.join(texts)}{shk}[vout]")
            fx_delay = int(fx_at * 1000)
            filters.append(f"[2:a]atrim=duration={dur},asetpts=PTS-STARTPTS[a1]")
            filters.append(f"[{fx_aud_i}:a]atrim=duration={fx_dur},adelay={fx_delay}|{fx_delay},asetpts=PTS-STARTPTS[af]")
            filters.append("[a1][af]amix=inputs=2:duration=longest:normalize=0[aout]")
        else:
            filters.append(f"[v1]{','.join(texts)}[vout]")
            filters.append(f"[2:a]atrim=duration={dur}[aout]")
        total_dur = dur

    elif stype == 'dialogue' and len(chars) >= 2:
        l_frames, l_audio = get_emo_assets(chars[0])
        r_frames, r_audio = get_emo_assets(chars[1])
        
        dur_l = len(l_frames) / 30.0
        dur_r = len(r_frames) / 30.0
        total_dur = dur_l + dur_r
        
        lpat, lstart = image_seq_input(l_frames)
        rpat, rstart = image_seq_input(r_frames)

        # 输入 1:左侧动图 2:右侧动图
        cmd.extend(["-framerate", "30", "-start_number", str(lstart), "-i", lpat])
        cmd.extend(["-framerate", "30", "-start_number", str(rstart), "-i", rpat])
        
        # 输入 3:左音频 4:右音频
        cmd.extend(["-i", l_audio] if l_audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
        cmd.extend(["-i", r_audio] if r_audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])

        # 特效: 双猫对波(可选)
        fx_name = (scene.get('fx') or 'none').strip()
        fx_on = fx_name not in ('', 'none') and os.path.isdir(os.path.join(FX_FOLDER, fx_name))
        if fx_on:
            fx_dir = os.path.join(FX_FOLDER, fx_name)
            fx_frames = sorted(glob.glob(os.path.join(fx_dir, "frames", "*.png")))
            if not fx_frames:
                raise FileNotFoundError(f"特效包缺帧: {fx_dir}/frames/")
            fx_pat, fx_start = image_seq_input(fx_frames)
            cmd.extend(["-framerate", "30", "-start_number", str(fx_start), "-i", fx_pat])
            fx_audio = os.path.join(fx_dir, "audio.wav")
            cmd.extend(["-i", fx_audio] if os.path.exists(fx_audio) else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
            fx_i, fx_aud_i = 5, 6
            fx_dur = len(fx_frames) / 30.0
            fx_at = float(scene.get('fx_at') or 0) or max(0.0, total_dur - fx_dur - 0.6)
            fx_boom = float(scene.get('fx_boom', 2.45) or 0)
            print(f"⚡ [FX] {fx_name} at={fx_at:.1f}s dur={fx_dur:.1f}s")

        # 视频合成链 (利用 enable 滤镜实现极速帧切换)
        filters.append(f"[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,setsar=1,trim=duration={total_dur}[bg]")
        # 双猫：各自动态序列循环填满自己那一半时长，不再用"静态尾帧垫底"（消除双影）
        nl, nr = len(l_frames), len(r_frames)
        filters.append(f"[1:v]scale=520:-1,setsar=1,loop=loop=-1:size={nl}:start=0,fps=30,trim=duration={total_dur},setpts=PTS-STARTPTS[la]")
        filters.append(f"[2:v]scale=520:-1,setsar=1,loop=loop=-1:size={nr}:start=0,fps=30,trim=duration={total_dur},setpts=PTS-STARTPTS+{dur_l}/TB[ra]")

        filters.append(f"[bg][la]overlay=x=30:y=(H-h)/2:enable='lt(t,{dur_l})'[v2]")
        filters.append(f"[v2][ra]overlay=x=530:y=(H-h)/2:enable='gte(t,{dur_l})'[v4]")

        # 文本生成
        ln_txt = write_text_file(temp_dir, f"ln_{index}.txt", chars[0]['name'])
        rn_txt = write_text_file(temp_dir, f"rn_{index}.txt", chars[1]['name'])
        ld_txt = write_text_file(temp_dir, f"ld_{index}.txt", wrap_text(f"*{chars[0]['text']}", 10))  # 修改为 10 字符换行
        rd_txt = write_text_file(temp_dir, f"rd_{index}.txt", wrap_text(f"*{chars[1]['text']}", 10))  # 修改为 10 字符换行

        texts.append(title_filter)
        # 双人场景：名字紧贴各自猫头顶（scale=520，y居中无位移）
        l_name_y = name_y_for(l_frames[0], 520, 0)
        r_name_y = name_y_for(r_frames[0], 520, 0)
        texts.append(f"drawtext=fontfile='{font_safe}':expansion=none:textfile='{ln_txt}':x=290-text_w/2:y={l_name_y}:fontsize=52:fontcolor=yellow:borderw=3:bordercolor=black:box=1:boxcolor=black@0.45:boxborderw=16")
        texts.append(f"drawtext=fontfile='{font_safe}':expansion=none:textfile='{rn_txt}':x=790-text_w/2:y={r_name_y}:fontsize=52:fontcolor=yellow:borderw=3:bordercolor=black:box=1:boxcolor=black@0.45:boxborderw=16")
        
        # 台词留在底部，同步修正左侧台词中心对齐 (x=290)
        texts.append(f"drawtext=fontfile='{font_safe}':expansion=none:textfile='{ld_txt}':enable='lt(t,{dur_l})':x=290-text_w/2:y=1080-260:fontsize=52:fontcolor=white:borderw=3:bordercolor=black:box=1:boxcolor=black@0.45:boxborderw=16:line_spacing=-30")
        texts.append(f"drawtext=fontfile='{font_safe}':expansion=none:textfile='{rd_txt}':enable='gte(t,{dur_l})':x=790-text_w/2:y=1080-260:fontsize=52:fontcolor=white:borderw=3:bordercolor=black:box=1:boxcolor=black@0.45:boxborderw=16:line_spacing=-30")
        
        if fx_on:
            # 对波: 猫合成后叠特效帧 → 字幕 → 爆炸瞬间屏幕震动(scale+crop位移)
            # setpts把fx帧时钟平移到fx_at, overlay窗口双保险; eof_action=pass播完即消失(不定格)
            filters.append(f"[{fx_i}:v]setpts=PTS+{fx_at}/TB[fxv]")
            filters.append(f"[v4][fxv]overlay=x=0:y=0:eof_action=pass[v4fx]")
            shk = (",scale=1120:1120,setsar=1,crop=1080:1080:"
                   f"x='(in_w-out_w)/2+16*sin(2*PI*20*(t-{fx_at+fx_boom}))*between(t,{fx_at+fx_boom-0.25},{fx_at+fx_boom+0.5})':"
                   f"y='(in_h-out_h)/2+13*sin(2*PI*17*(t-{fx_at+fx_boom}))*between(t,{fx_at+fx_boom-0.25},{fx_at+fx_boom+0.5})'")
            filters.append(f"[v4fx]{','.join(texts)}{shk}[vout]")
        else:
            filters.append(f"[v4]{','.join(texts)}[vout]")

        # 音频混合 (右侧音频延后 dur_l 毫秒)
        delay_ms = int(dur_l * 1000)
        filters.append(f"[3:a]atrim=duration={dur_l},asetpts=PTS-STARTPTS[a1]")
        filters.append(f"[4:a]atrim=duration={dur_r},adelay={delay_ms}|{delay_ms},asetpts=PTS-STARTPTS[a2]")
        if fx_on:
            fx_delay = int(fx_at * 1000)
            filters.append(f"[{fx_aud_i}:a]atrim=duration={fx_dur},adelay={fx_delay}|{fx_delay},asetpts=PTS-STARTPTS[af]")
            filters.append("[a1][a2][af]amix=inputs=3:duration=longest:normalize=0[aout]")
        else:
            filters.append("[a1][a2]amix=inputs=2:duration=longest:normalize=0[aout]")

    filter_complex = ";".join(filters)
    cmd.extend(["-filter_complex", filter_complex])
    
    # 输出配置 (硬编码最高效的 x264 参数，速度起飞)
    cmd.extend([
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-threads", "2",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-r", "24", "-t", str(total_dur),
        temp_output
    ])

    # 执行命令
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"❌ FFmpeg 错误日志:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg 渲染失败，场景: {scene['title']}")

    return temp_output


def resolve_character_frames(c):
    """统一素材解析：优先 image_assets 图片素材库，回落项目内置 meme/<情绪>。

    - c 是 Character dict（含 name/emotion/char）
    - 若 c['char'] 非空，或 c['emotion'] 命中 image_assets：
        从 image_assets 取素材（单图会自动动画化），返回 (frames, audio)
    - 否则走原逻辑：meme/<emotion>/frames + audio.mp3
    """
    from core.image_assets import is_image_asset, resolve_assets
    role = (c.get('char') or '').strip()
    emo = (c.get('emotion') or '').strip()

    # 判定是否使用图片素材
    use_img = False
    img_role, img_emo = None, None
    if role and is_image_asset(role):
        use_img = True
        img_role, img_emo = role, (emo or role)
    elif emo and is_image_asset(emo):
        use_img = True
        img_role, img_emo = emo, emo

    if use_img:
        try:
            frames = resolve_assets(img_role, img_emo)
            if frames:
                return frames, None   # 图片素材无配音，静音处理
        except Exception as e:
            print(f"⚠️ 图片素材加载失败({img_role}/{img_emo}): {e}，回落内置情绪")

    # 内置情绪素材
    base = os.path.join(EMOTION_FOLDER, emo)
    frames = sorted(glob.glob(os.path.join(base, "frames", "*.png")))
    if not frames:
        raise FileNotFoundError(f"找不到帧: {emo}")
    audio = os.path.join(base, "audio.mp3")
    has_audio = os.path.exists(audio) and os.path.getsize(audio) > 2048
    return frames, (audio if has_audio else None)


def create_video(data, output_path):
    """主控入口：并行调度 FFmpeg 渲染，并使用极速 Copy 模式拼接最终视频"""
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"🚀 [FFmpeg引擎] 开启并发渲染，共 {len(data)} 个场景...")
        
        results = [None] * len(data)
        # 串行渲染：1.8G 小机上并发 ffmpeg 会触发 x264 "Invalid argument" 偶发崩溃，稳字第一
        for i, scene in enumerate(data):
            try:
                results[i] = process_single_scene_ffmpeg(i, scene, temp_dir)
                print(f"✅ 场景 {i+1} 压制完成！")
            except Exception as e:
                print(f"⚠️ 场景 {i+1} 首次渲染失败({str(e)[:80]})，自动重试一次...")
                try:
                    results[i] = process_single_scene_ffmpeg(i, data[i], temp_dir)
                    print(f"✅ 场景 {i+1} 重试成功！")
                except Exception as e2:
                    print(f"❌ 场景 {i+1} 重试仍失败: {str(e2)[:120]}")
                    return None

        if any(res is None for res in results):
            return None

        # 🎬 秒级无损拼接
        print("🎬 正在无损秒级拼接最终视频...")
        concat_list_path = os.path.join(temp_dir, "final_concat.txt")
        with open(concat_list_path, 'w', encoding='utf-8') as f:
            for mp4 in results:
                safe_mp4 = mp4.replace('\\', '/')
                f.write(f"file '{safe_mp4}'\n")

        # 使用 -c copy 直接复制视频流，无需重新编码，1秒内完成！
        concat_cmd = [
            FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0", 
            "-i", concat_list_path, "-c", "copy", output_path
        ]
        
        res = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0:
            print("🎉 FFmpeg 渲染引擎全流程完成！速度遥遥领先。")
            return output_path
        else:
            print(f"❌ 最终拼接失败:\n{res.stderr.decode('utf-8')}")
            return None
