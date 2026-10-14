"""启动自检脚本：一步步打印，定位卡住/报错的位置。"""


def step(n, text):
    print(f"{n}. {text} ...", flush=True)


step(1, "导入 fastapi")
import fastapi
print("   ok", fastapi.__version__, flush=True)

step(2, "导入 httpx")
import httpx
print("   ok", httpx.__version__, flush=True)

step(3, "导入 dotenv")
import dotenv
print("   ok", flush=True)

step(4, "导入 app.config")
from app import config
print("   ok", flush=True)

step(5, "导入 app.store")
from app import store
print("   ok", flush=True)

step(6, "导入 app.workflow")
from app import workflow
print("   ok", flush=True)

step(7, "导入 app.adapters")
from app import adapters
print("   ok", flush=True)

step(8, "初始化 Store（读写 data.json）")
s = store.Store()
print("   ok", flush=True)

step(9, "读取供应商配置")
p = config.providers()
print("   ok", {k: (v.name, bool(v.api_key)) for k, v in p.items()}, flush=True)

step(10, "构建 AI 适配器")
a = adapters.build_adapters(p)
print("   ok", flush=True)

print("ALL_OK", flush=True)
