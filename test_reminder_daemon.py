# -*- coding: utf-8 -*-
"""提醒进程的纯逻辑测试，不弹出窗口。"""
import datetime as dt
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("reminder_daemon", HERE / "reminder_daemon.pyw")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("ok:", name)


now = dt.datetime(2026, 10, 30, 11, 0)
items = [
    {"id": "soon", "title": "项目例会", "startAt": "2026-10-30T11:30:00", "where": "会议室", "kind": "日程"},
    {"id": "later", "title": "午饭", "startAt": "2026-10-30T12:30:00", "where": "", "kind": "日程"},
]
mod.STATE = {"items": items, "notified": {}}
due = mod.due_items(now)
check("提前三十分钟触发", [x["id"] for x in due] == ["soon"], due)

mod.STATE["notified"][mod.reminder_key(items[0])] = now.isoformat()
check("同一事项不重复提醒", mod.due_items(now) == [])

mod.STATE = {"items": items, "notified": {}}
check("未进入提醒窗口不提前触发", mod.due_items(dt.datetime(2026, 10, 30, 10, 50)) == [])
print("reminder daemon ok")
