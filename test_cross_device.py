"""Desktop and mobile integrate with the actual Worker handler over local HTTP."""
import json,subprocess,tempfile,time,urllib.request
from pathlib import Path
from test_mobile_sync_retry import CDP,free_port,EDGE
ROOT=Path(__file__).resolve().parent

def main():
    service_port=free_port();processes=[];dirs=[]
    flags={'creationflags':subprocess.CREATE_NO_WINDOW}
    try:
        processes.append(subprocess.Popen(['node',str(ROOT/'test_sync_server.mjs'),str(service_port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**flags))
        sync={'url':f'http://127.0.0.1:{service_port}/api/sync','token':'integration-only','lastSync':1}
        clients=[]
        for mobile in [False,True]:
            tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);dirs.append(tmp);port=free_port()
            page=ROOT/('mobile/index.html' if mobile else 'index.html')
            processes.append(subprocess.Popen([str(EDGE),'--headless=new','--disable-gpu','--no-first-run',f'--remote-debugging-port={port}',f'--user-data-dir={tmp.name}',page.as_uri()],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**flags))
            for _ in range(60):
                try:
                    targets=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list'));break
                except Exception:time.sleep(.1)
            c=CDP(next(x for x in targets if x['type']=='page')['webSocketDebuggerUrl']);clients.append(c)
            c.call('Page.enable');c.call('Runtime.enable')
            fixture={k:[] for k in (['todos','events','thoughts','courses','deleted'] if mobile else ['todo','dated','ideas','done','courses','places','deleted'])};fixture['sync']=sync
            c.call('Page.addScriptToEvaluateOnNewDocument',source='window.__errors=[];window.addEventListener("error",e=>window.__errors.push(e.message));localStorage.setItem('+json.dumps('sange.mobile.v1' if mobile else 'triage.v2')+','+json.dumps(json.dumps(fixture))+');')
            c.eval('location.reload()')
        desktop,mobile=clients
        time.sleep(1.8)
        assert not desktop.eval('window.__errors'),desktop.eval('window.__errors')
        def wait(c,expr):
            start=time.monotonic()
            while time.monotonic()-start<7:
                if c.eval(expr):return round(time.monotonic()-start,2)
                time.sleep(.05)
            raise AssertionError(expr+'; mobile='+str(mobile.eval('document.querySelector("#syncStatus").textContent'))+'; desktop='+str(desktop.eval('JSON.stringify({status:document.querySelector("#syncStatus").textContent,data:JSON.parse(localStorage.getItem("triage.v2"))})')))
        desktop.eval('document.querySelector("#inp").value="Integration task #urgent";document.querySelector("[data-k=todo]").click();document.querySelector("#addBtn").click()')
        delay=wait(mobile,'document.querySelector("#todoList").textContent.includes("Integration task")')
        print('ok: desktop -> mobile automatic sync:',delay,'seconds')
        mobile.eval('document.querySelector("#todoList [data-done]").click()')
        delay=wait(desktop,'JSON.parse(localStorage.getItem("triage.v2")).done.some(x=>x.text.includes("Integration task"))')
        print('ok: mobile completion -> desktop history:',delay,'seconds')
        assert 'undefined' not in desktop.eval('document.body.innerText')
        mobile.eval('document.querySelector("#capture").click();document.querySelector("#sheetInput").value="Integration thought";document.querySelector("#submitBtn").click()')
        delay=wait(desktop,'JSON.parse(localStorage.getItem("triage.v2")).ideas.some(x=>x.text==="Integration thought")')
        print('ok: mobile -> desktop automatic sync:',delay,'seconds')
        # Delete the done task from mobile, verify desktop cannot revive it.
        mobile.eval('document.querySelector("#todoList [data-delete-todo]").click()')
        wait(desktop,'JSON.parse(localStorage.getItem("triage.v2")).done.length===0')
        time.sleep(2.5)
        assert mobile.eval('JSON.parse(localStorage.getItem("sange.mobile.v1")).todos.length===0')
        print('ok: deletion propagates and remains deleted after another polling cycle')
    finally:
        for p in reversed(processes):p.terminate()
        for p in processes:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill()
        for d in dirs:d.cleanup()
if __name__=='__main__':main()
