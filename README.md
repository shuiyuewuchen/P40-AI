# AI长视频自动生成流水线

从一句提示词，自动完成分镜、文生图、图生视频和拼接，生成 30 分钟以上、可以循环播放的长视频。面向电视屏保等循环播放场景，主题以自然风景、户外、宇宙、极光为主。

## 项目结构

- `outputs/多AI视频生成平台-UI原型.html`：可点击的界面原型，双击用浏览器打开即可，无需安装。
- `outputs/mvp/`：后端服务（Python + FastAPI）。
- `outputs/多AI融合视频生成平台-方案与架构文档.md`：方案与架构说明。
- `outputs/演讲稿-应用介绍.md`：录屏演示脚本。
- `outputs/AI长视频自动生成流水线-阶段成果报告.docx`：阶段成果报告。

## 环境要求

- 界面原型：任意现代浏览器，无需安装任何东西。
- 后端：Python 3.11 或更高版本（3.12、3.15 均可）。
- 拼接出片（可选）：ffmpeg。

## 快速开始

### 1. 打开界面原型

双击打开 `outputs/多AI视频生成平台-UI原型.html`，用测试账号登录：

- 管理员：test1 / 123456
- 普通成员：test2 / 123456

### 2. 运行后端

```bash
cd outputs/mvp
python3 -m venv .venv
source .venv/bin/activate          # Windows 用 .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # 然后按下一节填入你的 API Key
uvicorn app.main:app --reload --port 8000
```

启动后打开 http://127.0.0.1:8000/docs 可查看接口文档。

### 3. 配置 API Key

在 `outputs/mvp/.env` 里填写：

```
DEEPSEEK_API_KEY=你的DeepSeek密钥
ARK_API_KEY=你的火山方舟密钥
SEEDREAM_MODEL=doubao-seedream-5-0-flash-260915
SEEDANCE_MODEL=doubao-seedance-2-0-mini-260615
```

- DeepSeek：到 https://platform.deepseek.com 创建 API Key。
- 火山方舟：到 https://console.volcengine.com/ark 开通 Seedream（文生图）和 Seedance（图生视频）服务，创建 API Key，并在「开通管理」里核对实际的 Model ID。

注意：文生图和图生视频的模型服务需要在火山方舟开通后才会真实生成图片和视频；未开通时，后端会用占位结果把整条流程跑通，方便先联调。

## 常见问题

- 启动报 `unsupported operand type(s) for |`：说明 Python 版本低于 3.10，请用 3.11+ 重建虚拟环境。
- 端口被占用：执行 `lsof -ti :8000 | xargs kill -9` 后再启动。
- 文生图或图生视频返回 `note: 真实调用失败`：检查火山方舟模型是否开通、Model ID 是否与 `.env` 一致。

## 免责说明

本项目仅用于演示与学习。生成内容请遵守各模型服务条款，商用前确认素材与配乐的授权。
