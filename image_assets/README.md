# image_assets — 用你自己的图片做猫meme

把任意图片（PNG/JPG/WebP）丢进这个目录，项目会自动把它变成**会呼吸浮动**的序列帧，
直接参与视频渲染 —— 不用自己切帧、不用绿幕、不用预处理。

## 三种放法

### 1. 单图 = 一个表情（最常用，推荐）
```
image_assets/<角色名>/<表情名>.png
```
例：
```
image_assets/阿尘/blank.png
image_assets/阿尘/anxious.png
image_assets/阿尘/majestic.png
```
渲染时这样引用：
```python
{"name": "阿尘", "char": "阿尘", "emotion": "anxious", "text": "别过来！", "at": 0}
```

### 2. 一个角色只放一张图（不区分表情）
```
image_assets/老猫.png
# 或者
image_assets/老猫/only.png
```
之后 `emotion` 随便填，都会用这张图：
```python
{"name": "老猫", "char": "老猫", "emotion": "whatever", "text": "神格会转移。", "at": 0}
```

### 3. 已切好的序列帧（你自己做的动画）
```
image_assets/阿尘/run/0001.png
image_assets/阿尘/run/0002.png
...
```
序列帧会被**原样使用**，不做任何处理。

## 用辅助脚本添加（推荐）

```bash
# 单图
python3 add_image_asset.py --role 阿尘 --emotion blank --image /path/head.png

# 一个角色只放一张图
python3 add_image_asset.py --role 老猫 --image /path/old.png

# 序列帧目录
python3 add_image_asset.py --role 阿尘 --emotion run --frames /path/seq_dir/

# 查看素材库现状
python3 add_image_asset.py --list
```

## 自动动画说明

单张静态图会被程序加上"呼吸感"：
- **上下浮动** ±16px（主呼吸节奏）
- **左右摇摆** ±8px（2 倍频，避免机械直线运动）
- **缩放呼吸** ±1.4%（像轻轻吸气鼓起）

一个循环 150 帧 = 5 秒 @30fps，首尾帧数值一致，循环播放**无缝衔接**。

参数在 `core/image_assets.py` 顶部的 `BOB_AMPLITUDE` / `SWAY_AMPLITUDE` /
`SCALE_AMPLITUDE` / `DEFAULT_FRAMES` 可调。

## 检查清单

- [ ] 图片有透明背景更佳（PNG RGBA）；不透明也能用，只是会带方块底
- [ ] 图片不用预先缩放，程序会自动等比缩放到 540×540 画布（不变形）
- [ ] 生成的动画序列缓存在 `.cache/`，改图后自动重新生成
- [ ] 素材库不进 git（体积大且属个人内容），换机器用 `add_image_asset.py` 重新添加
