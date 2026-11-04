# -*- coding: utf-8 -*-
"""首次同步安全回归测试。

使用临时浏览器配置和内存中的模拟云端，不读取或上传真实数据。
"""
import json
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket


HERE = Path(__file__).resolve().parent
PAGE = HERE / "index.html"
EDGE_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


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


def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    print("ok:", name)


def main():
    edge = next((p for p in EDGE_CANDIDATES if p.is_file()), None)
    if not edge:
        raise RuntimeError("找不到 Microsoft Edge")

    fixture = {
        "todo": [{"id": "t1", "text": "本机真实待办", "cat": "academic"}],
        "dated": [],
        "ideas": [{"id": "i1", "text": "本机念头"}],
        "done": [],
        "courses": [],
        "places": [],
        "deleted": [],
        "sync": {"token": "", "lastSync": 0},
    }
    mock_script = """
(() => {
  localStorage.setItem("triage.v2", %s);
  window.confirm = () => true;
  const initial = [
    {kind:"course", id:"c1", updatedAt:20, deleted:false,
     payload:{id:"c1",day:2,start:1,end:2,weeks:[10],name:"测试课程",place:"A",
              teacher:"",classNo:"",color:"green"}},
    {kind:"todo", id:"t1", updatedAt:20, deleted:false,
     payload:{id:"t1",text:"云端同名旧数据",cat:"action"}},
    {kind:"todo", id:"remote-only", updatedAt:20, deleted:false,
     payload:{id:"remote-only",text:"云端多余示例",cat:"info"}}
  ];
  const server = new Map(initial.map(x => [x.kind + "|" + x.id, x]));
  window.__syncRequests = [];
  window.fetch = async (_url, options) => {
    const body = JSON.parse((options && options.body) || "{}");
    window.__syncRequests.push(body);
    for (const item of (body.items || [])) {
      const key = item.kind + "|" + item.id;
      const old = server.get(key);
      if (!old || item.updatedAt > old.updatedAt) server.set(key, item);
    }
    return new Response(JSON.stringify({
      ok:true, serverTime:Date.now(), items:Array.from(server.values())
    }), {status:200, headers:{"content-type":"application/json"}});
  };
})();
""" % json.dumps(json.dumps(fixture, ensure_ascii=False), ensure_ascii=False)

    with tempfile.TemporaryDirectory(prefix="triage-sync-test-", ignore_cleanup_errors=True) as tmp:
        port = free_port()
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if hasattr(subprocess, "CREATE_NO_WINDOW") else {}
        proc = subprocess.Popen(
            [
                str(edge), "--headless=new", "--disable-gpu", "--no-first-run",
                f"--remote-debugging-port={port}", f"--user-data-dir={tmp}",
                PAGE.as_uri(),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
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
            cdp.call("Page.addScriptToEvaluateOnNewDocument", source=mock_script)
            cdp.eval("location.reload()")
            time.sleep(0.8)

            cdp.eval("document.querySelector('#syncBtn').click()")
            cdp.eval("document.querySelector('#syncToken').value='test-token'")
            cdp.eval("document.querySelector('#syncRun').click()")
            first_guard = ""
            for _ in range(10):
                first_guard = cdp.eval("document.querySelector('#syncStatus').textContent")
                if first_guard:
                    break
                time.sleep(0.1)
            check("首次同步前拦截普通合并",
                  "首次同步" in first_guard, first_guard)
            cdp.eval("document.querySelector('#syncFirst').click()")

            status = ""
            for _ in range(80):
                status = cdp.eval("document.querySelector('#syncStatus').textContent")
                if status.startswith("已同步") or status.startswith("同步失败"):
                    break
                time.sleep(0.1)
            check("首次同步成功", status.startswith("已同步"), status)

            requests = cdp.eval("window.__syncRequests")
            pushes = [request for request in requests if request.get("items")]
            check("首次同步先拉后推", bool(requests) and bool(pushes), requests)
            pushed = pushes[0]["items"]
            local_todo = next(x for x in pushed if x["kind"] == "todo" and x["id"] == "t1")
            remote_delete = next(x for x in pushed if x["kind"] == "todo" and x["id"] == "remote-only")
            check("本机同名条目时间戳被抬高", local_todo["updatedAt"] > 20, local_todo)
            check("云端多余条目被墓碑删除", remote_delete["deleted"] is True, remote_delete)

            stored = cdp.eval("JSON.parse(localStorage.getItem('triage.v2'))")
            check("本机待办未被云端同名示例覆盖",
                  stored["todo"][0]["text"] == "本机真实待办", stored["todo"])
            check("课程从云端拉入",
                  any(c["id"] == "c1" for c in stored["courses"]), stored["courses"])
            check("同步前备份存在",
                  bool(cdp.eval("localStorage.getItem('triage.presync.backup')")))
            print("sync safety ok")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
