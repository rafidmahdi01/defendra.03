import axios, { CanceledError } from "axios";

import {
  clearWorkstationLink,
  isElectronApp,
  isWorkstationLinked,
  isWorkstationPathExempt,
  normalizeApiPath,
} from "./workstationGate";

export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 15000,
});

api.interceptors.request.use((config) => {
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
  const path =
    (window.location.pathname.replace(/\/$/, "") || "/").toLowerCase();
  if (path === "/login") return;
  window.location.replace("/login");
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("crps_token");
      localStorage.removeItem("crps_user");
      clearWorkstationLink();
      redirectToLoginIfNeeded();
    }
    return Promise.reject(error);
  }
);

export { clearWorkstationLink, getWorkstationDeviceId, isElectronApp, isWorkstationLinked, setWorkstationLinked } from "./workstationGate";
