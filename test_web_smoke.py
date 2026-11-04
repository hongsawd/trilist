# -*- coding: utf-8 -*-
"""Web 主界面无头冒烟测试。

只依赖标准库和本机 Edge。验证脚本能启动、页面不报错、两个视图都能渲染，
并生成一张截图供人工检查。跑法：python -X utf8 test_web_smoke.py
"""
import datetime
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
PAGE = HERE / "index.html"
EDGE_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


def find_edge():
    for path in EDGE_CANDIDATES:
        if path.is_file():
            return path
    raise RuntimeError("找不到 Microsoft Edge")


def run_edge(edge, profile, args):
    flags = [
        str(edge),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--hide-scrollbars",
        f"--user-data-dir={profile}",
        "--virtual-time-budget=1000",
    ]
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(
        flags + args,
        cwd=HERE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        **kwargs,
    )


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("ok:", name)


def main():
    edge = find_edge()
    page_url = PAGE.as_uri()
    with tempfile.TemporaryDirectory(prefix="triage-web-") as tmp:
        board = run_edge(edge, Path(tmp) / "board-profile", ["--dump-dom", page_url])
        check("看板进程", board.returncode == 0, board.stderr[-500:])
        dom = board.stdout
        check("无脚本启动错误", "<title>ERR @" not in dom, dom[:300])
        check("应用名称与页码指示存在", "<title>三格</title>" in dom and 'id="viewPosition"' in dom)
        check("看板默认数据已渲染", "写周报" in dom and "示例日程 A" in dom)
        check("念头普通列已渲染", 'id="list-ideas"' in dom and "idea-card" in dom)
        check(
            "今日念头卡已渲染",
            'id="ideaSpotlight"' in dom
            and 'class="spot-card"' in dom
            and 'id="ideaSpotCount"' in dom
            and "THOUGHT OF THE DAY" not in dom,
        )
        check("备份入口存在", 'id="exportBtn"' in dom and 'id="importFile"' in dom)
        check(
            "行内编辑与撤销入口存在",
            'data-edit' in dom and 'id="undoToast"' in dom and 'id="editDialog"' not in dom,
        )
        check(
            "积木输入默认念头",
            'class="kind on" data-k="ideas"' in dom
            and 'id="blockFields"' in dom
            and 'id="blockDate"' in dom,
        )
        check(
            "课表与日期快捷键入口存在",
            'data-view="course"' in dom
            and 'id="courseGrid"' in dom
            and "Ctrl+;" in dom,
        )
        check(
            "键盘帮助与快捷弹窗存在",
            'id="helpPanel"' in dom and 'id="peekPanel"' in dom and 'id="modeBadge"' in dom,
        )

        cal = run_edge(
            edge,
            Path(tmp) / "cal-profile",
            ["--dump-dom", page_url + "?view=cal"],
        )
        check("日历进程", cal.returncode == 0, cal.stderr[-500:])
        month = datetime.date.today().strftime("%Y 年 %m 月").replace(" 0", " ")
        check("日历默认打开", 'id="view-cal"' in cal.stdout and month in cal.stdout)
        check("日历无脚本启动错误", "<title>ERR @" not in cal.stdout)

        quick = run_edge(
            edge,
            Path(tmp) / "quick-profile",
            ["--dump-dom", page_url + "?peek=1"],
        )
        check("独立近期面板", quick.returncode == 0, quick.stderr[-500:])
        check(
            "独立近期面板只显示清单",
            '<body class="peek-only">' in quick.stdout
            and 'id="peekPanel"' in quick.stdout
            and "<title>ERR @" not in quick.stdout,
        )

        shot = Path(tmp) / "board.png"
        result = run_edge(
            edge,
            Path(tmp) / "shot-profile",
            ["--window-size=1400,1000", f"--screenshot={shot}", page_url],
        )
        check("截图进程", result.returncode == 0, result.stderr[-500:])
        check("截图非空", shot.is_file() and shot.stat().st_size > 20_000)

    print("web smoke ok")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL:", exc, file=sys.stderr)
        raise SystemExit(1)
