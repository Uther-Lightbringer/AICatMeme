import sys, os
sys.path.insert(0, "/opt/AICatMeme")
os.chdir("/opt/AICatMeme")
from services.video_service import create_video

scenes = [
    # 1. 集结: 五猫前后排
    {"title": "第一幕·五猫集结", "place": "fantacy", "scene_type": "multi", "layout": "depth",
     "characters": [
        {"name": "掌门猫", "emotion": "majestic", "text": "魔尊出世，诸位随我出征。", "at": 0},
        {"name": "火猫", "emotion": "proud", "text": "烈焰诀早已饥渴难耐！", "at": 2.4},
        {"name": "冰猫", "emotion": "disdain", "text": "聒噪。", "at": 4.8},
        {"name": "雷修猫", "emotion": "brave", "text": "天雷已蓄势待发。", "at": 7.0},
        {"name": "剑修猫", "emotion": "smirk", "text": "我的剑，也渴了。", "at": 9.2}]},
    # 2. 烈火诀: 对话镜头, 火猫轰杂兵
    {"title": "第二幕·烈火诀", "place": "forest", "scene_type": "dialogue", "fx": "fire_burst",
     "characters": [
        {"name": "火猫", "emotion": "proud", "text": "吃我一记烈火诀！"},
        {"name": "杂兵猫", "emotion": "pitiful", "text": "啊——我的毛！"}]},
    # 3. 冰封
    {"title": "第三幕·寒冰狱", "place": "river", "scene_type": "single", "fx": "freeze",
     "characters": [{"name": "冰猫", "emotion": "blank", "text": "寒冰狱，封。"}]},
    # 4. 天雷诛邪
    {"title": "第四幕·天雷诛邪", "place": "Mountain", "scene_type": "single", "fx": "thunder_strike",
     "characters": [{"name": "雷修猫", "emotion": "shocked", "text": "九霄神雷，听我号令！"}]},
    # 5. 剑气对斩
    {"title": "第五幕·剑气纵横", "place": "stage", "scene_type": "dialogue", "fx": "slash",
     "characters": [
        {"name": "剑修猫", "emotion": "smirk", "text": "接我一剑，算你赢。"},
        {"name": "魔将猫", "emotion": "disdain", "text": "剑气？哈！"}]},
    # 6. 护盾
    {"title": "第六幕·金刚护体", "place": "museum", "scene_type": "single", "fx": "shield",
     "characters": [{"name": "盾修猫", "emotion": "brave", "text": "罡气护体，不动如山！"}]},
    # 7. 召唤阵
    {"title": "第七幕·魔尊亲临", "place": "fantacy", "scene_type": "single", "fx": "summon",
     "characters": [{"name": "魔尊猫", "emotion": "disdain", "text": "区区五猫，也敢造次？"}]},
    # 8. 正邪对波
    {"title": "第八幕·正邪对波", "place": "stage", "scene_type": "dialogue", "fx": "beam_clash",
     "characters": [
        {"name": "掌门猫", "emotion": "majestic", "text": "五灵合一，诛邪！"},
        {"name": "魔尊猫", "emotion": "disdain", "text": "那就看看谁先倒下！"}]},
    # 9. 终局闪屏
    {"title": "第九幕·尘埃落定", "place": "fantacy", "scene_type": "single", "fx": "screen_flash",
     "characters": [{"name": "掌门猫", "emotion": "majestic", "text": "此战，我们赢了。"}]},
]

ok = create_video(scenes, "/opt/AICatMeme/output/五猫斗法_特效全开.mp4")
print("RESULT:", ok)
