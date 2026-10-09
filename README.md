# 🐈 AICatMeme: AI 驱动的猫 Meme 视频自动生成工具 (支持对话版)

欢迎来到 **AICatMeme**！这是一个利用大模型（Gemini/OpenAI/DeepSeek 等）自动拆分剧本，并结合猫片素材库自动合成“猫片”视频的开源项目。

## **体验网址：`ai.stickic.asia`**

---

### 🎥 效果示例 / Example Preview

**Fan-submitted video 来自粉丝的投稿视频：**

[https://github.com/user-attachments/assets/69a448a4-8dea-4ee9-b8b9-a2b8b231f84b](https://github.com/user-attachments/assets/69a448a4-8dea-4ee9-b8b9-a2b8b231f84b)

🖼️ *The background image will also change according to the prompt.*
📌 *背景图也会根据 prompt 自动更换！*

---

### 🖼️ 用自己的图片做角色 / Custom Image Characters

不想用内置猫片素材？把任意图片丢进 `image_assets/`，项目会自动把它变成
**会呼吸浮动**的序列帧参与渲染 —— 不用切帧、不用绿幕、不用预处理。

```bash
# 添加一张图作为一个表情
python3 add_image_asset.py --role 阿尘 --emotion blank --image /path/head.png
# 一个角色只放一张图（emotion 随便填都用它）
python3 add_image_asset.py --role 老猫 --image /path/old.png
# 已切好的序列帧目录
python3 add_image_asset.py --role 阿尘 --emotion run --frames /path/seq_dir/
# 查看素材库
python3 add_image_asset.py --list
```

剧本里这样引用（新增 `char` 字段指定素材角色）：
```python
{"name": "阿尘", "char": "阿尘", "emotion": "blank", "text": "十天后我会成神。", "at": 0}
```

- 单图会自动加"呼吸感"微动（上下 ±16px / 摇摆 ±8px / 缩放 ±1.4%），循环无缝
- 图片自动等比缩放到 540×540，不变形；透明 PNG 效果最佳
- 生成的动画缓存于 `image_assets/.cache/`，改图自动重建
- 也支持你直接放 `emotion` 用自定义名（不加 `char`），命中素材库即自动启用

详细说明见 [`image_assets/README.md`](image_assets/README.md)。

---

### 🚀 重磅更新 / Big Update!

微信小程序已正式上线！📱 打开微信，搜索：**AI视频生成猫meme** 即可体验！或直接扫描二维码进入👇

![gh\_d8d6e3fde1de\_430](https://github.com/user-attachments/assets/4d2ec73b-c029-4d11-beb4-95c45fd2d9fc)
---

### 🛠️ 环境准备与安装 / Installation

#### 1. 克隆仓库到本地

打开终端，执行以下命令：

```bash
git clone https://github.com/Stickic-cyber/AICatMeme.git
cd AICatMeme

```

#### 2. 安装 Python 依赖

建议使用虚拟环境（如 Conda 或 venv）：

```bash
pip install -r requirements.txt

```

---

### 📖 快速运行指南 (V2.0 架构)

项目采用了**预处理 + 后端 + 前端**的分离架构，请按顺序执行：

#### 第一步：素材库预处理 (Pre-Process)

在正式生成前，你需要将原始绿幕素材转化为干净的透明 PNG 序列。

1. 将你的 `.mp4` 绿幕素材放入 `meme_org` 文件夹。
2. 运行预处理脚本：
```bash
python PreProcessVideo.py

```


*该脚本会执行强力去绿光算法，并将素材拆解为带透明通道的 PNG 序列和音频。*

#### 第二步：启动后端服务 (Backend)

后端负责接收任务、调用 AI API 以及执行视频渲染逻辑。

1. 确保 Redis 运行中（可选，用于请求限流）。
2. 运行 Flask 后端：
```bash
python app.py

```


*服务默认运行在 `5000` 端口。*

#### 第三步：启动交互面板 (Dashboard)

1. 启动前端 Web 界面：
```bash
streamlit run dashboard.py

```


2. 浏览器访问 `http://localhost:8501`。
3. **配置：** 在侧边栏配置 AI 厂商（Gemini/OpenAI/DeepSeek 等）及 API Key，即可开始生成！

---

### 📂 核心文件职能说明

| 文件名 | 职能 | 说明 |
| --- | --- | --- |
| **`PreProcessVideo.py`** | **素材加工** | 绿幕抠图核心。采用 `colorkey` + `despill` 滤镜，保证素材边缘丝滑。 |
| **`app.py`** | **后端核心** | 生产级 Flask 服务，支持 AI 脚本分析与视频合成调度。 |
| **`dashboard.py`** | **前端 UI** | 基于 Streamlit。支持多语言切换、多模型配置及左右分栏视频预览。 |
| **`services/video_service.py`** | **渲染引擎** | 纯 FFmpeg 渲染：single/dialogue/multi 三模式、flat/depth 站位、字幕底条、特效叠加与震屏。 |
| **`gen_fx_*.py`** | **特效生成** | 用 PIL 程序化生成特效帧序列，产物落在 `fx/<特效名>/frames/` + `audio.wav`。 |

---

### 🎆 特效系统 (FX)

镜头剧本里每个 scene 可选挂一个特效包：

```json
{
  "title": "终局对决·仙法对波", "place": "stage", "scene_type": "dialogue",
  "fx": "beam_clash", "fx_at": 4.0, "fx_boom": 2.45,
  "characters": [...]
}
```

- `fx`：特效包名，对应 `fx/<名字>/` 目录（内含 `frames/*.png` 与可选 `audio.wav/mp3`）；填 `none` 或不填则无特效
- `fx_at`：特效起始秒，`0` = 自动对齐场景收尾
- `fx_boom`：该特效的爆炸点偏移秒（beam_clash 专用，震屏以它对齐）

**已上线特效：**

| 特效名 | 效果 | 适用镜头 | 状态 |
| --- | --- | --- | --- |
| `beam_clash` | 双猫对波：蓄力球→锥形光束→撞点拉锯僵持（双向火花/气浪环/电弧）→白闪爆炸 | dialogue/multi | ✅ |
| `fire_burst` | 烈火诀：火球凝聚→火焰喷发→命中爆炸 | single/dialogue | ✅ |
| `freeze` | 寒冰狱：冰棱蔓延→冰塑封裹→碎冰飘落 | single | ✅ |
| `thunder_strike` | 天雷诛邪：聚云→分形闪电→落点冲击环→电蛇残留 | single | ✅ |
| `slash` | 剑气纵横：月牙形剑气横扫→切割线→火花 | dialogue/single | ✅ |
| `shield` | 金刚护体：网格能量罩→受击波纹→罩碎飞散 | single | ✅ |
| `summon` | 召唤阵：地面阵图旋转→紫光柱冲天→顶端炸开 | single | ✅ |
| `screen_flash` | 终局：黑白频闪→血红→暗角收拢 | single | ✅ |
| `teleport` | 瞬移：残影消散→空间波纹→碎片汇聚重组 | single | ✅ |
| `heal` | 治疗雨：绿雨下降→环绕绿环→上升粒子→脉冲 | single | ✅ |
| `money_rain` | 钞票雨：旋转钞票+金币弹跳+¥金闪 | single | ✅ |
| `hearts` | 心动攻击：粉雾+飘升爱心+心跳大爱心 | single | ✅ |
| `anger_flame` | 怒焰：黑红火焰+头顶青筋+地面龟裂+红暗角 | single | ✅ |
| `dizzy` | 晕眩：头顶转星星+螺旋线+眩晕波纹 | single | ✅ |
| `meteor` | 天降陨石：火球拖尾下落→落地白闪→地面冲击环+烟柱 | single | ✅ |
| `zoom_punch` | 冲击推进：放射速度线→白闪冲击环→多重震波+碎片 | single | ✅ |

**特效池规划**（后续候选）：`charging_pillar` 升级光柱、`fire_tornado` 火焰旋风、`poison_cloud` 毒瘴、`summon_dragon` 神龙降临、`time_slow` 子弹时间、`afterimage` 残影连击。

**新增一个特效的步骤**（渲染管线已全面通用化，不用动 video_service）：

1. 复制 `gen_fx_beam_clash.py` 改名为 `gen_fx_<新特效>.py`，按需设计时间轴（PIL 画帧 + `wave` 合成音）
2. 产物路径固定：`fx/<新特效名>/frames/%04d.png` + `fx/<新特效名>/audio.wav`
3. scene 里 `"fx": "<新特效名>"` 即用；`app.py` 的导播 prompt 里补一句使用规则，AI 就会在合适桥段自动挂特效
4. 注意事项：光束/线条画粗（>28px，防 scale 震屏链+压缩吃对比度）；爆炸帧数≥3帧白闪；音频用 `adelay` 思路对齐 `fx_at`

---

### 📜 路径配置提醒 (Path Configuration)

为了保证程序运行，请确保：

* ✅ **ImageMagick 路径** 已在 `core/config.py` 中正确指向其 `magick.exe` 位置。
* ✅ **素材路径** 建议使用相对路径，以便项目在不同环境下都能直接跑通。

