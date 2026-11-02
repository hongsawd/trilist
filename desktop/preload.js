const { contextBridge, ipcRenderer } = require("electron");

try {
  const seed = ipcRenderer.sendSync("desktop:initial-seed");
  if (seed && !localStorage.getItem("triage.v2")) {
    localStorage.setItem("triage.v2", seed);
  }
} catch {}

contextBridge.exposeInMainWorld("sanGeDesktop", {
  syncReminders: items => ipcRenderer.invoke("reminders:sync", items),
  hidePanel: () => ipcRenderer.send("panel:hide"),
  togglePanel: () => ipcRenderer.send("panel:toggle"),
  openQuick: () => ipcRenderer.send("quick:open"),
  closeQuick: () => ipcRenderer.send("quick:close"),
  globalShortcut: "Ctrl+Alt+Space",
  quickShortcut: "Ctrl+Alt+Q"
});
