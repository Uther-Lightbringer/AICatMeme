import sys, os
sys.path.insert(0, "/opt/AICatMeme")
os.chdir("/opt/AICatMeme")
from services.video_service import create_video

scenes = [
    {"title": "第一幕·瞬移上班", "place": "bank", "scene_type": "single", "fx": "teleport",
     "characters": [{"name": "社畜猫", "emotion": "excited", "text": "要迟到了……到了！"}]},
    {"title": "第二幕·妙手回春", "place": "hospital", "scene_type": "single", "fx": "heal",
     "characters": [{"name": "医猫", "emotion": "smirk", "text": "这一针下去，包好。"}]},
    {"title": "第三幕·天降横财", "place": "station", "scene_type": "single", "fx": "money_rain",
     "characters": [{"name": "锦鲤猫", "emotion": "laughing", "text": "钱多的花不完，烦！"}]},
    {"title": "第四幕·恋爱脑发作", "place": "home", "scene_type": "single", "fx": "hearts",
     "characters": [{"name": "恋爱猫", "emotion": "shy", "text": "看到他，心跳好快……"}]},
    {"title": "第五幕·气到冒烟", "place": "school", "scene_type": "single", "fx": "anger_flame",
     "characters": [{"name": "怒猫", "emotion": "frustrated", "text": "再催稿我就炸了！"}]},
    {"title": "第六幕·CPU烧了", "place": "classroom", "scene_type": "single", "fx": "dizzy",
     "characters": [{"name": "学渣猫", "emotion": "helpless", "text": "这道题…好晕…"}]},
    {"title": "第七幕·天降陨石", "place": "village", "scene_type": "single", "fx": "meteor",
     "characters": [{"name": "村长猫", "emotion": "shocked", "text": "快看天上！那是什么！"}]},
    {"title": "第八幕·一拳超人", "place": "gym", "scene_type": "single", "fx": "zoom_punch",
     "characters": [{"name": "拳王猫", "emotion": "proud", "text": "接这一拳，算我输！"}]},
]

ok = create_video(scenes, "/opt/AICatMeme/output/特效嘉年华.mp4")
print("RESULT:", ok)
