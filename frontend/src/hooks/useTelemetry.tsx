import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "@/services/api";

export type TrendPoint = {
  label: string;
  logs: number;
  alerts: number;
  critical: number;
};

export type Overview = {
  total_devices: number;
  active_devices: number;
  offline_devices: number;
  critical_alerts: number;
  logs_today: number;
  pending_queue: number;
};

export type RealAlert = {
  id: string;
  title: string;
  severity: string;
  status: string;
  created_at: string;
};

export type RealLog = {
  id: string;
  device_id: string;
  category: string;
  severity: string;
  source?: string | null;
  message: string;
  created_at: string;
};

export type Telemetry = {
  now: Date;
  overview: Overview;
  trends: TrendPoint[];
  recentAlerts: RealAlert[];
  recentLogs: RealLog[];
};

const EMPTY_OVERVIEW: Overview = {
  total_devices: 0,
  active_devices: 0,
  offline_devices: 0,
  critical_alerts: 0,
  logs_today: 0,
  pending_queue: 0,
};

const TelemetryContext = createContext<Telemetry | null>(null);

function overviewEqual(a: Overview, b: Overview): boolean {
  return (
    a.total_devices === b.total_devices &&
    a.active_devices === b.active_devices &&
    a.offline_devices === b.offline_devices &&
    a.critical_alerts === b.critical_alerts &&
    a.logs_today === b.logs_today &&
    a.pending_queue === b.pending_queue
  );
}

function alertsEqual(a: RealAlert[], b: RealAlert[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i].id !== b[i].id || a[i].status !== b[i].status) return false;
  }
  return true;
}

function trendsEqual(a: TrendPoint[], b: TrendPoint[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i].label !== b[i].label || a[i].logs !== b[i].logs || a[i].alerts !== b[i].alerts || a[i].critical !== b[i].critical) return false;
  }
  return true;
}

function logsEqual(a: RealLog[], b: RealLog[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (
      a[i].id !== b[i].id ||
      a[i].severity !== b[i].severity ||
      a[i].message !== b[i].message ||
      a[i].created_at !== b[i].created_at
    ) return false;
  }
  return true;
}

export function TelemetryProvider({ children, intervalMs = 10000 }: { children: ReactNode; intervalMs?: number }) {
  const [overview, setOverview] = useState<Overview>(EMPTY_OVERVIEW);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [recentAlerts, setRecentAlerts] = useState<RealAlert[]>([]);
  const [recentLogs, setRecentLogs] = useState<RealLog[]>([]);
  const [now, setNow] = useState(() => new Date());

  const prevRef = useRef({
    overview: EMPTY_OVERVIEW,
    trends: [] as TrendPoint[],
    recentAlerts: [] as RealAlert[],
    recentLogs: [] as RealLog[],
  });

  const fetchAll = useCallback(async () => {
    try {
      const [overviewRes, trendsRes, alertsRes, logsRes] = await Promise.allSettled([
        api.get<Overview>("/analytics/overview"),
        api.get<TrendPoint[]>("/analytics/trends?days=7"),
        api.get<RealAlert[]>("/alerts?limit=6"),
        api.get<RealLog[]>("/logs?limit=6"),
      ]);

      const newOverview = overviewRes.status === "fulfilled" ? overviewRes.value.data : EMPTY_OVERVIEW;
      const newTrends = trendsRes.status === "fulfilled" ? trendsRes.value.data : [];
      const newAlerts = alertsRes.status === "fulfilled" ? alertsRes.value.data : [];
      const newLogs = logsRes.status === "fulfilled" ? logsRes.value.data : [];

      if (!overviewEqual(prevRef.current.overview, newOverview)) {
        prevRef.current.overview = newOverview;
        setOverview(newOverview);
      }
      if (!trendsEqual(prevRef.current.trends, newTrends)) {
        prevRef.current.trends = newTrends;
        setTrends(newTrends);
      }
      if (!alertsEqual(prevRef.current.recentAlerts, newAlerts)) {
        prevRef.current.recentAlerts = newAlerts;
        setRecentAlerts(newAlerts);
      }
      if (!logsEqual(prevRef.current.recentLogs, newLogs)) {
        prevRef.current.recentLogs = newLogs;
        setRecentLogs(newLogs);
      }
      setNow(new Date());
    } catch {
      // keep previous state on error
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, fetchAll]);

  const value = useMemo<Telemetry>(
    () => ({ now, overview, trends, recentAlerts, recentLogs }),
    [now, overview, trends, recentAlerts, recentLogs],
  );

  return <TelemetryContext.Provider value={value}>{children}</TelemetryContext.Provider>;
}

export function useTelemetry(): Telemetry {
  const ctx = useContext(TelemetryContext);
  if (!ctx) throw new Error("useTelemetry must be used within <TelemetryProvider>");
  return ctx;
}

export function formatRelative(isoString: string, now = Date.now()): string {
  const s = Math.max(1, Math.floor((now - new Date(isoString).getTime()) / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  return `${h}h`;
}
