# -*- coding: utf-8 -*-
"""分诊台 —— 一个只做一件事的小工具。

把脑子里冒出来的东西，当场分成三格：
  待办  占屏，办完划掉消失（这是唯一"要你动手"的分区）
  有期  只显示还剩几天，不催
  念头  不催、不能勾，只能"转成待办"或"先搁下"（长期的事住这里，别住待办）

用法：
  双击 triage.pyw            —— 打开悬浮窗（无边框、置顶、可拖）
  窗口底部输入框打字          —— 回车默认进"待办"
  文本里写 @11-01 / @2026-11-01 —— 自动进"有期"并带上日期
  点三个按钮                 —— 强制选一格，没有"待会再说"
  header 上 ─ 折叠成一条，× 退出

命令行（给我自己调试和批量灌数据用）：
  python triage.pyw --list
  python triage.pyw --add "整理书桌 还没挑" --kind idea
"""

import json
import os
import re
import sys
import datetime

try:
    import tkinter as tk
except Exception:          # 没有 tkinter 时命令行部分仍可用
    tk = None

DATA_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "triage.json")

DATE_RE = re.compile(r"@\s*(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[-/]\d{1,2})")
KINDS = ("todo", "dated", "ideas")


# ---------- 数据 ----------

def load(path):
    if not os.path.exists(path):
        return {"todo": [], "dated": [], "ideas": [], "ui": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return {"todo": [], "dated": [], "ideas": [], "ui": {}}
    if not isinstance(d, dict):
        d = {}
    for k in KINDS:
        if not isinstance(d.get(k), list):
            d[k] = []
    if not isinstance(d.get("ui"), dict):
        d["ui"] = {}
    return d


def save(path, d):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def now_iso():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")


def parse_date(text, today=None):
    """把 '英语作文 @11-01' 拆成 (date, '英语作文')；没日期返回 (None, 原文)。"""
    today = today or datetime.date.today()
    m = DATE_RE.search(text)
    if not m:
        return None, text.strip()
    raw = m.group(1).replace("/", "-")
    parts = raw.split("-")
    try:
        if len(parts) == 3:
            d = datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
        else:
            mo, da = int(parts[0]), int(parts[1])
            d = datetime.date(today.year, mo, da)
            if d < today:                     # 已经过了就是明年
                d = datetime.date(today.year + 1, mo, da)
    except ValueError:
        return None, text.strip()
    return d, DATE_RE.sub("", text).strip()


def days_left(datestr, today=None):
    today = today or datetime.date.today()
    try:
        y, m, dd = [int(x) for x in datestr.split("-")]
        return (datetime.date(y, m, dd) - today).days
    except Exception:
        return None


def add(path, text, kind):
    d = load(path)
    text = (text or "").strip()
    if not text:
        return d
    kind = {"idea": "ideas", "ideas": "ideas", "todo": "todo",
            "dated": "dated", "date": "dated"}.get(kind, "todo")
    dt, clean = parse_date(text)
    if kind == "dated" or dt is not None:
        if dt is None:
            kind, dt = "todo", None
        else:
            d["dated"].append({"id": now_iso() + "-" + str(len(d["dated"])),
                               "text": clean, "date": dt.isoformat(), "at": now_iso()})
            save(path, d)
            return d
    if kind == "ideas":
        d["ideas"].append({"id": now_iso() + "-" + str(len(d["ideas"])),
                           "text": clean, "at": now_iso(), "parked": ""})
    else:
        d["todo"].append({"id": now_iso() + "-" + str(len(d["todo"])),
                          "text": clean, "at": now_iso()})
    save(path, d)
    return d


# ---------- 界面 ----------

BG        = "#1c1f24"
CARD      = "#2a2e36"
CARD_DIM  = "#23272e"
BAR_TODO  = "#e0574f"
BAR_DATED = "#d9a13b"
BAR_IDEA  = "#59616e"
TXT       = "#e6e8ea"
DIM       = "#98a0aa"
FAINT     = "#6b7480"

FAMILY = "Microsoft YaHei UI"


def pressure_color(n):
    if n >= 6:
        return "#e0574f"
    if n >= 3:
        return "#d9a13b"
    return "#4f9d69"


class App:
    def __init__(self, root, path):
        self.root = root
        self.path = path
        self.d = load(path)
        self.collapsed = False
        self.pressure_n = 0

        root.title("分诊")
        root.configure(bg=BG)
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        try:
            root.attributes("-alpha", 0.97)
        except Exception:
            pass

        self.f_title = tkfont("", 15, bold=True)
        self.f_body = tkfont("", 13)
        self.f_small = tkfont("", 11)
        self.f_strike = tkfont("", 13, overstrike=True)

        self.header = tk.Frame(root, bg=BG, height=52)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        self.dot = tk.Label(self.header, text="●", bg=BG, fg=pressure_color(0),
                            font=tkfont("", 9))
        self.dot.pack(side="left", padx=(10, 0), pady=8)

        self.title = tk.Label(self.header, text="分诊", bg=BG, fg=TXT, font=self.f_title)
        self.title.pack(side="left", padx=(6, 0))

        self.summary = tk.Label(self.header, text="", bg=BG, fg=FAINT, font=self.f_small)
        self.summary.pack(side="left", padx=(8, 0))

        self.btn_quit = tk.Label(self.header, text="×", bg=BG, fg=FAINT, font=tkfont("", 11),
                                 cursor="hand2", padx=8)
        self.btn_quit.pack(side="right")
        self.btn_quit.bind("<Button-1>", lambda e: self.root.destroy())
        self.btn_quit.bind("<Enter>", lambda e: self.btn_quit.config(fg=BAR_TODO))
        self.btn_quit.bind("<Leave>", lambda e: self.btn_quit.config(fg=FAINT))

        self.btn_fold = tk.Label(self.header, text="─", bg=BG, fg=FAINT, font=self.f_body,
                                 cursor="hand2", padx=6)
        self.btn_fold.pack(side="right")
        self.btn_fold.bind("<Button-1>", lambda e: self.toggle_fold())
        self.btn_fold.bind("<Enter>", lambda e: self.btn_fold.config(fg=TXT))
        self.btn_fold.bind("<Leave>", lambda e: self.btn_fold.config(fg=FAINT))

        for w in (self.header, self.dot, self.title, self.summary):
            w.bind("<Button-1>", self.drag_start)
            w.bind("<B1-Motion>", self.drag_move)

        self.body = tk.Frame(root, bg=BG)
        self.body.pack(fill="both", expand=True)

        self.footer = tk.Frame(root, bg=BG)
        self.footer.pack(fill="x", side="bottom")

        self.entry = tk.Entry(self.footer, bg=CARD, fg=TXT, insertbackground=TXT,
                             relief="flat", font=self.f_body)
        self.entry.pack(side="top", fill="x", padx=12, pady=(6, 6), ipady=7)
        self.entry.bind("<Return>", lambda e: self.submit("todo"))
        self.entry.bind("<Escape>", lambda e: self.root.destroy())

        row = tk.Frame(self.footer, bg=BG)
        row.pack(fill="x", padx=14, pady=(0, 12))
        for label, kind, color in (("待办", "todo", BAR_TODO),
                                   ("有期", "dated", BAR_DATED),
                                   ("念头", "ideas", BAR_IDEA)):
            b = tk.Label(row, text=label, bg=CARD_DIM, fg=color, font=self.f_small,
                         padx=14, pady=5, cursor="hand2")
            b.pack(side="left", padx=(0, 6))
            b.bind("<Button-1>", lambda e, k=kind: self.submit(k))
            b.bind("<Enter>", lambda e, w=b: w.config(bg=CARD))
            b.bind("<Leave>", lambda e, w=b: w.config(bg=CARD_DIM))

        self.hint = tk.Label(row, text="", bg=BG, fg=FAINT, font=self.f_small)
        self.hint.pack(side="left", padx=(4, 0))

        self.render()
        self.place_window()

    # --- 窗口 ---

    def place_window(self):
        ui = self.d.get("ui", {})
        x = ui.get("x")
        y = ui.get("y")
        try:
            sw = self.root.winfo_screenwidth()
        except Exception:
            sw = 1920
        self.root.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        if not isinstance(x, int) or x < -50 or x > sw:
            x = sw - 500
        if not isinstance(y, int) or y < -50:
            y = 80
        self.root.geometry("%dx%d+%d+%d" % (max(w, 340), h, x, y))

    def drag_start(self, e):
        self._dx, self._dy = e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y()

    def drag_move(self, e):
        x, y = e.x_root - self._dx, e.y_root - self._dy
        self.root.geometry("+%d+%d" % (x, y))
        self.d.setdefault("ui", {})["x"] = x
        self.d["ui"]["y"] = y

    def toggle_fold(self):
        if not self.collapsed:
            self.d.setdefault("ui", {})["x"] = self.root.winfo_x()
            self.d["ui"]["y"] = self.root.winfo_y()
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.body.pack_forget()
            self.footer.pack_forget()
            self.entry.pack_forget()
        else:
            self.body.pack(fill="both", expand=True)
            self.footer.pack(fill="x", side="bottom")
            self.entry.pack(side="top", fill="x", padx=12, pady=(6, 6), ipady=7)
            self.render()
        self.root.update_idletasks()
        self.fit()

    # --- 渲染 ---

    def clear(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    def label(self, parent, text, fg=TXT, font=None, bg=BG, **kw):
        return tk.Label(parent, text=text, fg=fg, bg=bg, anchor="w",
                        font=font or self.f_body, justify="left",
                        wraplength=420, **kw)

    def fit(self):
        self.root.update_idletasks()
        w = max(self.root.winfo_reqwidth(), 460)
        h = self.root.winfo_reqheight()
        self.root.geometry("%dx%d" % (w, h))

    def section(self, title, count, color, hint=""):
        head = tk.Frame(self.body, bg=BG)
        head.pack(fill="x", padx=14, pady=(10, 3))
        tk.Label(head, text=title, fg=color, bg=BG, font=self.f_small).pack(side="left")
        tk.Label(head, text=" %d" % count, fg=FAINT, bg=BG, font=self.f_small).pack(side="left")
        if hint:
            tk.Label(head, text=hint, fg=FAINT, bg=BG, font=self.f_small).pack(side="right")
        return head

    def render(self):
        if self.collapsed:
            return
        self.clear(self.body)
        d = self.d
        n_todo = len(d["todo"])
        self.pressure_n = n_todo
        self.dot.config(fg=pressure_color(n_todo))
        parts = []
        if n_todo:
            parts.append("待办 %d" % n_todo)
        if d["dated"]:
            parts.append("有期 %d" % len(d["dated"]))
        if d["ideas"]:
            parts.append("念头 %d" % len(d["ideas"]))
        self.summary.config(text="· " + "  ".join(parts) if parts else "· 空着")

        # 待办
        self.section("待办", n_todo, BAR_TODO, "占屏的就是它")
        if not n_todo:
            self.label(self.body, "  没有要动手的事", fg=FAINT, font=self.f_small).pack(
                fill="x", padx=16)
        for item in d["todo"]:
            self.todo_row(item)

        # 有期
        if d["dated"]:
            self.section("有期", len(d["dated"]), BAR_DATED, "只看剩几天")
            for item in sorted(d["dated"], key=lambda i: i.get("date", "")):
                self.dated_row(item)
        else:
            self.section("有期", 0, BAR_DATED, "")
            self.label(self.body, "  没有带日期的", fg=FAINT, font=self.f_small).pack(
                fill="x", padx=16)

        # 念头
        self.section("念头", len(d["ideas"]), BAR_IDEA, "不催，只能转走或搁下")
        if not d["ideas"]:
            self.label(self.body, "  没有悬着的事", fg=FAINT, font=self.f_small).pack(
                fill="x", padx=16)
        for item in d["ideas"]:
            self.idea_row(item)

        self.root.update_idletasks()
        self.fit()

    def row_frame(self, color):
        f = tk.Frame(self.body, bg=CARD)
        f.pack(fill="x", padx=14, pady=1)
        bar = tk.Frame(f, bg=color, width=3)
        bar.pack(side="left", fill="y")
        return f

    def todo_row(self, item):
        f = self.row_frame(BAR_TODO)
        txt = self.label(f, item["text"], bg=CARD)
        txt.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=5)
        done = tk.Label(f, text="✓", fg=FAINT, bg=CARD, font=self.f_body,
                        cursor="hand2", padx=8)
        done.pack(side="right")
        done.bind("<Button-1>", lambda e, i=item, t=txt: self.finish(i, t))
        done.bind("<Enter>", lambda e: done.config(fg="#4f9d69"))
        done.bind("<Leave>", lambda e: done.config(fg=FAINT))

    def finish(self, item, label):
        label.config(font=self.f_strike, fg=FAINT)   # 先划掉
        self.root.after(260, lambda: self.remove("todo", item["id"]))

    def remove(self, kind, item_id):
        self.d[kind] = [i for i in self.d[kind] if i["id"] != item_id]
        save(self.path, self.d)
        self.render()

    def dated_row(self, item):
        left = days_left(item.get("date", ""))
        f = self.row_frame(BAR_DATED)
        txt = self.label(f, item["text"], bg=CARD)
        txt.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=5)
        done = tk.Label(f, text="✓", fg=FAINT, bg=CARD, font=self.f_body,
                        cursor="hand2", padx=6)
        done.pack(side="right")
        done.bind("<Button-1>", lambda e, i=item, t=txt: self.finish(i, t))
        if left is None:
            tag, col = "??", FAINT
        elif left < 0:
            tag, col = "过 %d 天" % (-left), BAR_TODO
        elif left == 0:
            tag, col = "今天", BAR_TODO
        elif left <= 3:
            tag, col = "剩 %d 天" % left, BAR_DATED
        else:
            tag, col = "%d 天后" % left, DIM
        tk.Label(f, text=tag, fg=col, bg=CARD, font=self.f_small,
                 padx=6).pack(side="right")

    def idea_row(self, item):
        f = self.row_frame(BAR_IDEA)
        txt = self.label(f, item["text"], bg=CARD_DIM, fg=DIM, font=self.f_small)
        txt.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=4)
        to_todo = tk.Label(f, text="→待办", fg=FAINT, bg=CARD_DIM, font=self.f_small,
                           cursor="hand2", padx=5)
        to_todo.pack(side="right")
        to_todo.bind("<Button-1>", lambda e, i=item: self.idea_to_todo(i))
        to_todo.bind("<Enter>", lambda e: to_todo.config(fg=TXT))
        to_todo.bind("<Leave>", lambda e: to_todo.config(fg=FAINT))
        drop = tk.Label(f, text="搁下", fg=FAINT, bg=CARD_DIM, font=self.f_small,
                        cursor="hand2", padx=5)
        drop.pack(side="right")
        drop.bind("<Button-1>", lambda e, i=item: self.remove("ideas", i["id"]))
        drop.bind("<Enter>", lambda e: drop.config(fg=TXT))
        drop.bind("<Leave>", lambda e: drop.config(fg=FAINT))

    # --- 动作 ---

    def flash(self, msg):
        self.hint.config(text=msg)
        self.root.after(1600, lambda: self.hint.config(text=""))

    def submit(self, kind):
        text = self.entry.get().strip()
        if not text:
            self.entry.focus_set()
            return
        dt, clean = parse_date(text)
        if kind == "dated" and dt is None:
            self.flash("写个日期，比如 @11-01")
            return
        self.entry.delete(0, "end")
        self.d = add(self.path, text, kind)
        self.render()
        if dt is not None:
            self.flash("进有期 · %s" % dt.isoformat())

    def idea_to_todo(self, item):
        self.d["ideas"] = [i for i in self.d["ideas"] if i["id"] != item["id"]]
        self.d["todo"].append({"id": now_iso() + "-t", "text": item["text"], "at": now_iso()})
        save(self.path, self.d)
        self.render()


from tkinter import font as tkfont_mod  # noqa: E402


def tkfont(fam, size, bold=False, overstrike=False):
    from tkinter import font as F
    f = F.Font(family=FAMILY if fam == "" else fam, size=size)
    f.configure(weight="bold" if bold else "normal")
    if overstrike:
        f.configure(overstrike=True)
    return f


# ---------- 命令行 ----------

def cli(argv):
    path = DATA_DEFAULT
    args = list(argv)
    if "--data" in args:
        i = args.index("--data")
        path = args[i + 1]
        del args[i:i + 2]
    if "--list" in args:
        d = load(path)
        for k in KINDS:
            print("[%s]" % k)
            for it in d[k]:
                extra = ("  " + it["date"]) if k == "dated" else ""
                print("  - " + it["text"] + extra)
        return 0
    if "--add" in args:
        i = args.index("--add")
        text = args[i + 1]
        kind = "todo"
        if "--kind" in args:
            kind = args[args.index("--kind") + 1]
        add(path, text, kind)
        print("ok")
        return 0
    if "--uitest" in args:
        import tempfile
        import tkinter as tk
        tmp = os.path.join(tempfile.gettempdir(), "triage_ui.json")
        if os.path.exists(tmp):
            os.remove(tmp)
        add(tmp, "英语作文 @11-01", "dated")
        add(tmp, "回一条该回的消息", "todo")
        add(tmp, "示例念头：换一把椅子", "ideas")
        root = tk.Tk()
        root.withdraw()
        app = App(root, tmp)
        root.update_idletasks()
        print("size", root.winfo_reqwidth(), root.winfo_reqheight())
        app.render()
        root.update_idletasks()
        app.toggle_fold()
        root.update_idletasks()
        app.toggle_fold()
        root.update_idletasks()
        app.remove("todo", app.d["todo"][0]["id"])
        root.update_idletasks()
        root.destroy()
        print("uitest ok")
        return 0
    if "--selftest" in args:
        import tempfile
        tmp = os.path.join(tempfile.gettempdir(), "triage_selftest.json")
        if os.path.exists(tmp):
            os.remove(tmp)
        add(tmp, "英语作文 @11-01", "dated")
        add(tmp, "回消息", "todo")
        add(tmp, "示例念头 还没挑好", "idea")
        d = load(tmp)
        assert len(d["dated"]) == 1, d
        assert len(d["ideas"]) == 1, d
        assert len(d["todo"]) == 1, d
        assert len(d["dated"]) == 1, d
        assert d["dated"][0]["date"].endswith("-11-01"), d["dated"]
        assert d["dated"][0]["text"] == "英语作文", d["dated"]
        assert days_left("2099-01-01") > 0
        assert parse_date("x @11-01")[0] is not None
        print("selftest ok")
        return 0
    return 2


def enable_dpi():
    """必须在建 Tk() 之前调用：否则 Tk 先按 96dpi 定好字体缩放，
    200% 屏上文字就只有一半大。"""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main():
    if len(sys.argv) > 1:
        sys.exit(cli(sys.argv[1:]))

    path = DATA_DEFAULT
    try:
        import tkinter as tk
    except Exception as e:
        print("没有 tkinter: %s" % e)
        return
    enable_dpi()
    root = tk.Tk()
    App(root, path)
    root.mainloop()


if __name__ == "__main__":
    main()
