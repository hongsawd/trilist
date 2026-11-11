"""Real browser regression: remote sync must not replace an active date editor."""
import json,subprocess,tempfile,time,urllib.request
from pathlib import Path
from test_mobile_sync_retry import CDP,free_port,EDGE
ROOT=Path(__file__).resolve().parent

def main():
    fixture={"todo":[{"id":"task","text":"Test task","cat":"action","date":"2027-01-15","time":"09:00","where":"Test place","place":"Test place","note":"Original note","updatedAt":10}],"dated":[{"id":"event","text":"Test event","cat":"info","date":"2027-01-16","updatedAt":10}],"ideas":[],"done":[],"courses":[],"places":[],"deleted":[],"mig3":True,"mig4":True,"mig5":True,"sync":{"url":"https://example.test/sync-test","token":"test-only","lastSync":1}}
    mock='''(()=>{
      localStorage.setItem('triage.v2',FIXTURE);
      const data=JSON.parse(FIXTURE);
      const remote=new Map();
      for(const [kind,list] of [['todo',data.todo],['event',data.dated]])for(const x of list)remote.set(kind+'|'+x.id,{kind,id:x.id,updatedAt:x.updatedAt,deleted:false,payload:x});
      window.__patchRemote=(kind,id,patch,deleted=false)=>{
        const old=remote.get(kind+'|'+id);
        const row={...old,updatedAt:Date.now(),deleted,payload:deleted?null:{...old.payload,...patch}};
        remote.set(kind+'|'+id,row);
      };
      window.__requests=0;
      window.fetch=async(url,options)=>{
        if(!String(url).includes('sync-test'))return new Response(JSON.stringify({ok:true}));
        window.__requests++;
        for(const row of JSON.parse(options.body).items){const old=remote.get(row.kind+'|'+row.id);if(!old||row.updatedAt>old.updatedAt)remote.set(row.kind+'|'+row.id,row);}
        return new Response(JSON.stringify({ok:true,serverTime:Date.now(),items:[...remote.values()]}));
      };
    })();'''.replace('FIXTURE',json.dumps(json.dumps(fixture)))
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        port=free_port();proc=subprocess.Popen([str(EDGE),'--headless=new','--disable-gpu','--no-first-run',f'--remote-debugging-port={port}',f'--user-data-dir={tmp}',(ROOT/'index.html').as_uri()],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for _ in range(60):
                try:targets=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list'));break
                except Exception:time.sleep(.1)
            c=CDP(next(x for x in targets if x['type']=='page')['webSocketDebuggerUrl']);c.call('Page.enable');c.call('Runtime.enable')
            c.call('Page.addScriptToEvaluateOnNewDocument',source=mock)
            c.eval('location.reload()');time.sleep(.3)
            def wait(expr):
                for _ in range(70):
                    if c.eval(expr):return
                    time.sleep(.05)
                raise AssertionError(expr)
            wait('window.__requests>=1 && document.querySelector("#syncStatus").textContent.startsWith("已同步")')
            c.eval('document.querySelector("#list-todo [data-edit]").click()');time.sleep(.05)
            c.eval('window.__dateField=document.querySelector("#list-todo .inline-date");__dateField.focus();__dateField.value="2027-02-20";__dateField.dispatchEvent(new Event("input",{bubbles:true}));')
            for event in ['keyDown','keyUp']:c.call('Input.dispatchKeyEvent',type=event,key='ArrowUp',code='ArrowUp',windowsVirtualKeyCode=38)
            assert c.eval('window.__dateField.value')!='2027-02-20','Native date keyboard input did not work'
            for event in ['keyDown','keyUp']:c.call('Input.dispatchKeyEvent',type=event,key='ArrowDown',code='ArrowDown',windowsVirtualKeyCode=40)
            assert c.eval('window.__dateField.value')=='2027-02-20'
            c.eval('window.__patchRemote("event","event",{text:"Remote event updated"});window.dispatchEvent(new Event("focus"))')
            wait('JSON.parse(localStorage.getItem("triage.v2")).dated[0].text==="Remote event updated"')
            assert c.eval('document.querySelector("#list-todo .inline-date").value')=='2027-02-20','Date draft reset during background sync'
            assert c.eval('document.querySelector("#list-todo .inline-date")===window.__dateField'),'Date control was replaced'
            assert c.eval('document.activeElement===window.__dateField'),'Date focus was lost'
            print('ok: background sync preserves date draft, original native control and focus',flush=True)
            c.eval('window.__patchRemote("todo","task",{note:"Remote note updated"});window.dispatchEvent(new Event("focus"))')
            wait('JSON.parse(localStorage.getItem("triage.v2")).todo[0].note==="Remote note updated"')
            c.eval('document.querySelector("#list-todo .save").click()')
            wait('!document.querySelector("#list-todo .inline-editor")')
            time.sleep(2.2)
            item=c.eval('JSON.parse(localStorage.getItem("triage.v2")).todo[0]')
            assert item['date']=='2027-02-20',item
            assert item['note']=='Remote note updated',item
            print('ok: saved date survives next sync and preserves unrelated remote changes',flush=True)
            c.eval('document.querySelector("#list-todo [data-edit]").click()');time.sleep(.05)
            c.eval('const f=document.querySelector("#list-todo .inline-date");f.value="2027-03-05";f.dispatchEvent(new Event("input",{bubbles:true}));window.__patchRemote("todo","task",{date:"2027-04-06"});window.dispatchEvent(new Event("focus"))')
            wait('JSON.parse(localStorage.getItem("triage.v2")).todo[0].date==="2027-04-06"')
            assert c.eval('document.querySelector("#list-todo .inline-date").value')=='2027-03-05'
            c.eval('document.querySelector("#list-todo .cancel").click()')
            assert c.eval('JSON.parse(localStorage.getItem("triage.v2")).todo[0].date')=='2027-04-06'
            print('ok: cancel discards draft and retains current synced value',flush=True)
            c.eval('document.querySelector("#list-todo [data-edit]").click()');time.sleep(.05)
            c.eval('document.querySelector("#list-todo [data-clear=date]").click();document.querySelector("#list-todo [data-clear=where]").click();document.querySelector("#list-todo .inline-note").value="";document.querySelector("#list-todo .save").click()')
            time.sleep(2.2)
            item=c.eval('JSON.parse(localStorage.getItem("triage.v2")).todo[0]')
            assert not item.get('date') and not item.get('where') and not item.get('place') and not item.get('note'),item
            print('ok: explicit clears remain cleared after syncing',flush=True)
            c.eval('location.reload()');time.sleep(.3)
            wait('window.__requests>=1 && document.querySelector("#syncStatus").textContent.startsWith("已同步")')
            c.eval('document.querySelector("[data-view=cal]").click()')
            for _ in range(24):
                if c.eval('!!document.querySelector("[data-date=\\"2027-01-15\\"]")'):break
                c.eval('document.querySelector("#nextM").click()')
            c.eval('document.querySelector("[data-date=\\"2027-01-15\\"]").click();document.querySelector("#dayItems [data-edit]").click()');time.sleep(.05)
            c.eval('window.__calendarField=document.querySelector("#dayItems .inline-date");__calendarField.focus();__calendarField.value="2027-02-21";__calendarField.dispatchEvent(new Event("input",{bubbles:true}));window.__patchRemote("event","event",{text:"Calendar sync update"});window.dispatchEvent(new Event("focus"))')
            wait('JSON.parse(localStorage.getItem("triage.v2")).dated[0].text==="Calendar sync update"')
            assert c.eval('document.querySelector("#dayItems .inline-date")===window.__calendarField')
            assert c.eval('document.querySelector("#dayItems .inline-date").value')=='2027-02-21'
            c.eval('document.querySelector("[data-view=board]").click()')
            assert c.eval('document.querySelector("#list-todo .inline-date").value')=='2027-02-21'
            c.eval('document.querySelector("[data-view=cal]").click()')
            assert c.eval('document.querySelector("#dayItems .inline-date").value')=='2027-02-21'
            c.eval('document.querySelector("#dayItems .save").click()');time.sleep(2.2)
            assert c.eval('JSON.parse(localStorage.getItem("triage.v2")).todo[0].date')=='2027-02-21'
            print('ok: calendar date edit and draft navigation survive sync',flush=True)
            c.eval('document.querySelector("[data-view=board]").click();document.querySelector("#list-todo [data-edit]").click()');time.sleep(.05)
            c.eval('window.__patchRemote("todo","task",{},true);window.dispatchEvent(new Event("focus"))')
            wait('JSON.parse(localStorage.getItem("triage.v2")).todo.length===0')
            c.eval('document.querySelector("#list-todo .save").click()')
            assert c.eval('document.querySelector("#list-todo .inline-error").textContent')
            assert c.eval('JSON.parse(localStorage.getItem("triage.v2")).todo.length')==0
            c.eval('document.querySelector("#list-todo .cancel").click()')
            assert not c.eval('!!document.querySelector("main:not([hidden]) .inline-editor")')
            print('ok: a remote deletion preserves input and cannot be silently resurrected',flush=True)
        finally:proc.terminate();proc.wait(timeout=5)
if __name__=='__main__':main()
