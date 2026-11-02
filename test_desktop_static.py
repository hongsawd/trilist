# -*- coding: utf-8 -*-
"""桌面壳静态验收：入口、全局快捷键、提醒桥和种子数据。"""
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
DESKTOP = HERE / "desktop"


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("ok:", name)


package = json.loads((DESKTOP / "package.json").read_text(encoding="utf-8"))
main = (DESKTOP / "main.js").read_text(encoding="utf-8")
preload = (DESKTOP / "preload.js").read_text(encoding="utf-8")
notice = (DESKTOP / "notification.html").read_text(encoding="utf-8")
seed = json.loads((DESKTOP / "seed-data.json").read_text(encoding="utf-8"))

check("桌面入口", package.get("main") == "main.js")
check("全局完整侧栏快捷键", "Control+Alt+Space" in main)
check("全局近期窗口快捷键", 'const QUICK_HOTKEY = "Control+Alt+Q"' in main)
check("渲染进程桥接", "syncReminders" in preload and "openQuick" in preload)
check("独立近期窗口模式", 'query:{peek:"1"}' in main and "peek-only" in (HERE / "index.html").read_text(encoding="utf-8"))
check("提醒样式", "background:#fff" in notice and "提前 30 分钟" in notice)
check("种子数据齐全", all(isinstance(seed.get(k), list) for k in ("todo", "dated", "ideas", "done")))
check("桌面图标", (DESKTOP / "icon.png").stat().st_size > 1000)

for script in ("main.js", "preload.js"):
    result = subprocess.run(
        ["node", "--check", str(DESKTOP / script)],
        capture_output=True, text=True, timeout=20
    )
    check(script + " 语法", result.returncode == 0, result.stderr[-500:])

print("desktop static ok")
