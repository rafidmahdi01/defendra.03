const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("crpsDesktop", {
  getVersion: () => ipcRenderer.invoke("app-version"),
  getSystemMetrics: () => ipcRenderer.invoke("system-metrics"),
  getMachineInfo: () => ipcRenderer.invoke("machine-info"),
  saveApiKey: (apiKey) => ipcRenderer.invoke("save-api-key", apiKey),
  getApiKey: () => ipcRenderer.invoke("get-api-key"),
});
