"""A new desktop/mobile user can obtain, persist and copy a token from the UI."""
import json,subprocess,tempfile,time,urllib.request
from pathlib import Path
from test_mobile_sync_retry import CDP,free_port,EDGE
ROOT=Path(__file__).resolve().parent
for mobile in [False,True]:
    fixture={k:[] for k in (['todos','events','thoughts','courses','deleted'] if mobile else ['todo','dated','ideas','done','courses','deleted','places'])}
    fixture['sync']={'url':'https://example.test/api/sync','token':'','lastSync':0}
    fixture.update({'mig3':True,'mig4':True,'mig5':True})
    mock='''(()=>{
      localStorage.setItem(KEY,FIXTURE);
      window.__created=0;
      window.__token='sg_'+'a'.repeat(64);
      Object.defineProperty(navigator,'clipboard',{value:{writeText:async v=>window.__copied=v}});
      window.fetch=async(url,options)=>{
        if(String(url).endsWith('/register')){window.__created++;return new Response(JSON.stringify({ok:true,token:window.__token}),{status:201});}
        if(String(url).includes('example.test'))return new Response(JSON.stringify({ok:true,serverTime:Date.now(),items:JSON.parse(options.body).items||[]}));
        return new Response(JSON.stringify({ok:true}));
      };
    })();'''.replace('KEY',json.dumps('sange.mobile.v1' if mobile else 'triage.v2')).replace('FIXTURE',json.dumps(json.dumps(fixture)))
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        port=free_port();page=ROOT/('mobile/index.html' if mobile else 'index.html')
        proc=subprocess.Popen([str(EDGE),'--headless=new','--disable-gpu','--no-first-run',f'--remote-debugging-port={port}',f'--user-data-dir={tmp}',page.as_uri()],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for _ in range(60):
                try:targets=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list'));break
                except Exception:time.sleep(.1)
            c=CDP(next(t for t in targets if t['type']=='page')['webSocketDebuggerUrl']);c.call('Page.enable');c.call('Runtime.enable');c.call('Page.addScriptToEvaluateOnNewDocument',source=mock);c.eval('location.reload()');time.sleep(.3)
            if mobile:c.eval('document.querySelectorAll(".seg-btn")[2].click()')
            else:c.eval('document.querySelector("#syncBtn").click()')
            assert c.eval('getComputedStyle(document.querySelector("#syncGetToken")).display')!='none'
            c.eval('document.querySelector("#syncGetToken").click()')
            key='sange.mobile.v1' if mobile else 'triage.v2'
            for _ in range(60):
                if c.eval(f'JSON.parse(localStorage.getItem({json.dumps(key)})).sync.lastSync>0'):break
                time.sleep(.1)
            assert c.eval(f'JSON.parse(localStorage.getItem({json.dumps(key)})).sync.token===window.__token')
            assert c.eval(f'JSON.parse(localStorage.getItem({json.dumps(key)})).sync.lastSync>0')
            assert c.eval('window.__created')==1
            assert c.eval('getComputedStyle(document.querySelector("#syncGetToken")).display')=='none'
            c.eval('document.querySelector("#syncCopyToken").click()');time.sleep(.1)
            assert c.eval('window.__copied===window.__token')
            if mobile:
                c.eval('document.querySelector("#syncTokenToggle").click()')
                assert c.eval('!document.querySelector("#syncTokenBox").classList.contains("hidden")')
            print('ok: token creation, first sync, persistence, copy and existing-account protection', 'mobile' if mobile else 'desktop')
        finally:proc.terminate();proc.wait(timeout=5)
