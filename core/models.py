from pydantic import BaseModel, Field
from typing import List

EMOTIONS = "imploring, broken, surprised, laughing, blank, showoff, proud, irritable, shy, smirk, willful, cheering, hungry, anxious, scolding, astonished, pitiful, disdain, striving, others, giggle, painful, majestic, innocent, frustrated, helpless, excited, brave, happy, shocked, eating, awkward, despair"
PLACES = "beach, forest, highway, lab, Mountain, port, river, concert, fantacy, others, rooftop, stage, airport, amusementpark, bank, cinema, classroom, grassland, gym, home, hospital, kitchen, library, museum, park, playground, pool, restaurant, school, shop, station, theater, village"
FX_LIST = "none, beam_clash, fire_burst, freeze, thunder_strike, slash, shield, summon, screen_flash, teleport, heal, money_rain, hearts, anger_flame, dizzy, meteor, zoom_punch"
FX_GUIDE = "可选视觉特效(填特效名或none)：对波beam_clash、烈火fire_burst、冰封freeze、天雷thunder_strike、剑气slash、护盾shield、召唤summon、闪屏screen_flash、瞬移teleport、治疗heal、钞票雨money_rain、心动hearts、怒焰anger_flame、晕眩dizzy、陨石meteor、冲击zoom_punch"

class Character(BaseModel):
    name: str = Field(description="角色名，简短")
    emotion: str = Field(default="", description=f"表情。既可用项目内置情绪（严格从以下英文单词中选择：{EMOTIONS}），也可填 image_assets/ 下的自定义角色名（直接用图片素材）")
    text: str = Field(description="少于15字的对话文本")
    at: float = Field(default=0.0, description="第几秒开始说话（仅multi模式使用，单位秒）")
    entrance: str = Field(default="none", description="multi专用：入场方式 none/left/right/bottom/top")
    exit: str = Field(default="none", description="multi专用：退场方式 none/left/right/top")
    char: str = Field(default="", description="图片素材专用：指定 image_assets/<char>/ 下的角色素材。填了优先用 image_assets，emotion 则作为该角色下的表情文件名")

class Scene(BaseModel):
    title: str = Field(description="当前场景的全局标题")
    place: str = Field(description=f"场景地点，必须严格从以下选择：{PLACES}")
    layout: str = Field(default="flat", description="multi专用站位：flat=横向等分同层 / depth=前后排近大远小(偶数位后排缩小上移")
    scene_type: str = Field(description="镜头类型：single（1只独白）/ dialogue（2只对话）/ multi（3只及以上同屏，角色须填 at/entrance/exit）")
    fx: str = Field(default="none", description=f"特效开关。{FX_GUIDE}。可选值: {FX_LIST}")
    fx_at: float = Field(default=0.0, description="特效起始秒，0=自动(对齐场景收尾)")
    fx_boom: float = Field(default=0.0, description="beam_clash专用：第几秒爆炸(相对特效起点)，0=默认2.45")
    characters: List[Character] = Field(description="角色列表")

class StoryAnalysis(BaseModel):
    scenes: List[Scene] = Field(description="根据故事发展拆分出的连续镜头列表")
