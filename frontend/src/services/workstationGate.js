const LINKED_KEY = "crps_workstation_linked";
const DEVICE_ID_KEY = "crps_workstation_device_id";

export function isElectronApp() {
  return typeof window !== "undefined" && typeof window.crpsDesktop?.getMachineInfo === "function";
}

export function isWorkstationLinked() {
  return localStorage.getItem(LINKED_KEY) === "1";
}

export function setWorkstationLinked(deviceId) {
  localStorage.setItem(LINKED_KEY, "1");
  localStorage.setItem(DEVICE_ID_KEY, deviceId);
  window.dispatchEvent(new Event("crps-workstation-linked"));
}

export function clearWorkstationLink() {
  localStorage.removeItem(LINKED_KEY);
  localStorage.removeItem(DEVICE_ID_KEY);
  window.dispatchEvent(new Event("crps-workstation-unlinked"));
}

export function getWorkstationDeviceId() {
  return localStorage.getItem(DEVICE_ID_KEY);
}

/** Relative path under /api (no query), e.g. auth/login */
export function normalizeApiPath(url) {
  if (!url) return "";
  let path = url;
  try {
    if (path.startsWith("http")) {
      path = new URL(path).pathname;
    }
  } catch {
    /* keep path */
  }
  path = path.split("?")[0];
  if (path.startsWith("/api/")) path = path.slice(5);
  else if (path.startsWith("/")) path = path.slice(1);
  return path.replace(/\/$/, "");
}

export function isWorkstationPathExempt(path) {
  if (!path) return true;
  if (path === "devices/workstation/link") return true;
  if (path.startsWith("auth/")) return true;
  if (path.startsWith("sentinel/")) return true;
  return false;
}
