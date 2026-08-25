const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const path = require("path");

let backendProcess;

function startBackend() {
  const executable =
    process.platform === "win32" ? "rank-local-api.exe" : "rank-local-api";
  const backendPath = app.isPackaged
    ? path.join(process.resourcesPath, "backend", executable)
    : null;
  if (!backendPath) return;
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
    { stdio: "ignore", windowsHide: true },
  );
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1536,
    height: 1024,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: "#f7f9fb",
    title: "六大財務指標 Rank",
    webPreferences: { contextIsolation: true, sandbox: true },
  });
  win.loadFile(path.join(__dirname, "../dist/index.html"));
}
app.whenReady().then(() => {
  startBackend();
  setTimeout(createWindow, 350);
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
app.on("before-quit", () => {
  if (backendProcess) backendProcess.kill();
});
