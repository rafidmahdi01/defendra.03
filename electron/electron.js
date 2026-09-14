const { app, BrowserWindow, ipcMain, shell } = require("electron");
const os = require("os");
const path = require("path");

// Keep hardware acceleration enabled; allow Electron to use the system GPU.
app.commandLine.appendSwitch("ignore-gpu-blocklist");

const isDev = Boolean(process.env.ELECTRON_START_URL);

/** Overall RAM use (0–100), host-wide — matches Task Manager “Memory” pressure reasonably well for dashboards. */
function ramUsagePercent() {
  const total = os.totalmem();
  if (!total) return 0;
  const used = total - os.freemem();
  return Math.min(100, Math.max(0, (100 * used) / total));
}

/** CPU busy % from jiffies delta across all logical processors (works on Windows). */
function cpuUsagePercent() {
  return new Promise((resolve) => {
    const start = os.cpus().map((c) => c.times);
    setTimeout(() => {
      const end = os.cpus().map((c) => c.times);
      let idleDiff = 0;
      let totalDiff = 0;
      for (let i = 0; i < end.length; i++) {
        const s = start[i];
        const e = end[i];
        idleDiff += e.idle - s.idle;
        totalDiff +=
          e.user - s.user +
          e.nice - s.nice +
          e.sys - s.sys +
          e.idle - s.idle +
          (e.irq - s.irq);
      }
      const pct = totalDiff > 0 ? 100 * (1 - idleDiff / totalDiff) : 0;
      resolve(Math.min(100, Math.max(0, pct)));
    }, 150);
  });
}

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: "#050816",
    title: "Defendra.AI",
    icon: path.join(__dirname, "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  if (isDev) {
    const devUrl = process.env.ELECTRON_START_URL || "http://127.0.0.1:5173";
    mainWindow.webContents.on("did-fail-load", (_e, code, desc, url) => {
      console.error("[electron] did-fail-load", { code, desc, url, devUrl });
    });
    mainWindow.webContents.on("did-finish-load", () => {
      console.log("[electron] loaded", mainWindow.webContents.getURL());
    });
    mainWindow.loadURL(devUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, "../frontend/dist/index.html"));
  }
}

app.whenReady().then(() => {
  ipcMain.handle("app-version", () => app.getVersion());
  ipcMain.handle("system-metrics", async () => {
    const [cpu, ram] = await Promise.all([cpuUsagePercent(), Promise.resolve(ramUsagePercent())]);
    return {
      cpu_usage: Math.round(cpu * 10) / 10,
      ram_usage: Math.round(ram * 10) / 10,
    };
  });
  ipcMain.handle("machine-info", () => {
    let ipAddress = "127.0.0.1";
    const nets = os.networkInterfaces();
    for (const entries of Object.values(nets)) {
      for (const entry of entries || []) {
        if (entry && entry.family === "IPv4" && !entry.internal) {
          ipAddress = entry.address;
          break;
        }
      }
      if (ipAddress !== "127.0.0.1") break;
    }
    return {
      hostname: os.hostname(),
      platform: process.platform,
      arch: os.arch(),
      ip_address: ipAddress,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    };
  });
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
