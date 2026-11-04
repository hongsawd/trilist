# -*- coding: utf-8 -*-
"""手机端同步期间继续编辑后的自动补同步测试。"""
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
        out = self.call(
            "Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True
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
    if not EDGE.is_file():
        raise RuntimeError("找不到 Microsoft Edge")
    store = {
        "todos": [], "events": [], "courses": [], "thoughts": [], "deleted": [],
        "sync": {"url": "https://example.test/api/sync", "token": "test-token", "lastSync": 20}
    }
    mock = """
(() => {
  localStorage.setItem("sange.mobile.v1", %s);
  window.__requests = 0;
  window.__release = [];
  const server = new Map();
  window.fetch = async (_url, options) => {
    window.__requests++;
    const body = JSON.parse((options && options.body) || "{}");
    for (const item of (body.items || [])) {
      const key = item.kind + "|" + item.id;
      const old = server.get(key);
      if (!old || item.updatedAt > old.updatedAt) server.set(key, item);
    }
    return await new Promise(resolve => {
      window.__release.push(() => resolve(new Response(
        JSON.stringify({ok:true,serverTime:Date.now(),items:Array.from(server.values())}),
        {status:200,headers:{"content-type":"application/json"}}
      )));
    });
  };
})();
""" % json.dumps(json.dumps(store, ensure_ascii=False), ensure_ascii=False)

    with tempfile.TemporaryDirectory(prefix="sange-sync-retry-", ignore_cleanup_errors=True) as tmp:
        port = free_port()
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if hasattr(subprocess, "CREATE_NO_WINDOW") else {}
        proc = subprocess.Popen(
            [
                str(EDGE), "--headless=new", "--disable-gpu", "--no-first-run",
                f"--remote-debugging-port={port}", f"--user-data-dir={tmp}", PAGE.as_uri(),
            ],
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
            cdp.call("Page.addScriptToEvaluateOnNewDocument", source=mock)
            cdp.eval("location.reload()")

            for _ in range(40):
                if cdp.eval("window.__requests") == 1:
                    break
                time.sleep(0.1)
            check("启动同步请求已发出", cdp.eval("window.__requests") == 1)

            cdp.eval("document.querySelector('#capture').click()")
            time.sleep(0.2)
            cdp.eval("document.querySelector('.type[data-type=\"todo\"]').click()")
            cdp.eval("document.querySelector('#sheetInput').value='同步期间新增'")
            cdp.eval("document.querySelector('#submitBtn').click()")
            time.sleep(0.2)
            check("同步期间可继续编辑", any(
                x.get("text") == "同步期间新增"
                for x in cdp.eval("JSON.parse(localStorage.getItem('sange.mobile.v1')).todos")
            ))

            cdp.eval("window.__release.shift()()")
            for _ in range(60):
                if cdp.eval("window.__requests") == 2:
                    break
                time.sleep(0.1)
            check("完成后自动补一轮同步", cdp.eval("window.__requests") == 2)
            cdp.eval("window.__release.shift()()")
            time.sleep(0.3)
            check("补同步后数据仍在", any(
                x.get("text") == "同步期间新增"
                for x in cdp.eval("JSON.parse(localStorage.getItem('sange.mobile.v1')).todos")
            ))
            print("mobile sync retry ok")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
