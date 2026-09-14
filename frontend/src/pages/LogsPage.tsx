import { useEffect, useState } from "react";
import { Download, ScrollText, Search, Trash2 } from "lucide-react";

import { GlassCard } from "@/components/defendra/Card";
import { api } from "@/services/api";
import { useServiceConnected } from "@/hooks/useServiceConnected";

type LogRow = {
  id: number | string;
  created_at: string;
  device_id?: number | string;
  category?: string;
  severity?: string;
  message: string;
};

export default function LogsPage() {
  const { connected } = useServiceConnected();
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [query, setQuery] = useState("");
  const [clearing, setClearing] = useState(false);

  const load = async () => {
    try {
      const endpoint = query
        ? `/logs/search?q=${encodeURIComponent(query)}`
        : "/logs";
      const { data } = await api.get<LogRow[]>(endpoint);
      setLogs(data);
    } catch {
      setLogs([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const clearAll = async () => {
    if (!connected || logs.length === 0 || clearing) return;
    
    const confirmed = window.confirm(
      `Are you sure you want to permanently delete all ${logs.length} log${logs.length !== 1 ? 's' : ''}? This action cannot be undone.`
    );
    
    if (!confirmed) return;
    
    setClearing(true);
    try {
      await api.delete("/logs");
      setLogs([]);
    } catch {
      // keep list if server delete fails
    } finally {
      setClearing(false);
    }
  };

  const exportCsv = async () => {
    if (!connected) return;
    const response = await api.get("/logs/export", { responseType: "blob" });
    const url = URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = "security-logs.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3 px-1">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Security Logs</h1>
          <p className="text-xs text-muted-foreground">
            Searchable telemetry from every protected endpoint
          </p>
        </div>
        <button
          type="button"
          disabled={!connected || logs.length === 0 || clearing}
          onClick={clearAll}
          className="flex items-center gap-1.5 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-3 py-2 text-xs font-medium text-[var(--danger)] transition hover:bg-[var(--danger)]/20 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Trash2 className={`h-3.5 w-3.5 ${clearing ? "animate-pulse" : ""}`} /> Clear All
        </button>
      </header>

      <GlassCard>
        <div className="flex flex-col gap-3 md:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              disabled={!connected}
              className="h-10 w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-3 text-sm placeholder:text-muted-foreground/70 focus:border-[var(--electric)]/50 focus:outline-none focus:ring-2 focus:ring-[var(--electric)]/20 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="Search logs by message, device, category…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && connected && load()}
            />
          </div>
          <button
            type="button"
            disabled={!connected}
            onClick={load}
            className="h-10 rounded-xl bg-gradient-cyber px-5 text-sm font-semibold text-primary-foreground transition hover:brightness-110 glow-blue disabled:cursor-not-allowed disabled:opacity-40"
          >
            Search
          </button>
          <button
            type="button"
            disabled={!connected}
            onClick={exportCsv}
            className="glass-strong flex h-10 items-center gap-2 rounded-xl px-4 text-sm font-medium transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Download className="h-4 w-4" /> Export CSV
          </button>
        </div>
      </GlassCard>

      <GlassCard
        title="Recent entries"
        subtitle={`${logs.length} record${logs.length === 1 ? "" : "s"}`}
        icon={<ScrollText className="h-4 w-4 text-[var(--cyan)]" />}
      >
        <div className="overflow-hidden rounded-xl ring-1 ring-white/5">
          <table className="w-full text-left text-xs">
            <thead className="bg-white/5 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Time</th>
                <th className="px-3 py-2 font-medium">Device</th>
                <th className="px-3 py-2 font-medium">Category</th>
                <th className="px-3 py-2 font-medium">Severity</th>
                <th className="px-3 py-2 font-medium">Message</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                    No log entries yet.
                  </td>
                </tr>
              )}
              {logs.map((row) => (
                <tr
                  key={row.id}
                  className="border-t border-white/5 transition hover:bg-white/[0.03]"
                >
                  <td className="px-3 py-2 text-muted-foreground tabular-nums">
                    {new Date(row.created_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{row.device_id ?? "—"}</td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {row.category ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    <SeverityPill value={row.severity} />
                  </td>
                  <td className="px-3 py-2">{row.message}</td>
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
      : v === "high" || v === "warning" || v === "warn"
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
