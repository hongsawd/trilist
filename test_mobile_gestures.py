import json,sys,subprocess,tempfile,time,urllib.request
from pathlib import Path
r=Path(__file__).resolve().parent
from test_mobile_sync_retry import CDP,free_port,EDGE
fixture={'todos':[{'id':f't{i}','text':f'Example task {i}','cat':'action','updatedAt':1} for i in range(25)],'events':[{'id':f'e{i}','text':f'Example event {i}','date':'2027-01-20','time':'12:00','updatedAt':1} for i in range(25)],'thoughts':[],'courses':[],'deleted':[],'sync':{'url':'','token':'','lastSync':0}}
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 port=free_port();proc=subprocess.Popen([str(EDGE),'--headless=new','--disable-gpu','--no-first-run',f'--remote-debugging-port={port}',f'--user-data-dir={tmp}',(r/'mobile/index.html').as_uri()],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
 try:
  for i in range(60):
   try:
    targets=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list'));break
   except Exception:time.sleep(.1)
  c=CDP(next(x for x in targets if x['type']=='page')['webSocketDebuggerUrl'])
  c.call('Page.enable');c.call('Runtime.enable')
  c.call('Emulation.setDeviceMetricsOverride',width=390,height=844,deviceScaleFactor=1,mobile=True)
  c.call('Emulation.setTouchEmulationEnabled',enabled=True,maxTouchPoints=1)
  c.call('Page.addScriptToEvaluateOnNewDocument',source='localStorage.setItem("sange.mobile.v1",'+json.dumps(json.dumps(fixture))+');')
  c.eval('location.reload()');time.sleep(.5)
  def drag(x,y,dx,dy):
   c.call('Input.dispatchTouchEvent',type='touchStart',touchPoints=[{'x':x,'y':y}])
   for i in range(1,13):
    c.call('Input.dispatchTouchEvent',type='touchMove',touchPoints=[{'x':x+dx*i/12,'y':y+dy*i/12}]);time.sleep(.018)
   c.call('Input.dispatchTouchEvent',type='touchEnd',touchPoints=[]);time.sleep(.35)
  for selector in ['#todoList','#eventList']:
   c.eval(f'document.querySelector({json.dumps(selector)}).scrollIntoView({{block:"center"}})');time.sleep(.2)
   box=c.eval(f'(()=>{{const e=document.querySelector({json.dumps(selector)}),b=e.getBoundingClientRect();return {{x:b.x+b.width*.7,y:Math.min(700,b.bottom-30),h:b.height,overflow:e.scrollHeight>e.clientHeight}}}})()')
   assert box['overflow'],(box,c.eval('JSON.stringify({count:document.querySelectorAll("#todoList .item").length,text:document.body.innerText.slice(-800),stored:JSON.parse(localStorage.getItem("sange.mobile.v1")).todos.length})'))
   drag(box['x'],box['y'],0,-170)
   top=c.eval(f'document.querySelector({json.dumps(selector)}).scrollTop')
   assert top>30,(selector,top,box)
   print('ok: native vertical scroll',selector,round(top))
  c.eval('window.scrollTo(0,0)');time.sleep(.15)
  drag(330,210,-230,0)
  assert c.eval('document.querySelector(".seg-btn.on").dataset.page')=='2'
  drag(330,210,-230,0)
  assert c.eval('document.querySelector(".seg-btn.on").dataset.page')=='3'
  drag(30,150,260,0)
  assert c.eval('document.querySelector(".seg-btn.on").dataset.page')=='2'
  print('ok: touch page rail, settings return gesture')
  # Course area uses its own horizontal rail.
  c.eval('document.querySelector("#ttViewport").scrollIntoView({block:"center"})');time.sleep(.15)
  before=c.eval('document.querySelector("#weekPill").textContent')
  box=c.eval('(()=>{const b=document.querySelector("#ttViewport").getBoundingClientRect();return {x:b.right-40,y:Math.max(140,b.top+80)}})()')
  drag(box['x'],box['y'],-210,0)
  assert c.eval('document.querySelector("#weekPill").textContent')!=before
  assert c.eval('document.querySelector(".seg-btn.on").dataset.page')=='2'
  print('ok: course week gesture does not change pages')
  c.call('Emulation.setDeviceMetricsOverride',width=375,height=812,deviceScaleFactor=1,mobile=True)
  c.call('Emulation.setEmulatedMedia',features=[{'name':'prefers-reduced-motion','value':'reduce'}])
  assert c.eval('document.documentElement.scrollWidth<=window.innerWidth')
  c.call('Emulation.setDeviceMetricsOverride',width=844,height=390,deviceScaleFactor=1,mobile=True)
  assert c.eval('document.documentElement.scrollWidth<=window.innerWidth')
  print('ok: small screen, landscape and reduced motion')
  shot=c.call('Page.captureScreenshot',format='png')
  import base64
  # Screenshots remain in the temporary browser session unless explicitly exported.
 finally:proc.terminate();proc.wait(timeout=5)
