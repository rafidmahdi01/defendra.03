import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { API_URL } from "@/services/api";

type Ctx = { connected: boolean; checking: boolean };

const ServiceConnectedContext = createContext<Ctx | null>(null);

export function ServiceConnectedProvider({ children }: { children: ReactNode }) {
  const [checking, setChecking] = useState(true);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const probe = async () => {
      if (!navigator.onLine) {
        if (!cancelled) {
          setConnected(false);
          setChecking(false);
        }
        return;
      }
      try {
        const r = await fetch(`${API_URL}/health`, {
          method: "GET",
          signal: AbortSignal.timeout(4000),
        });
        if (!cancelled) {
          setConnected(r.ok);
          setChecking(false);
        }
      } catch {
        if (!cancelled) {
          setConnected(false);
          setChecking(false);
        }
      }
    };

    probe();
    const id = setInterval(probe, 10_000);
    window.addEventListener("online", probe);
    window.addEventListener("offline", probe);
    return () => {
      cancelled = true;
      clearInterval(id);
      window.removeEventListener("online", probe);
      window.removeEventListener("offline", probe);
    };
  }, []);

  return (
    <ServiceConnectedContext.Provider value={{ connected, checking }}>
      {children}
    </ServiceConnectedContext.Provider>
  );
}

export function useServiceConnected(): Ctx {
  const ctx = useContext(ServiceConnectedContext);
  if (!ctx) {
    throw new Error("useServiceConnected must be used within ServiceConnectedProvider");
  }
  return ctx;
}
