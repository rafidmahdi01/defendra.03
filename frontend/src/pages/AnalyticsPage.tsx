import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, LineChart as LineChartIcon } from "lucide-react";

import { AnalyticsChart } from "@/components/defendra/AnalyticsChart";
import { GlassCard } from "@/components/defendra/Card";
import { useServiceConnected } from "@/hooks/useServiceConnected";
import type { TrendPoint } from "@/hooks/useTelemetry";
import { api } from "@/services/api";

type Device = {
  id: number | string;
  hostname: string;
  cpu_usage?: number;
  ram_usage?: number;
};

export default function AnalyticsPage() {
  const { connected } = useServiceConnected();
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoadErr(null);
      try {
        const [t, d] = await Promise.allSettled([
          api.get<TrendPoint[]>("/analytics/trends?days=14"),
          api.get<Device[]>("/devices"),
        ]);
        if (t.status === "fulfilled") setTrends(t.value.data);
        else setTrends([]);
        if (d.status === "fulfilled") setDevices(d.value.data);
        else setDevices([]);
        if (t.status === "rejected" && d.status === "rejected") setLoadErr("Could not load analytics.");
      } catch {
        setLoadErr("Could not load analytics.");
      }
    };
    load();
  }, []);

  useEffect(() => {
    if (!connected) return;
    const load = async () => {
      try {
        const [t, d] = await Promise.allSettled([
          api.get<TrendPoint[]>("/analytics/trends?days=14"),
          api.get<Device[]>("/devices"),
        ]);
        if (t.status === "fulfilled") setTrends(t.value.data);
        if (d.status === "fulfilled") setDevices(d.value.data);
      } catch {
        /* keep existing */
      }
    };
    load();
    const id = setInterval(load, 12_000);
    return () => clearInterval(id);
  }, [connected]);

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3 px-1">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
          <p className="text-xs text-muted-foreground">
            Threat vectors, trends and endpoint resource utilisation
          </p>
          {loadErr && (
            <p className="mt-1 text-[11px] text-[var(--danger)]">{loadErr}</p>
          )}
          {!connected && (
            <p className="mt-1 text-[11px] text-muted-foreground">Connect to the server to refresh charts.</p>
          )}
        </div>
      </header>

      <AnalyticsChart />

      <div className="grid gap-4 xl:grid-cols-2">
        <GlassCard
          title="Security trends"
          subtitle="Past 14 days · alerts & logs from the API"
          icon={<LineChartIcon className="h-4 w-4 text-[var(--cyan)]" />}
        >
          <div className="h-64 w-full">
            {trends.length === 0 ? (
              <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                No trend rows yet (no alerts/logs in this range).
              </div>
            ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends}>
                <defs>
                  <linearGradient id="g-alerts" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.7 0.24 22)" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="oklch(0.7 0.24 22)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="g-logs" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.86 0.2 165)" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="oklch(0.86 0.2 165)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="oklch(1 0 0 / 0.06)" />
                <XAxis dataKey="label" stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <YAxis stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <Tooltip
                  contentStyle={{
                    background: "oklch(0.18 0.04 265 / 0.9)",
                    border: "1px solid oklch(0.86 0.2 165 / 0.22)",
                    borderRadius: 12,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area
                  type="monotone"
                  dataKey="alerts"
                  name="Alerts"
                  stroke="oklch(0.7 0.24 22)"
                  strokeWidth={2}
                  fill="url(#g-alerts)"
                />
                <Area
                  type="monotone"
                  dataKey="logs"
                  name="Logs"
                  stroke="oklch(0.86 0.2 165)"
                  strokeWidth={2}
                  fill="url(#g-logs)"
                />
              </AreaChart>
            </ResponsiveContainer>
            )}
          </div>
        </GlassCard>

        <GlassCard
          title="Endpoint resources"
          subtitle="CPU & memory per device"
          icon={<Activity className="h-4 w-4 text-[var(--purple)]" />}
        >
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={devices.slice(0, 8).map((d) => ({
                name: d.hostname,
                CPU: d.cpu_usage ?? 0,
                RAM: d.ram_usage ?? 0,
              }))}>
                <CartesianGrid stroke="oklch(1 0 0 / 0.06)" />
                <XAxis dataKey="name" stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <YAxis stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <Tooltip
                  contentStyle={{
                    background: "oklch(0.18 0.04 265 / 0.9)",
                    border: "1px solid oklch(0.86 0.2 165 / 0.22)",
                    borderRadius: 12,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="CPU" fill="oklch(0.86 0.2 165)" radius={[6, 6, 0, 0]} />
                <Bar dataKey="RAM" fill="oklch(0.7 0.18 195)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
