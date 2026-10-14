"""FastAPI 入口：认证、项目状态机、AI 编排、用量记账。"""
import os
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import adapters, config, queue, stitch, store, workflow

app = FastAPI(title="智象鲸视 · 视频生成平台 MVP")
db = store.Store(os.getenv("DATA_PATH", "data.json"))
providers = config.providers()
ai = adapters.build_adapters(providers)


class LoginIn(BaseModel):
    account: str
    password: str


class RegisterIn(BaseModel):
    account: str
    name: str = ""


class AccountIn(BaseModel):
    account: str


class ProjectIn(BaseModel):
    minutes: int = 30
    segment_sec: int = 30
    resolution: str = "1080p"
    scene: str = "风景"
    tone: str = "暖色调"
    theme: str = "自然奇观之旅"
    audio: str = "网络免费音频"
    transition: str = "硬切"


# ---------- 认证 ----------
@app.post("/api/auth/login")
def login(body: LoginIn):
    u = db.get_user(body.account)
    if not u or u.get("password") != body.password or not u.get("active"):
        raise HTTPException(401, "请询问管理员获得账号密码")
    return {"account": body.account, "name": u["name"], "role": u["role"],
            "perms": u.get("perms", [])}


@app.post("/api/auth/register")
def register(body: RegisterIn):
    if db.get_user(body.account):
        raise HTTPException(409, "账号已存在")
    db.add_pending(body.account, body.name or body.account)
    return {"message": "已提交注册，等待管理员审批"}


@app.get("/api/auth/pending")
def pending():
    return db.data["pending"]


@app.post("/api/auth/approve")
def approve(body: AccountIn):
    db.approve(body.account)
    return {"message": "已通过并创建账号（默认密码 123456）"}


@app.post("/api/auth/reset-password")
def reset_password(body: AccountIn):
    db.reset_password(body.account)
    return {"message": "已重置为 123456"}


# ---------- 项目 ----------
@app.post("/api/projects")
def create_project(body: ProjectIn):
    est = workflow.estimate(body.minutes, body.segment_sec, body.resolution)
    pid = uuid.uuid4().hex[:12]
    project = {
        "id": pid,
        "status": "S0",
        "stage": "S1",
        "stage_status": "idle",
        "minutes": body.minutes,
        "segment_sec": body.segment_sec,
        "resolution": body.resolution,
        "scene": body.scene,
        "tone": body.tone,
        "theme": body.theme,
        "audio": body.audio,
        "transition": body.transition,
        "clips": est["clips"],
        "estimate": est,
        "scenes": [],
        "images": [],
        "videos": [],
        "created_by": "test1",
    }
    db.create_project(project)
    return project


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    return p


@app.post("/api/projects/{pid}/stages/{stage}/run")
def run_stage(pid: str, stage: str):
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    if stage == "S1":
        p["scenes"] = ai["ai1"].plan(p)
        db.add_usage(s1_tokens=12000)
    elif stage == "S2":
        results, failures = queue.run_batch(p["scenes"], ai["ai2"].generate,
                                            concurrency=10, retries=2)
        p["images"] = sorted(results, key=lambda x: x["index"])
        p["failed_images"] = [it for it, _e in failures]
        db.add_usage(s2_images=len(results), s2_tokens=len(results) * 300)
    elif stage == "S3":
        conc = 1 if p["resolution"] == "4K" else 10
        rpm = 15 if p["resolution"] == "4K" else 600
        img_map = {im["index"]: im["image_url"] for im in p.get("images", [])}
        for s in p["scenes"]:
            s["image_url"] = img_map.get(s["index"], "")
            s["resolution"] = p["resolution"]
        results, failures = queue.run_batch(p["scenes"], ai["ai3"].generate,
                                            concurrency=conc, rpm=rpm, retries=2)
        p["videos"] = sorted(results, key=lambda x: x["index"])
        p["failed_videos"] = [it for it, _e in failures]
        db.add_usage(s3_seconds=len(results) * p["segment_sec"], s3_clips=len(results))
    elif stage == "S4":
        video_urls = [v["video_url"] for v in p.get("videos", [])]
        output = f"output/{pid}.mp4"
        p["stitch_steps"] = stitch.stitch(video_urls, output,
                                          resolution=p["resolution"],
                                          transition=p.get("transition", "硬切"),
                                          clip_duration=p["segment_sec"],
                                          bgm=p.get("bgm"), bgm_volume=0.7)
        p["final"] = {"url": f"file:///{output}", "duration_sec": p["minutes"] * 60}
        db.add_usage(s4_minutes=p["minutes"])
    else:
        raise HTTPException(400, "未知阶段")
    p["stage_status"] = "pending_confirm"
    db.update_project(pid, p)
    db.log(p.get("created_by", "worker"), f"运行 {stage}")
    return p


@app.post("/api/projects/{pid}/stages/{stage}/retry")
def retry_stage(pid: str, stage: str):
    """批量重试该阶段失败的任务。"""
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    retried = 0
    if stage == "S2":
        failed = p.get("failed_images", [])
        if failed:
            results, failures = queue.run_batch(failed, ai["ai2"].generate,
                                                concurrency=10, retries=2)
            existing = {img["index"] for img in p["images"]}
            for r in results:
                if r["index"] not in existing:
                    p["images"].append(r)
            p["failed_images"] = [it for it, _e in failures]
            p["images"] = sorted(p["images"], key=lambda x: x["index"])
            retried = len(results)
            db.add_usage(s2_images=len(results), s2_tokens=len(results) * 300)
    elif stage == "S3":
        failed = p.get("failed_videos", [])
        if failed:
            conc = 1 if p["resolution"] == "4K" else 10
            rpm = 15 if p["resolution"] == "4K" else 600
            results, failures = queue.run_batch(failed, ai["ai3"].generate,
                                                concurrency=conc, rpm=rpm, retries=2)
            existing = {v["index"] for v in p["videos"]}
            for r in results:
                if r["index"] not in existing:
                    p["videos"].append(r)
            p["failed_videos"] = [it for it, _e in failures]
            p["videos"] = sorted(p["videos"], key=lambda x: x["index"])
            retried = len(results)
            db.add_usage(s3_seconds=len(results) * p["segment_sec"], s3_clips=len(results))
    else:
        raise HTTPException(400, "仅支持 S2/S3 重试")
    db.update_project(pid, p)
    db.log(p.get("created_by", "worker"), f"重试 {stage} 失败任务")
    return {"retried": retried, "project": p}


@app.post("/api/projects/{pid}/stages/{stage}/confirm")
def confirm_stage(pid: str, stage: str):
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    nxt = workflow.next_stage(stage)
    p["stage"] = nxt or "DONE"
    p["stage_status"] = "confirmed"
    p["status"] = "DONE" if nxt is None else nxt
    db.update_project(pid, p)
    return p


# ---------- 用量 ----------
@app.get("/api/usage/summary")
def usage_summary():
    return {
        "usage": db.usage_summary(),
        "quota_total": 100000,
        "quota_video": 36000,
        "quota_image": 50000,
    }


@app.get("/api/health")
def health():
    return {"ok": True, "providers": {k: v.name for k, v in providers.items()}}
