# 智象鲸视 · 视频生成平台（MVP 后端骨架）

这是与 UI 原型配套的最小可运行后端骨架，打通「登录/审批 → 项目创建 → 四阶段状态机 → AI 适配 → 用量记账 → 实时保存」的闭环。

## 运行

```bash
cd outputs/mvp
python3 -m venv .venv && source .venv/bin/activate   # Mac 推荐
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

打开 http://127.0.0.1:8000/docs 可查看自动生成的接口文档。

依赖 `ffmpeg`（S4 真正执行拼接时需要）：

```bash
brew install ffmpeg
```

## API Key

密钥放在 `.env` 文件（已加入 `.gitignore`，请勿提交到版本库）。两个 Key：

- `DEEPSEEK_API_KEY`：DeepSeek（AI1）
- `ARK_API_KEY`：火山方舟（AI2 Seedream + AI3 Seedance）

`config.py` 会通过 `python-dotenv` 自动读取 `.env`。

> 注意：`.env` 里没有写模型 ID。默认使用 `deepseek-chat`、`doubao-seedream-4-0-250828`、`doubao-seedance-2-5-260628`。请到火山方舟控制台「开通管理/模型推理」核对 Seedream、Seedance 的实际 Model ID，不一致时在 `.env` 里补 `SEEDREAM_MODEL`、`SEEDANCE_MODEL`。

## 测试账号

- 管理员：test1 / 123456
- 普通成员：test2 / 123456

## 目录结构

```
app/
  main.py       # FastAPI 路由
  config.py     # 供应商预设与环境变量
  store.py      # JSON 文件持久化（MVP 用，后续换数据库）
  workflow.py   # 状态机、片段数/成本估算
  adapters.py   # AI 适配层：AI1 编排 / AI2 文生图 / AI3 图生视频
  queue.py      # 任务队列：并发执行 + RPM 限流 + 重试
  stitch.py     # ffmpeg 拼接：参数归一化 + 转场 + 音频混音
data.json       # 运行时自动生成的状态文件
```

## 接入真实供应商

当前 `adapters.py` 里的三个适配器是 stub（返回占位 URL），先把流程跑通。接入真实 API 时：

1. 在环境变量里配置密钥（见 `config.py`）：
   - AI1：`DEEPSEEK_API_KEY`（DeepSeek V4）
   - AI2：`ARK_API_KEY`（火山方舟 Seedream）
   - AI3：`ARK_API_KEY`（火山方舟 Seedance）
2. 在 `adapters.py` 的对应 `generate()` 里把 stub 换成真实 HTTP 调用（用 `httpx`）。

## 下一步（建议顺序）

1. AI 适配器接真实 API（异步提交 + 轮询/回调）。
2. 任务队列：已提供 queue.py（并发 + RPM 限流 + 重试），已接入 S2/S3。
3. ffmpeg 拼接：已提供 stitch.py（参数归一化 + 转场 + 音频混音），已接入 S4；下一步在部署机上实际执行这些命令。
4. 把前端 HTML 原型接入这些接口。
