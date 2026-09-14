import { useEffect, useState } from "react";
import { Bell, CheckCircle2, Trash2 } from "lucide-react";

import { GlassCard } from "@/components/defendra/Card";
import { api } from "@/services/api";
import { useServiceConnected } from "@/hooks/useServiceConnected";

type Alert = {
  id: number | string;
  title: string;
  severity: string;
  status: string;
  created_at: string;
};

export default function AlertsPage() {
  const { connected } = useServiceConnected();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [clearing, setClearing] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get<Alert[]>("/alerts");
      setAlerts(data);
    } catch {
      setAlerts([]);
    }
  };

  const resolve = async (id: Alert["id"]) => {
    if (!connected) return;
    await api.put(`/alerts/${id}`, { status: "resolved" });
    load();
  };

  useEffect(() => {
    load();
  }, []);

  const clearAll = async () => {
    if (!connected || alerts.length === 0 || clearing) return;
    
    const confirmed = window.confirm(
      `Are you sure you want to permanently delete all ${alerts.length} alert${alerts.length !== 1 ? 's' : ''}? This action cannot be undone.`
    );
    
    if (!confirmed) return;
    
    setClearing(true);
    try {
      await api.delete("/alerts");
      setAlerts([]);
    } catch {
      // keep list if server delete fails
    } finally {
      setClearing(false);
    }
  };

  const open = alerts.filter((a) => a.status !== "resolved").length;

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3 px-1">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Alerts</h1>
          <p className="text-xs text-muted-foreground">
            {open} open incident{open === 1 ? "" : "s"} · review and triage
          </p>
        </div>
        <button
          type="button"
          disabled={!connected || alerts.length === 0 || clearing}
          onClick={clearAll}
          className="flex items-center gap-1.5 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-3 py-2 text-xs font-medium text-[var(--danger)] transition hover:bg-[var(--danger)]/20 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Trash2 className={`h-3.5 w-3.5 ${clearing ? "animate-pulse" : ""}`} /> Clear All
        </button>
      </header>

      <GlassCard
        title="Incident queue"
        subtitle="Triage in priority order"
        icon={<Bell className="h-4 w-4 text-[var(--danger)]" />}
      >
        <div className="overflow-hidden rounded-xl ring-1 ring-white/5">
          <table className="w-full text-left text-xs">
            <thead className="bg-white/5 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Time</th>
                <th className="px-3 py-2 font-medium">Title</th>
                <th className="px-3 py-2 font-medium">Severity</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {alerts.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                    No alerts. The fleet is calm.
                  </td>
                </tr>
              )}
              {alerts.map((row) => (
                <tr
                  key={row.id}
                  className="border-t border-white/5 transition hover:bg-white/[0.03]"
                >
                  <td className="px-3 py-2 text-muted-foreground tabular-nums">
                    {new Date(row.created_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 font-medium">{row.title}</td>
                  <td className="px-3 py-2">
                    <SeverityPill value={row.severity} />
                  </td>
                  <td className="px-3 py-2">
                    <StatusPill value={row.status} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    {row.status !== "resolved" ? (
                      <button
                        type="button"
                        disabled={!connected}
                        onClick={() => resolve(row.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--mint)] px-2.5 py-1 text-[10px] font-semibold text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <CheckCircle2 className="h-3 w-3" />
                        Resolve
                      </button>
                    ) : (
                      <span className="text-[10px] text-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}

function SeverityPill({ value }: { value?: string }) {
  const v = (value || "info").toLowerCase();
  const color =
    v === "critical" || v === "crit"
      ? "var(--danger)"
      : v === "high"
        ? "var(--warning)"
        : v === "medium" || v === "med"
          ? "var(--cyan)"
          : "var(--muted-foreground)";
  return (
    <span
      className="rounded-md px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ring-1"
      style={{ color, background: `${color}22`, borderColor: `${color}55` }}
    >
      {value || "info"}
    </span>
  );
}

function StatusPill({ value }: { value: string }) {
  const v = value.toLowerCase();
  const color =
    v === "resolved"
      ? "var(--success)"
      : v === "open" || v === "new"
        ? "var(--danger)"
        : "var(--cyan)";
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[10px] font-medium ring-1"
      style={{ color, background: `${color}1f`, borderColor: `${color}55` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {value}
    </span>
  );
}
