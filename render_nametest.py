import sys, os
sys.path.insert(0, "/opt/AICatMeme")
os.chdir("/opt/AICatMeme")
from services.video_service import create_video

scenes = [
    {"title": "测试·双猫对话", "place": "home", "scene_type": "dialogue",
     "characters": [
        {"name": "前女友猫", "emotion": "disdain", "text": "十年之期已到，退婚！"},
        {"name": "废柴猫", "emotion": "pitiful", "text": "莫欺少年穷……"}]},
    {"title": "测试·单猫", "place": "forest", "scene_type": "single",
     "characters": [{"name": "废柴猫", "emotion": "astonished", "text": "石缝里竟有金光？！"}]},
    {"title": "测试·四猫前后排", "place": "stage", "scene_type": "multi", "layout": "depth",
     "characters": [
        {"name": "老大猫", "emotion": "proud", "text": "都安静，听我说。", "at": 0},
        {"name": "马仔猫", "emotion": "showoff", "text": "老大牛逼！", "at": 3},
        {"name": "跟班甲", "emotion": "laughing", "text": "哈哈哈哈哈", "at": 6},
        {"name": "跟班乙", "emotion": "smirk", "text": "憋不住了。", "at": 9}]},
]

ok = create_video(scenes, "/opt/AICatMeme/output/nametest.mp4")
print("RESULT:", ok)
