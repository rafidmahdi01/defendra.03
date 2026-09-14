const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("crpsDesktop", {
  getVersion: () => ipcRenderer.invoke("app-version"),
  getSystemMetrics: () => ipcRenderer.invoke("system-metrics"),
  getMachineInfo: () => ipcRenderer.invoke("machine-info"),
});
