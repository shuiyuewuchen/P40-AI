"""JSON 文件持久化的轻量存储（MVP 用，后续替换为数据库）。"""
import json
import os
import threading
from datetime import datetime


_lock = threading.RLock()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str = "data.json"):
        self.path = path
        with _lock:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    self.data = json.load(f)
            else:
                self.data = {
                    "users": {
                        "test1": {"name": "陈晓", "role": "admin", "password": "123456",
                                  "active": True,
                                  "perms": ["创建项目", "切换模型", "使用模板库", "团队管理"]},
                        "test2": {"name": "李娜", "role": "worker", "password": "123456",
                                  "active": True,
                                  "perms": ["创建项目", "切换模型", "使用模板库"]},
                    },
                    "pending": [],
                    "projects": {},
                    "usage": {"s1_tokens": 12480, "s2_images": 188, "s2_tokens": 56400,
                              "s3_seconds": 1080, "s3_clips": 60, "s4_minutes": 30,
                              "credit": 17600},
                    "templates": [],
                    "prompts": [],
                    "logs": [],
                }
                self._save()

    def _save(self):
        with _lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)

    # ---- 用户 ----
    def get_user(self, account):
        return self.data["users"].get(account)

    def add_user(self, account, name, role="worker"):
        self.data["users"][account] = {
            "name": name, "role": role, "password": "123456", "active": True,
            "perms": ["创建项目", "切换模型", "使用模板库"],
        }
        self.log("admin", f"创建账号 {account}")
        self._save()

    def reset_password(self, account):
        u = self.data["users"].get(account)
        if u:
            u["password"] = "123456"
            self.log("admin", f"重置 {account} 密码")
            self._save()

    def add_pending(self, account, name):
        self.data["pending"].append({"account": account, "name": name, "time": _now()})
        self._save()

    def approve(self, account):
        self.data["pending"] = [p for p in self.data["pending"] if p["account"] != account]
        self.add_user(account, account)

    # ---- 项目 ----
    def create_project(self, project):
        self.data["projects"][project["id"]] = project
        self._save()

    def get_project(self, pid):
        return self.data["projects"].get(pid)

    def update_project(self, pid, patch):
        self.data["projects"][pid].update(patch)
        self._save()

    # ---- 用量 ----
    def add_usage(self, **delta):
        u = self.data["usage"]
        for k, v in delta.items():
            u[k] = u.get(k, 0) + v
        self._save()

    def usage_summary(self):
        return self.data["usage"]

    # ---- 日志 ----
    def log(self, account, action):
        self.data["logs"].insert(0, {"time": _now(), "account": account, "action": action})
        self.data["logs"] = self.data["logs"][:200]
        self._save()

    def logs(self):
        return self.data["logs"]
