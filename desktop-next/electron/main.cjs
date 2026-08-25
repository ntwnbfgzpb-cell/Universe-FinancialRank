const { app, BrowserWindow, shell } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const path = require("path");

let backendProcess;
let mainWindow;

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) app.quit();

function backendHealthy() {
  return new Promise((resolve) => {
    const request = http.get("http://127.0.0.1:8765/api/v1/health", { timeout: 500 }, (response) => {
      response.resume();
      resolve(response.statusCode === 200);
    });
    request.on("timeout", () => { request.destroy(); resolve(false); });
    request.on("error", () => resolve(false));
  });
}

async function waitForBackend(timeoutMs = 10000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (await backendHealthy()) return true;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  return false;
}

function startBackend() {
  const executable =
    process.platform === "win32" ? "rank-local-api.exe" : "rank-local-api";
  const backendPath = app.isPackaged
    ? path.join(process.resourcesPath, "backend", executable)
    : null;
  if (!backendPath || !fs.existsSync(backendPath)) return false;
  const logPath = path.join(app.getPath("userData"), "rank-local-api.log");
  const log = fs.openSync(logPath, "a");
  backendProcess = spawn(
    backendPath,
    [
      "--db",
      path.join(app.getPath("userData"), "rank_local.db"),
      "--host",
      "127.0.0.1",
      "--port",
      "8765",
    ],
    { stdio: ["ignore", log, log], windowsHide: true },
  );
  backendProcess.on("error", (error) => fs.appendFileSync(logPath, `\nbackend spawn error: ${error.message}\n`));
  backendProcess.on("exit", (code, signal) => fs.appendFileSync(logPath, `\nbackend exited: code=${code} signal=${signal}\n`));
  return true;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1536,
    height: 1024,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: "#f7f9fb",
    title: "六大財務指標 Rank",
    show: false,
    autoHideMenuBar: true,
    webPreferences: { contextIsolation: true, sandbox: true },
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https:\/\//.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith("file://")) event.preventDefault();
  });
  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.on("closed", () => { mainWindow = null; });
  mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
}
app.whenReady().then(async () => {
  startBackend();
  await waitForBackend();
  createWindow();
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
app.on("second-instance", () => {
  if (!mainWindow) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.focus();
});
app.on("before-quit", () => {
  if (backendProcess) backendProcess.kill();
});
