# -*- coding: utf-8 -*-
"""三格的本地提醒进程。

浏览器通过 127.0.0.1:47821 同步日程；本进程提前 30 分钟弹出一个置顶小窗。
依赖 Python 3 标准库，不需要联网。
"""
from __future__ import annotations

import datetime as dt
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import queue
import threading
import time
import tkinter as tk

HERE = Path(__file__).resolve().parent
STATE_FILE = HERE / "reminder-state.json"
HOST = "127.0.0.1"
PORT = 47821
LOCK = threading.Lock()
NOTIFY_QUEUE: queue.Queue = queue.Queue()
SHUTDOWN = threading.Event()
ROOT = None


def load_state():
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return {
            "items": list(data.get("items", [])),
            "notified": dict(data.get("notified", {})),
        }
    except Exception:
        return {"items": [], "notified": {}}


def save_state(state):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


STATE = load_state()


def reminder_key(item):
    return str(item.get("id", "")) + "|" + str(item.get("startAt", ""))


def parse_start(item):
    try:
        return dt.datetime.fromisoformat(item["startAt"])
    except Exception:
        return None


def due_items(now=None):
    now = now or dt.datetime.now()
    due = []
    for item in list(STATE["items"]):
        start = parse_start(item)
        if not start:
            continue
        lead = item.get("remindBefore", 30)
        if lead is None:
            continue
        try:
            lead = max(0, min(10080, int(lead)))
        except (TypeError, ValueError):
            lead = 30
        remind_at = start - dt.timedelta(minutes=lead)
        key = reminder_key(item)
        if remind_at <= now <= start + dt.timedelta(minutes=2) and key not in STATE["notified"]:
            due.append(item)
    return due


def scheduler():
    while not SHUTDOWN.is_set():
        now = dt.datetime.now()
        with LOCK:
            due = due_items(now)
            if due:
                for item in due:
                    STATE["notified"][reminder_key(item)] = now.isoformat(timespec="seconds")
                save_state(STATE)
        if due:
            NOTIFY_QUEUE.put(due)
        SHUTDOWN.wait(10)


class Handler(BaseHTTPRequestHandler):
    server_version = "SanGeReminder/1.0"

    def _headers(self, status=200):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

    def _json(self, obj, status=200):
        self._headers(status)
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._headers(204)

    def do_GET(self):
        if self.path != "/status":
            return self._json({"ok": False}, 404)
        with LOCK:
            self._json({
                "ok": True,
                "items": len(STATE["items"]),
                "notified": len(STATE["notified"]),
            })

    def do_POST(self):
        if self.path == "/shutdown":
            SHUTDOWN.set()
            self._json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if self.path != "/sync":
            return self._json({"ok": False}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 2_000_000:
                raise ValueError("bad body")
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            items = body.get("items", [])
            valid = []
            for item in items:
                start = parse_start(item)
                if not start or not item.get("title"):
                    continue
                valid.append({
                    "id": str(item.get("id", ""))[:200],
                    "title": str(item["title"])[:300],
                    "startAt": start.isoformat(timespec="minutes"),
                    "where": str(item.get("where", ""))[:300],
                    "kind": str(item.get("kind", "日程"))[:30],
                    "remindBefore": item.get("remindBefore", 30),
                })
            with LOCK:
                STATE["items"] = sorted(valid, key=lambda x: x["startAt"])
                active = {reminder_key(x) for x in valid}
                STATE["notified"] = {
                    k: v for k, v in STATE["notified"].items() if k in active
                }
                save_state(STATE)
            self._json({"ok": True, "items": len(valid)})
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 400)

    def log_message(self, *_args):
        pass


class Notifier:
    def __init__(self, root):
        self.root = root
        self.window = None
        self.close_job = None
        root.after(400, self.poll)

    def poll(self):
        batch = []
        while True:
            try:
                batch.extend(NOTIFY_QUEUE.get_nowait())
            except queue.Empty:
                break
        if batch:
            self.show(batch)
        self.root.after(400, self.poll)

    def close(self):
        if self.close_job:
            self.root.after_cancel(self.close_job)
            self.close_job = None
        if self.window:
            self.window.destroy()
            self.window = None

    def show(self, items):
        self.close()
        win = tk.Toplevel(self.root)
        self.window = win
        win.title("三格提醒")
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        transparent = "#01ff02"
        try:
            win.attributes("-transparentcolor", transparent)
        except tk.TclError:
            transparent = "#202329"
        win.configure(bg=transparent)
        win.resizable(False, False)
        shown = items[:3]
        lead = shown[0].get("remindBefore", 30) if shown else 30
        lead_text = "到点提醒" if lead == 0 else f"提前 {lead} 分钟提醒"
        width, height = 520, 178 + len(shown)*66
        x = max(18, win.winfo_screenwidth() - width - 28)
        win.geometry(f"{width}x{height}+{x}+28")
        canvas = tk.Canvas(win, width=width, height=height, bg=transparent,
                           highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)

        def rounded(x1, y1, x2, y2, radius, fill, tags=()):
            points = [
                x1+radius,y1, x2-radius,y1, x2,y1, x2,y1+radius,
                x2,y2-radius, x2,y2, x2-radius,y2, x1+radius,y2,
                x1,y2, x1,y2-radius, x1,y1+radius, x1,y1
            ]
            return canvas.create_polygon(
                points, smooth=True, splinesteps=28, fill=fill,
                outline="", tags=tags
            )

        # 参考桌面电量挂件的深色圆角悬浮卡样式。
        rounded(8, 10, width-4, height-2, 22, "#11151b")
        rounded(3, 3, width-9, height-10, 22, "#20242b")
        rounded(24, 24, 76, 76, 13, "#24668d")
        canvas.create_text(50, 50, text=str(lead), fill="#fff", font=("Segoe UI", 20, "bold"))
        canvas.create_text(94, 36, text="三格 · 即将开始", anchor="w",
                           fill="#fff", font=("Microsoft YaHei UI", 20, "bold"))
        canvas.create_text(95, 66, text=lead_text, anchor="w",
                           fill="#aeb5bf", font=("Microsoft YaHei UI", 11))
        canvas.create_text(width-28, 31, text="×", fill="#c7ccd3", anchor="center",
                           font=("Microsoft YaHei UI", 18), tags=("close",))
        canvas.tag_bind("close", "<Button-1>", lambda _e: self.close())

        now = dt.datetime.now()
        for index, item in enumerate(shown):
            start = parse_start(item)
            minutes = max(0, round((start-now).total_seconds()/60)) if start else 0
            top = 92 + index*66
            canvas.create_text(94, top+9, text=item["title"], anchor="w",
                               fill="#fff", font=("Microsoft YaHei UI", 14, "bold"))
            meta = f"{start:%H:%M} · {item['where'] or item['kind']}"
            canvas.create_text(94, top+36, text=meta, anchor="w",
                               fill="#aeb5bf", font=("Microsoft YaHei UI", 10))
            canvas.create_text(width-34, top+20, text=f"还有 {minutes} 分钟", anchor="e",
                               fill="#67b8e8", font=("Microsoft YaHei UI", 11, "bold"))

        rounded(24, height-59, 136, height-21, 12, "#2f6fd0", tags=("dismiss",))
        canvas.create_text(80, height-40, text="知道了", fill="#fff",
                           font=("Microsoft YaHei UI", 11, "bold"), tags=("dismiss",))
        canvas.create_text(width-34, height-40, text=lead_text,
                           anchor="e", fill="#777f89", font=("Microsoft YaHei UI", 9))
        canvas.tag_bind("dismiss", "<Button-1>", lambda _e: self.close())
        win.bell()
        win.after(120, lambda: (win.lift(), win.focus_force()) if win.winfo_exists() else None)
        self.close_job = self.root.after(60_000, self.close)


def main():
    global ROOT
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError:
        return
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=scheduler, daemon=True).start()
    root = tk.Tk()
    root.withdraw()
    ROOT = root
    Notifier(root)

    def watch_shutdown():
        if SHUTDOWN.is_set():
            root.destroy()
        else:
            root.after(500, watch_shutdown)

    root.after(500, watch_shutdown)
    try:
        root.mainloop()
    finally:
        SHUTDOWN.set()
        server.server_close()


if __name__ == "__main__":
    main()
