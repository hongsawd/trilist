# -*- coding: utf-8 -*-
"""手机端待办、日程、念头编辑与撤销删除回归测试。"""
import json
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket


HERE = Path(__file__).resolve().parent
PAGE = HERE / "mobile" / "index.html"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=10, suppress_origin=True)
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
        out = self.call("Runtime.evaluate", expression=expression, returnByValue=True)
        result = out["result"]
        if result.get("subtype") == "error":
            raise RuntimeError(result.get("description"))
        return result.get("value")


def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    print("ok:", name)


def main():
    store = {
        "todos": [{"id": "t1", "text": "旧待办", "tag": "要办", "tone": "amber",
                   "meta": "", "done": False, "updatedAt": 1}],
        "events": [{"id": "e1", "date": "2026-11-04", "time": "09:00",
                    "endDate": "", "endTime": "", "text": "旧日程", "place": "旧地点",
                    "kind": "日程", "tone": "pink", "done": False, "updatedAt": 1}],
        "courses": [],
        "thoughts": [{"id": "i1", "text": "旧念头", "updatedAt": 1}],
        "deleted": [],
        "sync": {"url": "", "token": "", "lastSync": 0},
    }
    setup = """
(() => {
  localStorage.setItem("sange.mobile.v1", %s);
})();
""" % json.dumps(json.dumps(store, ensure_ascii=False), ensure_ascii=False)

    with tempfile.TemporaryDirectory(prefix="sange-edit-test-", ignore_cleanup_errors=True) as tmp:
        port = free_port()
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if hasattr(subprocess, "CREATE_NO_WINDOW") else {}
        proc = subprocess.Popen(
            [str(EDGE), "--headless=new", "--disable-gpu", "--no-first-run",
             f"--remote-debugging-port={port}", f"--user-data-dir={tmp}", PAGE.as_uri()],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs,
        )
        try:
            targets = None
            for _ in range(60):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as response:
                        targets = json.load(response)
                    if targets:
                        break
                except Exception:
                    time.sleep(0.1)
            check("浏览器已连接", bool(targets))
            page = next(t for t in targets if t.get("type") == "page")
            cdp = CDP(page["webSocketDebuggerUrl"])
            cdp.call("Runtime.enable")
            cdp.call("Page.enable")
            cdp.call("Page.addScriptToEvaluateOnNewDocument", source=setup)
            cdp.eval("location.reload()")
            time.sleep(0.7)

            cdp.eval("document.querySelector('[data-edit-todo]').click()")
            time.sleep(0.2)
            cdp.eval("document.querySelector('#editText').value='新待办'")
            cdp.eval("document.querySelector('#editCategory').value='学业'")
            cdp.eval("document.querySelector('#editDate').value='2026-11-05'")
            cdp.eval("document.querySelector('#editTime').value='14:30'")
            cdp.eval("document.querySelector('#editPlace').value='图书馆'")
            cdp.eval("document.querySelector('#editNote').value='带电脑'")
            cdp.eval("document.querySelector('#editSave').click()")
            time.sleep(0.2)
            todo = cdp.eval("JSON.parse(localStorage.getItem('sange.mobile.v1')).todos[0]")
            check("待办编辑保存", todo["text"] == "新待办" and todo["tag"] == "学业" and
                  todo["date"] == "2026-11-05" and todo["place"] == "图书馆", todo)

            cdp.eval("document.querySelector('[data-delete-todo]').click()")
            time.sleep(0.15)
            check("待办删除", cdp.eval("JSON.parse(localStorage.getItem('sange.mobile.v1')).todos.length") == 0)
            check("删除撤销入口", cdp.eval("!document.querySelector('#toastAction').hidden"))
            cdp.eval("document.querySelector('#toastAction').click()")
            time.sleep(0.2)
            check("待办撤销恢复", cdp.eval("JSON.parse(localStorage.getItem('sange.mobile.v1')).todos.length") == 1)

            cdp.eval("document.querySelector('[data-edit-event]').click()")
            time.sleep(0.2)
            cdp.eval("document.querySelector('#editText').value='新日程'")
            cdp.eval("document.querySelector('#editEndDate').value='2026-11-06'")
            cdp.eval("document.querySelector('#editEndTime').value='18:00'")
            cdp.eval("document.querySelector('#editPlace').value='报告厅'")
            cdp.eval("document.querySelector('#editKind').value='会议'")
            cdp.eval("document.querySelector('#editSave').click()")
            time.sleep(0.2)
            event = cdp.eval("JSON.parse(localStorage.getItem('sange.mobile.v1')).events[0]")
            check("日程编辑保存", event["text"] == "新日程" and event["endDate"] == "2026-11-06" and
                  event["endTime"] == "18:00" and event["place"] == "报告厅", event)

            cdp.eval("document.querySelector('[data-page=\"2\"]').click()")
            time.sleep(0.25)
            cdp.eval("document.querySelector('#allThoughts').click()")
            time.sleep(0.2)
            cdp.eval("document.querySelector('[data-edit-thought]').click()")
            time.sleep(0.2)
            cdp.eval("document.querySelector('#editText').value='新念头'")
            cdp.eval("document.querySelector('#editSave').click()")
            time.sleep(0.2)
            check("念头编辑保存", cdp.eval(
                "JSON.parse(localStorage.getItem('sange.mobile.v1')).thoughts[0].text") == "新念头")
            cdp.eval("document.querySelector('#allThoughts').click()")
            time.sleep(0.2)
            cdp.eval("document.querySelector('[data-delete-thought]').click()")
            time.sleep(0.15)
            check("念头删除", cdp.eval("JSON.parse(localStorage.getItem('sange.mobile.v1')).thoughts.length") == 0)
            cdp.eval("document.querySelector('#toastAction').click()")
            time.sleep(0.2)
            check("念头撤销恢复", cdp.eval("JSON.parse(localStorage.getItem('sange.mobile.v1')).thoughts.length") == 1)
            print("mobile edit/delete ok")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
