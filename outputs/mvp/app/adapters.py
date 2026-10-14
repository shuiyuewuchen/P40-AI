"""AI 适配层：统一接口 + 真实 API 调用（未配 Key 或调用失败时回退到 stub）。"""
import json
import time
import uuid

import httpx


def _stub_url(kind):
    ext = "png" if kind == "img" else "mp4"
    return f"https://cdn.example.com/{kind}/{uuid.uuid4().hex[:8]}.{ext}"


class Orchestrator:
    """AI1：DeepSeek 编排 / 分镜 / 拼接。"""

    def __init__(self, provider):
        self.provider = provider

    def plan(self, project):
        if not self.provider.api_key:
            return self._stub_plan(project)
        payload = {
            "model": self.provider.model,
            "messages": [
                {"role": "system",
                 "content": "你是视频分镜导演。根据主题、场景、色调生成每个镜头的提示词。"
                            "只输出 JSON 数组，每项格式 {\"scene\": \"场景名\", \"prompt\": \"提示词\"}。"},
                {"role": "user",
                 "content": json.dumps({
                     "theme": project.get("theme", ""),
                     "scene": project.get("scene", "风景"),
                     "tone": project.get("tone", "暖色调"),
                     "clips": project["clips"],
                     "segment_sec": project["segment_sec"],
                 }, ensure_ascii=False)},
            ],
            "temperature": 0.7,
        }
        try:
            r = httpx.post(f"{self.provider.base_url.rstrip('/')}/chat/completions",
                           headers={"Authorization": f"Bearer {self.provider.api_key}"},
                           json=payload, timeout=60)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            scenes = json.loads(content)
            return [{"index": i + 1,
                     "scene": s.get("scene", project.get("scene", "风景")),
                     "prompt": s.get("prompt", ""),
                     "duration_sec": project["segment_sec"]} for i, s in enumerate(scenes)]
        except Exception as exc:  # noqa: BLE001
            return [dict(s, note=f"真实调用失败，已用占位提示词（{exc}）")
                    for s in self._stub_plan(project)]

    def _stub_plan(self, project):
        scenes = []
        prev = "开篇镜头"
        for i in range(project["clips"]):
            continuity = (f"承接上一镜头（{prev}）自然过渡，镜头语言与色调统一，避免割裂"
                          if i > 0 else "作为开篇镜头，确立整体视觉基调")
            scenes.append({"index": i + 1, "scene": project.get("scene", "风景"),
                           "prompt": f"{project['tone']}色调的{project['scene']}，统一画质与运镜；{continuity}",
                           "duration_sec": project["segment_sec"]})
            prev = f"{project['scene']} · 镜头{i + 1}"
        return scenes

    def stitch(self, project):
        return {"url": f"file:///output/{project['id']}.mp4",
                "duration_sec": project["minutes"] * 60}


class ImageAdapter:
    """AI2：Seedream 文生图。"""

    def __init__(self, provider):
        self.provider = provider

    def generate(self, scene):
        if not self.provider.api_key:
            return self._stub(scene)
        payload = {
            "model": self.provider.model,
            "prompt": scene["prompt"],
            "size": "1920x1080",
            "response_format": "url",
        }
        try:
            r = httpx.post(f"{self.provider.base_url.rstrip('/')}/images/generations",
                           headers={"Authorization": f"Bearer {self.provider.api_key}"},
                           json=payload, timeout=180)
            r.raise_for_status()
            url = r.json()["data"][0].get("url")
            return {"index": scene["index"], "image_url": url or _stub_url("img")}
        except httpx.HTTPStatusError as exc:
            return {**self._stub(scene), "note": f"真实调用失败 HTTP {exc.response.status_code}：{exc.response.text[:300]}"}
        except Exception as exc:  # noqa: BLE001
            return {**self._stub(scene), "note": f"真实调用失败，已用占位图（{exc}）"}

    def _stub(self, scene):
        return {"index": scene["index"], "image_url": _stub_url("img")}


class VideoAdapter:
    """AI3：Seedance 图生视频（异步任务 + 轮询）。"""

    def __init__(self, provider):
        self.provider = provider

    def generate(self, scene):
        if not self.provider.api_key:
            return self._stub(scene)
        base = self.provider.base_url.rstrip("/")
        duration = max(4, min(15, int(scene["duration_sec"])))
        res = scene.get("resolution", "720p")
        if res not in ("480p", "720p"):
            res = "720p"
        payload = {
            "model": self.provider.model,
            "content": [
                {"type": "text", "text": scene["prompt"]},
                {"type": "image_url", "image_url": {"url": scene.get("image_url", "")},
                 "role": "first_frame"},
            ],
            "duration": duration,
            "resolution": res,
        }
        try:
            r = httpx.post(f"{base}/contents/generations/tasks",
                           headers={"Authorization": f"Bearer {self.provider.api_key}"},
                           json=payload, timeout=60)
            r.raise_for_status()
            task = r.json()
            task_id = task.get("id") or task.get("task_id")
            for _ in range(40):
                time.sleep(3)
                q = httpx.get(f"{base}/contents/generations/tasks/{task_id}",
                              headers={"Authorization": f"Bearer {self.provider.api_key}"},
                              timeout=30)
                q.raise_for_status()
                st = q.json()
                status = st.get("status")
                if status in ("succeeded", "success"):
                    url = (st.get("content") or {}).get("video_url") or st.get("video_url")
                    return {"index": scene["index"], "video_url": url or _stub_url("vid"),
                            "duration_sec": scene["duration_sec"]}
                if status in ("failed", "cancelled", "canceled"):
                    raise RuntimeError(f"seedance task {status}")
            raise RuntimeError("seedance timeout")
        except httpx.HTTPStatusError as exc:
            return {**self._stub(scene), "note": f"真实调用失败 HTTP {exc.response.status_code}：{exc.response.text[:300]}"}
        except Exception as exc:  # noqa: BLE001
            return {**self._stub(scene), "note": f"真实调用失败，已用占位视频（{exc}）"}

    def _stub(self, scene):
        return {"index": scene["index"], "video_url": _stub_url("vid"),
                "duration_sec": scene["duration_sec"]}


def build_adapters(providers):
    return {"ai1": Orchestrator(providers["ai1"]),
            "ai2": ImageAdapter(providers["ai2"]),
            "ai3": VideoAdapter(providers["ai3"])}
