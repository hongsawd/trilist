"use strict";

const {
  app, BrowserWindow, globalShortcut, ipcMain, Menu,
  nativeImage, screen, Tray
} = require("electron");
const fs = require("node:fs");
const path = require("node:path");
const {leadMinutes,isDue}=require("./reminder-rules");

const HOTKEY = "Control+Alt+Space";
const QUICK_HOTKEY = "Control+Alt+Q";
const QUICK_HOTKEY_FALLBACKS = ["Control+Alt+S", "Control+Shift+Space", "Alt+Shift+S"];
const INDEX_FILE = path.join(__dirname, "..", "index.html");
const PRELOAD_FILE = path.join(__dirname, "preload.js");
const NOTIFICATION_FILE = path.join(__dirname, "notification.html");
const SEED_FILE = path.join(__dirname, "seed-data.json");
const ICON_FILE = path.join(__dirname, "icon.png");
const QUICK_WIDTH = 410;
const QUICK_HEIGHT = 790;
const AUTOSTART = process.argv.includes("--autostart");
app.setPath("userData", path.join(__dirname, "profile"));

let panel = null;
let quickWindow = null;
let tray = null;
let notificationWindow = null;
let notificationTimer = null;
let reminders = [];
let notified = new Set();
let quitting = false;
let bootstrapped = false;
let animationTimer = null;
let quickHotkey = "";

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", (_event, argv) => {
    if (!argv.includes("--autostart")) showPanel();
  });
  app.whenReady().then(start);
}

function start() {
  app.setName("三格");
  app.setAppUserModelId("com.sange.desktop");
  Menu.setApplicationMenu(null);
  loadNotified();
  let seedText = "";
  try { seedText = fs.readFileSync(SEED_FILE, "utf8"); } catch {}
  ipcMain.on("desktop:initial-seed", event => {
    event.returnValue = seedText;
  });
  createPanel();
  createTray();
  const registered = globalShortcut.register(HOTKEY, togglePanel);
  if (!registered) {
    showError("全局快捷键注册失败：Ctrl+Alt+Space 可能已被其他程序占用。");
  }
  for (const shortcut of [QUICK_HOTKEY, ...QUICK_HOTKEY_FALLBACKS]) {
    if (globalShortcut.register(shortcut, toggleQuick)) {
      quickHotkey = shortcut.replace("Control", "Ctrl");
      writeLog("quick-view shortcut: " + quickHotkey);
      break;
    }
  }
  if (!quickHotkey) writeLog("quick-view global shortcut registration failed");
  setInterval(checkReminders, 10_000);
}

function createPanel() {
  panel = new BrowserWindow({
    show: false,
    frame: false,
    transparent: false,
    resizable: true,
    movable: true,
    minimizable: false,
    maximizable: false,
    skipTaskbar: true,
    backgroundColor: "#f6f7f9",
    title: "三格",
    icon: ICON_FILE,
    webPreferences: {
      preload: PRELOAD_FILE,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      spellcheck: false
    }
  });
  panel.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  panel.on("close", event => {
    if (!quitting) {
      event.preventDefault();
      hidePanel();
    }
  });
  panel.webContents.on("did-finish-load", async () => {
    if (!bootstrapped) {
      bootstrapped = true;
      try {
        const exists = await panel.webContents.executeJavaScript(
          "Boolean(localStorage.getItem('triage.v2'))"
        );
        if (!exists && fs.existsSync(SEED_FILE)) {
          const seed = fs.readFileSync(SEED_FILE, "utf8");
          await panel.webContents.executeJavaScript(
            `localStorage.setItem('triage.v2', ${JSON.stringify(seed)}); true`
          );
          panel.reload();
          return;
        }
      } catch (error) {
        writeLog("bootstrap failed: " + error.stack);
      }
    }
    if (!AUTOSTART) showPanel();
  });
  panel.loadFile(INDEX_FILE);
}

function workArea() {
  const point = screen.getCursorScreenPoint();
  return screen.getDisplayNearestPoint(point).workArea;
}

function panelBounds() {
  const area = workArea();
  const width = Math.max(900, Math.min(1180, area.width - 28));
  const height = Math.max(620, area.height - 28);
  return {
    width,
    height,
    x: area.x + area.width - width - 14,
    y: area.y + 14,
    offX: area.x + area.width + 8
  };
}

function showPanel() {
  if (!panel || panel.isDestroyed()) return;
  if (quickWindow && !quickWindow.isDestroyed()) quickWindow.hide();
  clearInterval(animationTimer);
  const b = panelBounds();
  panel.setBounds({ x: b.offX, y: b.y, width: b.width, height: b.height });
  panel.show();
  panel.moveTop();
  panel.focus();
  panel.webContents.focus();
  animateX(b.offX, b.x);
}

function hidePanel() {
  if (!panel || panel.isDestroyed() || !panel.isVisible()) return;
  clearInterval(animationTimer);
  const b = panelBounds();
  animateX(panel.getBounds().x, b.offX, () => panel.hide());
}

function togglePanel() {
  if (!panel || panel.isDestroyed()) return;
  panel.isVisible() ? hidePanel() : showPanel();
}

function animateX(from, to, done) {
  clearInterval(animationTimer);
  const started = Date.now();
  const duration = 170;
  animationTimer = setInterval(() => {
    if (!panel || panel.isDestroyed()) {
      clearInterval(animationTimer);
      return;
    }
    const t = Math.min(1, (Date.now() - started) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    const y = panel.getBounds().y;
    panel.setPosition(Math.round(from + (to - from) * eased), y);
    if (t >= 1) {
      clearInterval(animationTimer);
      if (done) done();
    }
  }, 16);
}

function createTray() {
  const image = nativeImage.createFromPath(ICON_FILE);
  tray = new Tray(image.resize({ width: 24, height: 24 }));
  tray.setToolTip("三格 · Ctrl+Alt+Space");
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "打开 / 收起三格  Ctrl+Alt+Space", click: togglePanel },
    { label: `只打开近期安排  ${quickHotkey || "（快捷键不可用）"}`, click: toggleQuick },
    { type: "separator" },
    { label: "退出", click: () => quitApp() }
  ]));
  tray.on("click", togglePanel);
}

function sanitizeReminder(item) {
  const when = new Date(item?.startAt || "");
  if (!item?.title || Number.isNaN(when.getTime())) return null;
  return {
    id: String(item.id || `${item.title}:${item.startAt}`).slice(0, 240),
    title: String(item.title).slice(0, 300),
    startAt: when.toISOString(),
    where: String(item.where || "").slice(0, 300),
    kind: String(item.kind || "日程").slice(0, 30),
    remindBefore:leadMinutes(item.remindBefore)
  };
}

ipcMain.handle("reminders:sync", (_event, items) => {
  reminders = (Array.isArray(items) ? items : []).map(sanitizeReminder).filter(Boolean);
  if (!reminders.length && notificationWindow && !notificationWindow.isDestroyed()) notificationWindow.close();
  const active = new Set(reminders.map(x => reminderKey(x)));
  for (const key of notified) if (!active.has(key)) notified.delete(key);
  saveNotified();
  try {
    fs.writeFileSync(
      path.join(app.getPath("userData"), "reminders.json"),
      JSON.stringify(reminders, null, 2),
      "utf8"
    );
  } catch (error) {
    writeLog("reminder snapshot save failed: " + error.stack);
  }
  checkReminders();
  return { ok: true, items: reminders.length };
});

ipcMain.on("panel:hide", hidePanel);
ipcMain.on("panel:toggle", togglePanel);
ipcMain.on("quick:open", openQuick);
ipcMain.on("quick:close", () => {
  if (quickWindow && !quickWindow.isDestroyed()) quickWindow.close();
});

function openQuick() {
  if (quickWindow && !quickWindow.isDestroyed()) {
    if (panel && panel.isVisible()) panel.hide();
    quickWindow.setAlwaysOnTop(true, "screen-saver");
    quickWindow.show();
    quickWindow.moveTop();
    quickWindow.focus();
    return;
  }
  if (panel && panel.isVisible()) panel.hide();
  const area = workArea();
  const width = Math.min(QUICK_WIDTH, area.width-28);
  const height = Math.min(QUICK_HEIGHT, area.height-34);
  quickWindow = new BrowserWindow({
    width, height,
    x: area.x+area.width-width-16,
    y: area.y+16,
    show:false,
    frame:false,
    resizable:false,
    skipTaskbar:true,
    alwaysOnTop:true,
    backgroundColor:"#f6f7f9",
    title:"三格 · 接下来",
    webPreferences:{
      preload:PRELOAD_FILE,
      contextIsolation:true,
      nodeIntegration:false,
      sandbox:false,
      spellcheck:false
    }
  });
  quickWindow.setAlwaysOnTop(true, "screen-saver");
  quickWindow.once("ready-to-show", () => {
    quickWindow.show();
    quickWindow.moveTop();
    quickWindow.focus();
  });
  quickWindow.webContents.setWindowOpenHandler(() => ({action:"deny"}));
  quickWindow.on("closed", () => { quickWindow = null; });
  quickWindow.loadFile(INDEX_FILE, {query:{peek:"1"}});
}

function toggleQuick() {
  if (quickWindow && !quickWindow.isDestroyed() && quickWindow.isVisible()) {
    quickWindow.hide();
  } else {
    openQuick();
  }
}

function reminderKey(item) {
  return item.id + "|" + item.startAt;
}

function checkReminders() {
  const now = Date.now();
  const due = [];
  for (const item of reminders) {
    const start = new Date(item.startAt).getTime();
    const key = reminderKey(item);
    if (isDue(item,now) && !notified.has(key)) {
      notified.add(key);
      due.push(item);
    }
  }
  if (due.length) {
    saveNotified();
    showNotification(due);
  }
}

function showNotification(items) {
  if (notificationWindow && !notificationWindow.isDestroyed()) {
    notificationWindow.close();
  }
  clearTimeout(notificationTimer);
  const area = workArea();
  const width = Math.min(540, area.width-24);
  const height = Math.min(430, 210 + items.slice(0,3).length*74);
  notificationWindow = new BrowserWindow({
    width, height,
    x: area.x+area.width-width-16,
    y: area.y+18,
    frame: false,
    transparent: true,
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    focusable: true,
    hasShadow: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });
  notificationWindow.setAlwaysOnTop(true, "screen-saver");
  notificationWindow.webContents.once("did-finish-load", () => {
    const payload = JSON.stringify(items.slice(0,3));
    notificationWindow.webContents.executeJavaScript(
      `renderNotifications(${payload}, ${JSON.stringify(HOTKEY)})`
    );
    notificationWindow.show();
    notificationWindow.moveTop();
    notificationWindow.focus();
  });
  notificationWindow.on("closed", () => {
    notificationWindow = null;
    clearTimeout(notificationTimer);
  });
  notificationWindow.loadFile(NOTIFICATION_FILE);
  notificationTimer = setTimeout(() => {
    if (notificationWindow && !notificationWindow.isDestroyed()) notificationWindow.close();
  }, 60_000);
}

function notifiedFile() {
  return path.join(app.getPath("userData"), "notified.json");
}

function loadNotified() {
  try {
    const data = JSON.parse(fs.readFileSync(notifiedFile(), "utf8"));
    notified = new Set(Array.isArray(data) ? data : []);
  } catch {
    notified = new Set();
  }
}

function saveNotified() {
  try {
    fs.mkdirSync(path.dirname(notifiedFile()), { recursive: true });
    fs.writeFileSync(notifiedFile(), JSON.stringify([...notified]), "utf8");
  } catch (error) {
    writeLog("notified save failed: " + error.stack);
  }
}

function writeLog(text) {
  try {
    fs.appendFileSync(
      path.join(app.getPath("userData"), "desktop.log"),
      `[${new Date().toISOString()}] ${text}\n`
    );
  } catch {}
}

function showError(message) {
  if (!panel || panel.isDestroyed()) return;
  panel.webContents.executeJavaScript(
    `document.getElementById('note').textContent=${JSON.stringify(message)}`
  );
}

function quitApp() {
  quitting = true;
  app.quit();
}

app.on("before-quit", () => { quitting = true; });
app.on("will-quit", () => globalShortcut.unregisterAll());
app.on("window-all-closed", () => {});
