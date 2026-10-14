"""配置与供应商预设。"""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Provider:
    name: str
    base_url: str
    api_key: str = ""
    model: str = ""
    models: list = field(default_factory=list)


# 各视频模型支持的单段时长与清晰度（与前端原型保持一致）
MODEL_SPEC = {
    "Seedance 2.0 mini": {"dur": [4, 8, 12, 15], "res": ["480p", "720p"]},
    "Seedance 2.5": {"dur": [5, 10, 15, 30], "res": ["480p", "720p", "1080p", "4K"]},
    "可灵 3.0": {"dur": [5, 10, 15], "res": ["720p", "1080p", "4K"]},
    "Vidu Q4": {"dur": [4, 8, 16], "res": ["540p", "720p", "1080p", "2K", "4K"]},
}


def providers() -> dict:
    """从环境变量读取供应商配置；未配 Key 时后端回退到 stub。"""
    return {
        "ai1": Provider(
            "DeepSeek",
            os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            os.getenv("DEEPSEEK_API_KEY", ""),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            models=["DeepSeek V4", "DeepSeek V4 Flash"],
        ),
        "ai2": Provider(
            "Seedream",
            os.getenv("SEEDREAM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
            os.getenv("ARK_API_KEY", ""),
            model=os.getenv("SEEDREAM_MODEL", "doubao-seedream-5-0-flash-260915"),
            models=["Seedream 4.0", "Seedream 5.0"],
        ),
        "ai3": Provider(
            "Seedance",
            os.getenv("SEEDANCE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
            os.getenv("ARK_API_KEY", ""),
            model=os.getenv("SEEDANCE_MODEL", "doubao-seedance-2-0-mini-260615"),
            models=["Seedance 2.5"],
        ),
    }
