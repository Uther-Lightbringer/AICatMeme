import sys, os
sys.path.insert(0, "/opt/AICatMeme")
os.chdir("/opt/AICatMeme")
from services.video_service import create_video

scenes = [
    {"title": "终局对决·仙法对波", "place": "fantacy", "scene_type": "dialogue",
     "fx": "beam_clash", "fx_at": 4.0,
     "characters": [
        {"name": "云清猫", "emotion": "majestic", "text": "接我这招，九天雷诀！"},
        {"name": "魔尊猫", "emotion": "disdain", "text": "雕虫小技，也敢献丑？"}]},
]

ok = create_video(scenes, "/opt/AICatMeme/output/beam_clash_test.mp4")
print("RESULT:", ok)
