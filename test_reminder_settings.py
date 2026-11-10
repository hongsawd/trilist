"""Reminder settings persist; custom and off modes reach the desktop bridge."""
import json,subprocess,tempfile,time,urllib.request
from pathlib import Path
from test_mobile_sync_retry import CDP,free_port,EDGE
ROOT=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    port=free_port()
    proc=subprocess.Popen([str(EDGE),'--headless=new','--disable-gpu','--no-first-run',f'--remote-debugging-port={port}',f'--user-data-dir={tmp}',(ROOT/'index.html').as_uri()+'?demo=1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        for _ in range(60):
            try:targets=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list'));break
            except Exception:time.sleep(.1)
        c=CDP(next(x for x in targets if x['type']=='page')['webSocketDebuggerUrl']);c.call('Page.enable');c.call('Runtime.enable')
        c.call('Page.addScriptToEvaluateOnNewDocument',source='window.sanGeDesktop={syncReminders:async items=>{window.__reminders=items;return {ok:true}},hidePanel(){}}')
        c.eval('location.reload()');time.sleep(.5)
        c.eval('document.querySelector("#settingsBtn").click()')
        assert c.eval('getComputedStyle(document.querySelector("#reminderCustomWrap")).display')=='none'
        c.eval('document.querySelector("#settingsCancel").click()')
        c.eval('document.querySelector("#settingsBtn").click();document.querySelector("#reminderMode").value="off";document.querySelector("#settingsSave").click()');time.sleep(.1)
        assert c.eval('window.__reminders.length')==0
        c.eval('location.reload()');time.sleep(.5)
        assert c.eval('JSON.parse(localStorage.getItem("triage.v2")).settings.reminderMinutes') is None
        c.eval('document.querySelector("#settingsBtn").click();document.querySelector("#reminderMode").value="custom";document.querySelector("#reminderMode").dispatchEvent(new Event("change"));document.querySelector("#reminderCustom").value="-5";document.querySelector("#settingsSave").click()')
        assert c.eval('document.querySelector("#settingsDialog").open') is True
        assert c.eval('document.querySelector("#reminderError").textContent')
        c.eval('document.querySelector("#reminderCustom").value="7";document.querySelector("#settingsSave").click()');time.sleep(.1)
        assert c.eval('JSON.parse(localStorage.getItem("triage.v2")).settings.reminderMinutes')==7
        assert c.eval('window.__reminders.every(x=>x.remindBefore===7)') is True
        c.eval('document.querySelector("#settingsBtn").click();document.querySelector("#reminderMode").value="30";document.querySelector("#settingsSave").click()')
        assert c.eval('JSON.parse(localStorage.getItem("triage.v2")).settings.reminderMinutes')==30
        print('ok: reminder off, persistence, invalid input, custom minutes and default 30 minutes')
    finally:proc.terminate();proc.wait(timeout=5)
