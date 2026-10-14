"""轻量任务队列：并发执行 + RPM 限流 + 重试（MVP 用，后续可换 Celery/BullMQ）。"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class RateLimiter:
    """按 RPM 限制提交速率。"""

    def __init__(self, rpm):
        self.min_interval = (60.0 / rpm) if rpm and rpm > 0 else 0.0
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self):
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.time()
            delay = self._last + self.min_interval - now
            if delay > 0:
                time.sleep(delay)
            self._last = time.time()


def run_batch(items, fn, concurrency=10, rpm=None, retries=2, backoff=1.0):
    """并发执行 fn(item)，带重试与限流。

    返回 (results, failures)，failures 元素为 (item, last_exception)。
    """
    limiter = RateLimiter(rpm)
    results = []
    failures = []
    lock = threading.Lock()

    def worker(item):
        last = None
        for attempt in range(retries + 1):
            try:
                limiter.wait()
                return ("ok", fn(item))
            except Exception as exc:  # noqa: BLE001
                last = exc
                time.sleep(backoff * (attempt + 1))
        return ("fail", (item, last))

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futures = [ex.submit(worker, it) for it in items]
        for fut in as_completed(futures):
            status, payload = fut.result()
            with lock:
                if status == "ok":
                    results.append(payload)
                else:
                    failures.append(payload)

    return results, failures
