import os
import time
import json
import secrets
import string
import redis
import glob
from flask import Flask, request, jsonify
from flask_cors import CORS
from waitress import serve
from openai import OpenAI
from core import config as cfg
from core.models import StoryAnalysis
from utils.logger import initialize_csv, log_submission
from services.video_service import create_video

app = Flask(__name__)
CORS(app)

try:
    r = redis.Redis(host=cfg.REDIS_HOST, port=cfg.REDIS_PORT, db=0, decode_responses=True)
    r.ping()
except redis.ConnectionError:
    print('警告: 无法连接到 Redis 服务器，限流功能暂时停用。')

def generate_password(length=6):
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def process_request(data_json, client_ip):
    story = data_json.get('story', '')
    user_api_key = data_json.get('api_key') or cfg._ak
    model_name = data_json.get('model', cfg.DEEPSEEK_MODEL)
    try:
        client = OpenAI(
            api_key=user_api_key,
            base_url=cfg.DEEPSEEK_BASE_URL
        )
        prompt_text = f'分析以下故事，将其拆分为连续的镜头。故事：{story}'
        schema_str = json.dumps(StoryAnalysis.model_json_schema(), ensure_ascii=False)
        system_instruction = (
            "镜头模式选择规则：只有1个角色用single；正好2个角色对话用dialogue；3个及以上角色或群戏/围观场景必须用multi，multi须为每个角色填at(说话秒数依次递增)，角色>=3时用layout=depth(前后排)，2个角色用flat。\n"
            "特效使用规则：故事高潮处双方大招对轰/绝招对决的镜头，scene填 fx=\"beam_clash\"（双猫对波：蓄力→光束僵持对轰→爆炸震屏，3.5秒），普通叙事镜头 fx=\"none\"。同一故事最多用1-2次，用在最爆炸的转折点。\n"
            '你是一个专业的AI视频导播。请根据用户提供的故事生成连续的镜头脚本。\n'
            f'必须严格按照以下 JSON Schema 格式返回结果（只返回合法的 JSON 对象，不要包含 markdown 标记）：\n{schema_str}\n'
            '重要要求：台词文本使用中文，简洁有力。'
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {'role': 'system', 'content': system_instruction},
                {'role': 'user', 'content': prompt_text}
            ],
            response_format={'type': 'json_object'},
            temperature=0.7,
        )
        result_text = response.choices[0].message.content
        if result_text.startswith('```'):
            result_text = result_text.strip('`').removeprefix('json').strip()
        parsed_json = json.loads(result_text)
        generated_data = parsed_json.get('scenes', [])
        if not generated_data and isinstance(parsed_json, list):
            generated_data = parsed_json
        for sc in generated_data:
            if not isinstance(sc, dict):
                continue
            chs = sc.get('characters') or []
            n = len(chs)
            if n <= 1:
                sc['scene_type'] = 'single'
            elif n == 2 and sc.get('scene_type') != 'multi':
                sc['scene_type'] = 'dialogue'
            else:
                sc['scene_type'] = 'multi'
                # 自动补 at：没填 at 的角色按顺序每人预留自己的动画时长
                acc = 0.0
                for ci, ch in enumerate(chs):
                    if not ch.get('at'):
                        ch['at'] = acc
                    acc = float(ch['at']) + 4.0
            sc['characters'] = chs
            # 背景兜底：LLM 偶尔编不存在的场景名（如"会议室"），统一回落 others
            if not glob.glob(os.path.join(cfg.BG_FOLDER, f"{sc.get('place', 'others')}.*")):
                sc['place'] = 'others'
            # 特效兜底：LLM 编不存在的特效名时置空（特效包先要在 fx/ 下生成好）
            fx_val = (sc.get('fx') or 'none').strip()
            if fx_val not in ('', 'none') and not os.path.isdir(os.path.join(cfg.FX_FOLDER, fx_val)):
                print(f"⚠️ 特效包不存在，已忽略: {fx_val}")
                sc['fx'] = 'none'
        user_id = generate_password()
        output_path = f'{cfg.OUTPUT_FOLDER}/{user_id}.mp4'
        print(f'AI导播脚本: {json.dumps(generated_data, ensure_ascii=False, indent=2)}')
        video_result = create_video(generated_data, output_path)
        if not video_result:
            return {'message': '视频生成失败，请检查素材(背景和情感)是否齐全'}, 500
        return {'message': f'生成成功，专属ID：{user_id}', 'file_path': output_path}, 200
    except Exception as e:
        return {'message': str(e)}, 500

@app.route('/')
def home():
    return jsonify({'message': 'I Love U'})

@app.route('/healthz')
def healthz():
    return jsonify({'status': 'ok'})

@app.route('/generate_video', methods=['POST'])
def generate_video_endpoint():
    result, status_code = process_request(request.json or {}, request.remote_addr)
    return jsonify(result), status_code

@app.route('/generate_video_debug', methods=['POST'])
def generate_video_debug():
    data = request.json
    scenes_data = data.get('scenes', data) if isinstance(data, dict) else data
    user_id = generate_password()
    output_path = f'{cfg.OUTPUT_FOLDER}/debug_{user_id}.mp4'
    try:
        video_result = create_video(scenes_data, output_path)
        if not video_result:
            return jsonify({'message': '视频生成失败，请检查素材是否齐全'}), 500
        return jsonify({'message': f'调试生成成功！ID：{user_id}', 'file_path': output_path}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    initialize_csv()
    print('猫Meme视频制作服务已启动 (Powered by DeepSeek)...')
    serve(app, host='127.0.0.1', port=5000)
