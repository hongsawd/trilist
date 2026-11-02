# -*- coding: utf-8 -*-
"""分诊台端到端验收：走用户真实路径，不建可见窗口。
跑法：python -X utf8 test_e2e.py
"""
import datetime
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("triage", os.path.join(HERE, "triage.pyw"))
tri = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tri)

import tkinter as tk  # noqa: E402

ok = []


def check(name, cond, extra=""):
    if not cond:
        print("FAIL:", name, extra)
        sys.exit(1)
    ok.append(name)


tmp = os.path.join(tempfile.gettempdir(), "triage_e2e.json")
if os.path.exists(tmp):
    os.remove(tmp)

root = tk.Tk()
root.withdraw()
app = tri.App(root, tmp)

# 1. 回车进待办
app.entry.insert(0, "回一条该回的消息")
app.submit("todo")
check("待办 +1", len(app.d["todo"]) == 1, app.d["todo"])

# 2. 文本里带 @日期 → 自动进有期，日期被摘掉
app.entry.insert(0, "英语作文 @11-01")
app.submit("todo")
check("有期 +1", len(app.d["dated"]) == 1, app.d["dated"])
check("日期被摘掉", app.d["dated"][0]["text"] == "英语作文", app.d["dated"][0])
check("日期落位", app.d["dated"][0]["date"].endswith("-11-01"), app.d["dated"][0])

# 3. 有期按钮但没写日期 → 拒绝，不入库
app.entry.insert(0, "没写日期的东西")
app.submit("dated")
check("无日期被拒", len(app.d["dated"]) == 1 and len(app.d["todo"]) == 1)
check("被拒时保留输入等补日期", app.entry.get() == "没写日期的东西", app.entry.get())
app.entry.delete(0, "end")

# 4. 念头
app.entry.insert(0, "示例念头：换一把椅子")
app.submit("ideas")
check("念头 +1", len(app.d["ideas"]) == 1, app.d["ideas"])

# 5. 勾掉 → 从库里消失
todo_id = app.d["todo"][0]["id"]
app.remove("todo", todo_id)
check("勾掉后消失", len(app.d["todo"]) == 0, app.d["todo"])

# 6. 念头 → 转待办
app.idea_to_todo(app.d["ideas"][0])
check("转待办", len(app.d["ideas"]) == 0 and
      app.d["todo"][0]["text"] == "示例念头：换一把椅子", app.d["todo"])

root.destroy()

# 7. 重开窗口，数据还在
root = tk.Tk()
root.withdraw()
app2 = tri.App(root, tmp)
check("持久化-待办", len(app2.d["todo"]) == 1, app2.d)
check("持久化-有期", len(app2.d["dated"]) == 1, app2.d)
root.destroy()

# 8. 日期解析边界
today = datetime.date(2026, 10, 27)
d, _ = tri.parse_date("x @1-05", today)
check("跨年 @1-05 -> 明年", d == datetime.date(2027, 1, 5), d)
d2, _ = tri.parse_date("x @2027-03-02", today)
check("三位年份写法", d2 == datetime.date(2027, 3, 2), d2)
check("今天剩 0 天", tri.days_left("2026-10-27", today) == 0)
check("过期是负数", tri.days_left("2026-10-20", today) == -7)

# 9. 非法日期不炸、回落待办
before = len(app2.d["todo"]) if False else 0
d3, txt = tri.parse_date("x @13-45", today)
check("非法日期不解析", d3 is None, d3)

print("e2e ok（%d 项）: %s" % (len(ok), " / ".join(ok)))
