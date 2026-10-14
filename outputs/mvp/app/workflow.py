"""项目状态机与估算逻辑。"""
from typing import Optional

STAGES = ["S1", "S2", "S3", "S4"]
RES_FACTOR = {"480p": 0.7, "540p": 0.8, "720p": 1, "1080p": 1.5, "2K": 2.2, "4K": 4}


def clips_for(minutes: int, segment_sec: int) -> int:
    """片段数：整分钟 + 5/10/15/30 秒整除；8/16 秒向上取整，末段缩短。"""
    return max(1, -(-(minutes * 60) // segment_sec))


def estimate(minutes: int, segment_sec: int, resolution: str) -> dict:
    """按真实参考单价估算成本与耗时。"""
    clips = clips_for(minutes, segment_sec)
    factor = RES_FACTOR.get(resolution, 1)
    cost = clips * 0.3 + clips * segment_sec * 1.4 * factor + 0.5
    img_min = -(-clips // 10) * 0.5
    vid_conc = 1 if resolution == "4K" else 10
    vid_min = -(-clips // vid_conc) * (segment_sec / 20)
    machine_min = img_min + vid_min + 4.5
    total_min = machine_min + 32
    return {
        "clips": clips,
        "cost": round(cost),
        "machine_min": round(machine_min),
        "total_min": round(total_min),
    }


def next_stage(stage: str) -> Optional[str]:
    i = STAGES.index(stage)
    return STAGES[i + 1] if i + 1 < len(STAGES) else None
