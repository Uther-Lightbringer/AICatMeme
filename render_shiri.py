import sys, os
sys.path.insert(0, "/opt/AICatMeme")
os.chdir("/opt/AICatMeme")
from services.video_service import create_video

scenes = [
    {"title": "第一日·炼气：上门退婚", "place": "home", "scene_type": "dialogue",
     "characters": [
        {"name": "前女友猫", "emotion": "disdain", "text": "十年之期已到，退婚！"},
        {"name": "废柴猫", "emotion": "pitiful", "text": "莫欺少年穷……"}]},
    {"title": "第二日·炼气：后山捡秘籍", "place": "forest", "scene_type": "single",
     "characters": [{"name": "废柴猫", "emotion": "astonished", "text": "石缝里竟有金光？！"}]},
    {"title": "第三日·筑基：通宵一夜", "place": "rooftop", "scene_type": "single",
     "characters": [{"name": "废柴猫", "emotion": "striving", "text": "熬个通宵，居然筑基了？"}]},
    {"title": "第四日·金丹：宗门大比", "place": "stage", "scene_type": "dialogue",
     "characters": [
        {"name": "对手猫", "emotion": "showoff", "text": "筑基也配上台？"},
        {"name": "废柴猫", "emotion": "smirk", "text": "一招，够了。"}]},
    {"title": "第五日·元婴：长老震怒", "place": "theater", "scene_type": "dialogue",
     "characters": [
        {"name": "长老猫", "emotion": "shocked", "text": "此子竟已结丹？！"},
        {"name": "废柴猫", "emotion": "majestic", "text": "晚辈侥幸而已。"}]},
    {"title": "第六日·化神：拍卖会", "place": "shop", "scene_type": "dialogue",
     "characters": [
        {"name": "富豪猫", "emotion": "disdain", "text": "穷猫也敢竞宝？"},
        {"name": "废柴猫", "emotion": "laughing", "text": "这摊，我全包了。"}]},
    {"title": "第七日·炼虚：九天雷劫", "place": "Mountain", "scene_type": "single",
     "characters": [{"name": "废柴猫", "emotion": "painful", "text": "天劫？正好给我淬体！"}]},
    {"title": "第八日·合道：魔族夜袭", "place": "village", "scene_type": "single",
     "characters": [{"name": "废柴猫", "emotion": "brave", "text": "一猫，当关。"}]},
    {"title": "第九日·渡劫：霞光万丈", "place": "fantacy", "scene_type": "single",
     "characters": [{"name": "废柴猫", "emotion": "cheering", "text": "十日，我成神了！"}]},
    {"title": "第十日·成神：传说序章", "place": "stage", "scene_type": "single",
     "characters": [{"name": "废柴猫", "emotion": "showoff", "text": "十日成神，下一部演赘婿"}]},
]
ok = create_video(scenes, "/opt/AICatMeme/output/shirichenshen_v2.mp4")
print("RESULT:", ok)
