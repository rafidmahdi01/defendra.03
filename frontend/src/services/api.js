import axios, { CanceledError } from "axios";

import {
  clearWorkstationLink,
  isElectronApp,
  isWorkstationLinked,
  isWorkstationPathExempt,
  normalizeApiPath,
} from "./workstationGate";

export const API_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || "https://api.technohavenmalaysia.com";

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const method = (config.method || "").toLowerCase();
  if (["post", "put", "patch", "delete"].includes(method)) {
    if (config.data === undefined || config.data === null) {
      config.data = {};
    }
  }

  const path = normalizeApiPath(config.url || "");
  const token = localStorage.getItem("crps_token");
  if (
    isElectronApp() &&
    token &&
    !isWorkstationLinked() &&
    !isWorkstationPathExempt(path)
  ) {
    return Promise.reject(new CanceledError("Connect this computer in the desktop app to use Defendra services."));
  }

  const tokenHeader = localStorage.getItem("crps_token");
  if (tokenHeader) {
    config.headers.Authorization = `Bearer ${tokenHeader}`;
  }
  return config;
});

function redirectToLoginIfNeeded() {
  const hash = (window.location.hash || "").toLowerCase();
  if (hash.startsWith("#/login") || hash.startsWith("#login")) return;

  // Use HashRouter navigation to preserve local desktop file/server context
  if (window.location.hash || window.location.protocol === "file:" || window.location.port) {
    window.location.hash = "#/login";
    return;
  }

  const path = (window.location.pathname.replace(/\/$/, "") || "/").toLowerCase();
  if (path === "/login") return;
  window.location.hash = "#/login";
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = (error.config?.url || "").toLowerCase();
    const isAuthRoute =
      url.includes("/auth/login") ||
      url.includes("/auth/request-otp") ||
      url.includes("/auth/bootstrap-admin") ||
      url.includes("/auth/register");

    if (error.response?.status === 401 && !isAuthRoute) {
      localStorage.removeItem("crps_token");
      localStorage.removeItem("crps_user");
      clearWorkstationLink();
      redirectToLoginIfNeeded();
    }
    return Promise.reject(error);
  }
);

export { clearWorkstationLink, getWorkstationDeviceId, isElectronApp, isWorkstationLinked, setWorkstationLinked } from "./workstationGate";

