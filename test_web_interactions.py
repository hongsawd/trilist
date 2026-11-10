# -*- coding: utf-8 -*-
"""Web 主界面交互验收。

依赖：Python 3、本机 Edge、websocket-client。
跑法：python -X utf8 test_web_interactions.py
测试使用临时浏览器配置，不会改动日常 localStorage。
"""
import datetime
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

try:
    import websocket
except ImportError as exc:
    raise SystemExit("缺少测试依赖：python -m pip install websocket-client") from exc

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


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=10)
        self.seq = 0

    def call(self, method, **params):
        self.seq += 1
        self.ws.send(json.dumps({"id": self.seq, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") != self.seq:
                continue
            if "error" in msg:
                raise RuntimeError(msg["error"])
            return msg.get("result", {})

    def eval(self, expression):
        out = self.call(
            "Runtime.evaluate",
            expression=expression,
            returnByValue=True,
            awaitPromise=True,
        )
        result = out["result"]
        if result.get("subtype") == "error":
            raise RuntimeError(result.get("description"))
        return result.get("value")


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("ok:", name)


def main():
    edge = find_edge()
    target_day = datetime.date.today() + datetime.timedelta(days=2)
    compact = target_day.strftime("%m.%d")
    weekday = "一二三四五六日"[target_day.weekday()]

    with tempfile.TemporaryDirectory(
        prefix="triage-cdp-", ignore_cleanup_errors=True
    ) as tmp:
        port = free_port()
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        proc = subprocess.Popen(
            [
                str(edge), "--headless=new", "--disable-gpu", "--no-first-run",
                f"--remote-debugging-port={port}", f"--user-data-dir={tmp}",
                (PAGE.as_uri() + "?demo=1"),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
        try:
            targets = None
            for _ in range(60):
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/json/list", timeout=1
                    ) as response:
                        targets = json.load(response)
                    if targets:
                        break
                except Exception:
                    time.sleep(.1)
            check("浏览器已连接", bool(targets), targets)
            page = next(t for t in targets if t.get("type") == "page")
            cdp = CDP(page["webSocketDebuggerUrl"])
            cdp.call("Runtime.enable")
            time.sleep(.4)

            spotlight_text = cdp.eval("document.querySelector('#ideaSpotText').textContent")
            check(
                "启动时浮出今日念头",
                bool(spotlight_text)
                and cdp.eval("document.querySelector('#ideaSpotlight').hidden") is False
                and cdp.eval("document.querySelector('#ideaSpotlight').classList.contains('show')"),
            )
            cdp.eval("document.querySelector('#ideaSpotClose').click()")
            time.sleep(.35)
            check(
                "收回浮签后回到普通念头列",
                cdp.eval("document.querySelector('#ideaSpotlight').hidden") is True
                and any(
                    spotlight_text in (x.get("text") or "")
                    for x in cdp.eval("""Array.from(document.querySelectorAll('#list-ideas .idea-card'))
                      .map(x=>({text:x.textContent}))""")
                ),
            )

            cdp.eval(
                "document.body.dispatchEvent(new KeyboardEvent('keydown', "
                "{key:'i', bubbles:true, cancelable:true}))"
            )
            check(
                "I 键进入输入模式",
                cdp.eval("document.activeElement.id") == "inp"
                and cdp.eval("document.querySelector('#modeBadge').textContent") == "INSERT",
            )
            cdp.eval(
                "document.querySelector('#inp').dispatchEvent("
                "new KeyboardEvent('keydown', {key:'Escape', bubbles:true, cancelable:true}))"
            )
            time.sleep(.05)
            check(
                "Esc 返回普通模式",
                cdp.eval("document.querySelector('#modeBadge').textContent") == "NORMAL",
            )
            cdp.eval(
                "document.body.dispatchEvent(new KeyboardEvent('keydown', "
                "{key:'2', bubbles:true, cancelable:true}))"
            )
            check(
                "数字键切换到待办并聚焦输入",
                cdp.eval("document.querySelector('.kind.on').dataset.k") == "todo"
                and cdp.eval("document.activeElement.id") == "inp",
            )
            cdp.eval(
                "document.querySelector('#inp').dispatchEvent(new KeyboardEvent('keydown', "
                "{key:'1', altKey:true, bubbles:true, cancelable:true}))"
            )
            check(
                "Alt+1 在输入中切回念头",
                cdp.eval("document.querySelector('.kind.on').dataset.k") == "ideas",
            )
            cdp.eval(
                "document.querySelector('#inp').dispatchEvent("
                "new KeyboardEvent('keydown', {key:'Escape', bubbles:true, cancelable:true}))"
            )
            time.sleep(.05)

            cdp.eval("""(()=>{
              const i=document.querySelector('#inp');
              i.value='默认只进念头';
              i.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', bubbles:true}));
            })()""")
            stored = cdp.eval("JSON.parse(localStorage.getItem('triage.v2'))")
            check(
                "输入默认进念头",
                any(x["text"] == "默认只进念头" for x in stored["ideas"]),
            )
            check(
                "提交后类型复位为念头",
                cdp.eval("document.querySelector('.kind.on').dataset.k") == "ideas",
            )

            cdp.eval(
                "document.dispatchEvent(new KeyboardEvent('keydown', "
                "{key:';', code:'Semicolon', ctrlKey:true, bubbles:true, cancelable:true}))"
            )
            check(
                "Ctrl+; 打开日期并聚焦",
                cdp.eval("document.querySelector('#dateField').hidden") is False
                and cdp.eval("document.querySelector('#whereField').hidden") is False
                and cdp.eval("document.activeElement.id") == "blockDate"
                and bool(cdp.eval("document.querySelector('#blockDate').value")),
            )
            original_date = cdp.eval("document.querySelector('#blockDate').value")
            cdp.eval(
                "document.querySelector('#blockDate').dispatchEvent("
                "new KeyboardEvent('keydown', {key:'ArrowUp', bubbles:true, cancelable:true}))"
            )
            check(
                "日期可用上下键调整",
                cdp.eval("document.querySelector('#blockDate').value") != original_date,
            )
            cdp.eval(
                "document.querySelector('#blockDate').dispatchEvent("
                "new WheelEvent('wheel', {deltaY:-100, bubbles:true, cancelable:true}))"
            )
            check(
                "日期可用滚轮调整",
                cdp.eval("document.querySelector('#blockDate').value") != original_date,
            )
            cdp.eval("document.querySelector('#blockTime').value='09:00'")
            cdp.eval(
                "document.querySelector('#blockTime').dispatchEvent("
                "new WheelEvent('wheel', {deltaY:-100, bubbles:true, cancelable:true}))"
            )
            cdp.eval(
                "document.querySelector('#blockTime').dispatchEvent("
                "new WheelEvent('wheel', {deltaY:-100, bubbles:true, cancelable:true}))"
            )
            check(
                "时间滚轮按五分钟调整且不连跳",
                cdp.eval("document.querySelector('#blockTime').value") == "09:05",
            )
            cdp.eval("""(()=>{
              const d=document.querySelector('#blockDate');
              d.focus();
              d.dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowRight', bubbles:true, cancelable:true}));
            })()""")
            check("右方向键从日期切到时间", cdp.eval("document.activeElement.id") == "blockTime")
            cdp.eval(
                "document.querySelector('#blockTime').dispatchEvent("
                "new KeyboardEvent('keydown', {key:'ArrowRight', bubbles:true, cancelable:true}))"
            )
            check("右方向键从时间切到地点", cdp.eval("document.activeElement.id") == "blockWhere")
            cdp.eval(
                "document.querySelector('#blockWhere').dispatchEvent("
                "new KeyboardEvent('keydown', {key:'ArrowDown', bubbles:true, cancelable:true}))"
            )
            first_place = cdp.eval("document.querySelector('#blockWhere').value")
            cdp.eval(
                "document.querySelector('#blockWhere').dispatchEvent("
                "new KeyboardEvent('keydown', {key:'ArrowDown', bubbles:true, cancelable:true}))"
            )
            second_place = cdp.eval("document.querySelector('#blockWhere').value")
            check(
                "地点框上下选择历史地点",
                bool(first_place) and bool(second_place) and first_place != second_place,
                (first_place, second_place),
            )
            cdp.eval(
                "document.querySelector('#blockWhere').dispatchEvent("
                "new KeyboardEvent('keydown', {key:'ArrowLeft', bubbles:true, cancelable:true}))"
            )
            check("左方向键切回时间", cdp.eval("document.activeElement.id") == "blockTime")
            cdp.eval("""(()=>{
              if (!document.querySelector('#dateField').hidden) document.querySelector('[data-add="date"]').click();
              if (!document.querySelector('#whereField').hidden) document.querySelector('[data-add="where"]').click();
            })()""")

            cdp.eval("""(()=>{
              const i=document.querySelector('#inp');
              i.value='临时紧急 #紧急';
              document.querySelector('.kind[data-k="todo"]').click();
              document.querySelector('#addBtn').click();
            })()""")
            check(
                "紧急待办排在最前",
                cdp.eval("document.querySelector('#list-todo .card .text').textContent")
                == "临时紧急",
            )

            edit_id = cdp.eval(
                "document.querySelector('#list-todo .card').dataset.id"
            )
            cdp.eval(
                "document.body.dispatchEvent(new KeyboardEvent('keydown', "
                "{key:'j', bubbles:true, cancelable:true}))"
            )
            cdp.eval(
                "document.body.dispatchEvent(new KeyboardEvent('keydown', "
                "{key:'Enter', bubbles:true, cancelable:true}))"
            )
            check(
                "J/Enter 键盘打开行内编辑",
                cdp.eval("document.querySelectorAll('.inline-editor').length") == 1
                and cdp.eval("document.querySelector('#editDialog')") is None,
            )
            cdp.eval(f"""(()=>{{
              const card=document.querySelector('.inline-editor');
              card.querySelector('.inline-title').value='编辑后的紧急';
              card.querySelector('.inline-date').value='{target_day.isoformat()}';
              card.querySelector('.inline-time').value='09:30';
              card.querySelector('.inline-where').value='编辑地点';
              card.querySelector('.inline-cat').value='academic';
              card.querySelector('.inline-note').value='编辑后的备注';
            }})()""")
            cdp.eval("""(()=>{
              const card=document.querySelector('.inline-editor');
              card.querySelector('[data-clear="time"]').click();
              card.querySelector('[data-clear="where"]').click();
            })()""")
            check(
                "行内编辑可清空时间和地点",
                cdp.eval("document.querySelector('.inline-time').value") == ""
                and cdp.eval("document.querySelector('.inline-where').value") == "",
            )
            cdp.eval("""(()=>{
              const card=document.querySelector('.inline-editor');
              card.querySelector('.inline-time').value='09:30';
              card.querySelector('.inline-where').value='编辑地点';
              card.querySelector('.save').click();
            })()""")
            stored = cdp.eval("JSON.parse(localStorage.getItem('triage.v2'))")
            edited = next(x for x in stored["todo"] if x["id"] == edit_id)
            check(
                "编辑内容、日程和备注已保存",
                edited["text"] == "编辑后的紧急"
                and edited["note"] == "编辑后的备注"
                and edited["date"] == target_day.isoformat()
                and edited["where"] == "编辑地点",
                edited,
            )
            check("保存后行内编辑关闭", cdp.eval("document.querySelectorAll('.inline-editor').length") == 0)

            cdp.eval(
                f"document.querySelector('#list-todo .card[data-id=\"{edit_id}\"] [data-del]').click()"
            )
            stored = cdp.eval("JSON.parse(localStorage.getItem('triage.v2'))")
            check(
                "显式删除立即生效",
                not any(x["id"] == edit_id for x in stored["todo"]),
            )
            check("删除后出现底部撤销", cdp.eval("document.querySelector('#undoToast').classList.contains('show')") is True)
            cdp.eval("document.querySelector('#undoAction').click()")
            stored = cdp.eval("JSON.parse(localStorage.getItem('triage.v2'))")
            check("删除可以从底部撤销", any(x["id"] == edit_id for x in stored["todo"]))

            cdp.eval("""(()=>{
              const i=document.querySelector('#inp');
              i.value='无效日期 2026-02-30';
              document.querySelector('.kind[data-k="dated"]').click();
              document.querySelector('#addBtn').click();
            })()""")
            check(
                "日程必须先拼日期",
                "需要一块日期"
                in cdp.eval("document.querySelector('#note').textContent"),
            )
            check(
                "被拒输入仍保留",
                cdp.eval("document.querySelector('#inp').value")
                == "无效日期 2026-02-30",
            )

            cdp.eval(f"""(()=>{{
              const i=document.querySelector('#inp');
              i.value='写交互任务 #学业 {compact}';
              document.querySelector('.kind[data-k="todo"]').click();
              document.querySelector('#blockDate').value='{target_day.isoformat()}';
              document.querySelector('#blockTime').value='10:30';
              document.querySelector('#blockWhere').value='图书馆';
              document.querySelector('#addBtn').click();
            }})()""")
            stored = cdp.eval("JSON.parse(localStorage.getItem('triage.v2'))")
            task = next(x for x in stored["todo"] if x["text"] == "写交互任务")
            check(
                "日期积木可附加到待办",
                task["date"] == target_day.isoformat()
                and task["time"] == "10:30"
                and task["where"] == "图书馆",
                task,
            )
            cdp.eval("document.querySelector('[data-add=\"where\"]').click()")
            history_first = cdp.eval(
                "document.querySelector('#placeHistory button span').textContent"
            )
            check("地点历史按使用记录排序", history_first == "图书馆", history_first)
            cdp.eval("document.querySelector('#placeHistory button').click()")
            check(
                "地点历史可回填地址",
                cdp.eval("document.querySelector('#blockWhere').value") == "图书馆",
            )
            cdp.eval("document.querySelector('[data-add=\"where\"]').click()")

            cdp.eval("""(()=>{
              const i=document.querySelector('#inp');
              i.value='交互宣讲会';
              document.querySelector('[data-add="date"]').click();
            })()""")
            check(
                "日期积木不偷改待办类型",
                cdp.eval("document.querySelector('.kind.on').dataset.k") == "ideas"
                and cdp.eval("document.querySelector('#dateField').hidden") is False,
            )
            cdp.eval(f"""(()=>{{
              document.querySelector('.kind[data-k="dated"]').click();
              document.querySelector('#blockDate').value='{target_day.isoformat()}';
              document.querySelector('#blockTime').value='19:00';
              document.querySelector('#addBtn').click();
            }})()""")
            stored = cdp.eval("JSON.parse(localStorage.getItem('triage.v2'))")
            event = next(x for x in stored["dated"] if x["text"] == "交互宣讲会")
            check("只能等待的事件进入日程", event["date"] == target_day.isoformat(), event)

            target_iso = target_day.isoformat()
            cdp.eval("document.querySelector('.tab[data-view=\"cal\"]').click()")
            if not cdp.eval(
                f"!!document.querySelector('[data-date=\"{target_iso}\"]')"
            ):
                cdp.eval("document.querySelector('#nextM').click()")
            cdp.eval(
                f"document.querySelector('[data-date=\"{target_iso}\"]').click()"
            )
            day_text = cdp.eval("document.querySelector('#dayItems').textContent")
            check(
                "日历同时显示待办截止和日程",
                "编辑后的紧急" in day_text
                and "写交互任务" in day_text
                and "交互宣讲会" in day_text,
                day_text,
            )
            check(
                "日历不再显示课程",
                cdp.eval("document.querySelectorAll('#calGrid .ev.coursev').length") == 0,
            )
            cdp.eval("document.querySelector('.tab[data-view=\"board\"]').click()")

            cdp.eval("document.querySelector('.tab[data-view=\"course\"]').click()")
            check(
                "课表面板可打开",
                cdp.eval("document.querySelector('#view-course').hidden") is False
                and "第 " in cdp.eval("document.querySelector('#courseWeek').textContent"),
            )
            check(
                "课表课程已渲染",
                cdp.eval("document.querySelectorAll('#courseGrid .course-event').length") == 13,
            )
            course_cells = cdp.eval("""Array.from(
              document.querySelectorAll('#courseGrid .course-event')
            ).map(x=>({text:x.querySelector('b').textContent, col:x.style.gridColumn, row:x.style.gridRow}))""")
            check(
                "示例课程 C（数学）位于周二和周五第 1-2 节，周四第 3-4 节",
                any(x["text"] == "示例课程 C（数学）" and x["col"] == "3" and x["row"].startswith("2")
                    for x in course_cells)
                and any(x["text"] == "示例课程 C（数学）" and x["col"] == "6" and x["row"].startswith("2")
                    for x in course_cells)
                and any(x["text"] == "示例课程 C（数学）" and x["col"] == "5" and x["row"].startswith("4")
                    and "span 2" in x["row"] for x in course_cells),
                course_cells,
            )
            cdp.eval("""(()=>{
              const swipe=(from,to)=>{
                const main=document.querySelector('main:not([hidden])');
                main.dispatchEvent(new PointerEvent('pointerdown',{pointerId:7,pointerType:'touch',clientX:from,clientY:400,bubbles:true}));
                document.dispatchEvent(new PointerEvent('pointerup',{pointerId:7,pointerType:'touch',clientX:to,clientY:400,bubbles:true}));
              };
              swipe(700,400);
            })()""")
            check("左划切换到下一面板", cdp.eval("document.querySelector('.tab.on').dataset.view") == "board")
            cdp.eval("document.querySelector('.tab[data-view=\"board\"]').click()")
            cdp.eval("""(()=>{
              const main=document.querySelector('#view-board');
              main.dispatchEvent(new PointerEvent('pointerdown',{pointerId:8,pointerType:'touch',clientX:700,clientY:400,bubbles:true}));
              document.dispatchEvent(new PointerEvent('pointerup',{pointerId:8,pointerType:'touch',clientX:400,clientY:400,bubbles:true}));
            })()""")
            check("左划从看板进入日历", cdp.eval("document.querySelector('.tab.on').dataset.view") == "cal")
            cdp.eval("""(()=>{
              const main=document.querySelector('#view-cal');
              main.dispatchEvent(new PointerEvent('pointerdown',{pointerId:9,pointerType:'touch',clientX:700,clientY:400,bubbles:true}));
              document.dispatchEvent(new PointerEvent('pointerup',{pointerId:9,pointerType:'touch',clientX:400,clientY:400,bubbles:true}));
            })()""")
            check("左划从日历进入课表", cdp.eval("document.querySelector('.tab.on').dataset.view") == "course")
            cdp.eval("""(()=>{
              const main=document.querySelector('#view-course');
              main.dispatchEvent(new PointerEvent('pointerdown',{pointerId:10,pointerType:'touch',clientX:400,clientY:400,bubbles:true}));
              document.dispatchEvent(new PointerEvent('pointerup',{pointerId:10,pointerType:'touch',clientX:700,clientY:400,bubbles:true}));
            })()""")
            check("右划返回上一面板", cdp.eval("document.querySelector('.tab.on').dataset.view") == "cal")
            cdp.eval("document.querySelector('.tab[data-view=\"board\"]').click()")
            cdp.eval(
                "document.querySelector('#view-board').dispatchEvent("
                "new WheelEvent('wheel', {deltaX:100, deltaY:0, bubbles:true}))"
            )
            check("触控板横滑可切换面板", cdp.eval("document.querySelector('.tab.on').dataset.view") == "cal")
            cdp.eval("document.querySelector('.tab[data-view=\"board\"]').click()")
            cdp.eval(
                "document.body.dispatchEvent(new KeyboardEvent('keydown', "
                "{key:'c', bubbles:true, cancelable:true}))"
            )
            check(
                "C 键向右切换面板",
                cdp.eval("document.querySelector('.tab.on').dataset.view") == "cal"
                and cdp.eval("document.querySelector('#viewPosition').textContent") == "2/3",
            )
            cdp.eval(
                "document.body.dispatchEvent(new KeyboardEvent('keydown', "
                "{key:'x', bubbles:true, cancelable:true}))"
            )
            check(
                "X 键向左切换面板",
                cdp.eval("document.querySelector('.tab.on').dataset.view") == "board",
            )
            cdp.eval(
                "document.body.dispatchEvent(new KeyboardEvent('keydown', "
                "{key:'s', bubbles:true, cancelable:true}))"
            )
            check(
                "S 键打开近期安排弹窗",
                cdp.eval("document.querySelector('#peekPanel').hidden") is False
                and cdp.eval("document.querySelectorAll('#peekAgenda .peek-item').length") > 0
                and cdp.eval("document.querySelectorAll('#peekTodos .peek-item').length") > 0,
            )
            cdp.eval(
                "document.body.dispatchEvent(new KeyboardEvent('keydown', "
                "{key:'s', bubbles:true, cancelable:true}))"
            )
            cdp.eval(
                "document.body.dispatchEvent(new KeyboardEvent('keydown', "
                "{key:'h', bubbles:true, cancelable:true}))"
            )
            check(
                "H 键打开键盘说明",
                cdp.eval("document.querySelector('#helpPanel').hidden") is False,
            )
            cdp.eval(
                "document.body.dispatchEvent(new KeyboardEvent('keydown', "
                "{key:'h', bubbles:true, cancelable:true}))"
            )

            cdp.eval(f"""(()=>{{
              const i=document.querySelector('#inp');
              i.value='{compact}周{weekday} 08:00 交互测试定向 #要办';
              document.querySelector('.kind[data-k="dated"]').click();
              document.querySelector('#addBtn').click();
            }})()""")
            stored = cdp.eval("JSON.parse(localStorage.getItem('triage.v2'))")
            matches = [x for x in stored["dated"] if x["text"] == "交互测试定向"]
            check("无空格日期已入库", bool(matches), json.dumps(stored, ensure_ascii=False))
            item = matches[0]
            check("无空格日期可解析", item["date"] == target_day.isoformat(), item)

            check(
                "念头使用普通静态列",
                cdp.eval("document.querySelectorAll('.idea-card').length") > 0
                and cdp.eval("document.querySelector('.pool')") is None,
            )
            before_ideas = cdp.eval(
                "JSON.parse(localStorage.getItem('triage.v2')).ideas.length"
            )
            before_todo = cdp.eval(
                "JSON.parse(localStorage.getItem('triage.v2')).todo.length"
            )
            cdp.eval(
                "document.querySelector('.idea-card [data-a=\"to\"]').click()"
            )
            after_state = cdp.eval("JSON.parse(localStorage.getItem('triage.v2'))")
            check(
                "普通念头列仍可转待办",
                len(after_state["ideas"]) == before_ideas - 1
                and len(after_state["todo"]) == before_todo + 1,
                after_state,
            )

            before = cdp.eval(
                "JSON.parse(localStorage.getItem('triage.v2')).done.length"
            )
            cdp.eval("document.querySelector('#list-todo .card .check').click()")
            time.sleep(.3)
            after = cdp.eval(
                "JSON.parse(localStorage.getItem('triage.v2')).done.length"
            )
            check("完成记录保留", after == before + 1, (before, after))
            check(
                "误勾后出现底部撤销",
                cdp.eval("document.querySelector('#undoToast').classList.contains('show')")
                is True
                and "已完成" in cdp.eval(
                    "document.querySelector('#undoMessage').textContent"
                ),
            )
            cdp.eval("document.querySelector('#undoAction').click()")
            restored = cdp.eval("JSON.parse(localStorage.getItem('triage.v2'))")
            check("误勾可以从底部撤销", len(restored["done"]) == before)

            legacy = {
                "todo": [],
                "dated": [{
                    "id": "legacy-task",
                    "text": "旧作业交稿",
                    "date": target_day.isoformat(),
                    "time": "23:59",
                    "cat": "academic",
                    "note": "",
                }],
                "ideas": [],
                "done": [],
                "mig3": True,
                "schema": 3,
            }
            cdp.eval(
                "localStorage.setItem('triage.v2', "
                + json.dumps(json.dumps(legacy, ensure_ascii=False), ensure_ascii=False)
                + "); location.reload(); true"
            )
            time.sleep(.8)
            migrated = cdp.eval("JSON.parse(localStorage.getItem('triage.v2'))")
            check(
                "旧数据自动迁移到新模型",
                any(x["id"] == "legacy-task" for x in migrated["todo"])
                and not any(x["id"] == "legacy-task" for x in migrated["dated"]),
                migrated,
            )
            print("web interactions ok")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL:", exc, file=sys.stderr)
        raise SystemExit(1)
