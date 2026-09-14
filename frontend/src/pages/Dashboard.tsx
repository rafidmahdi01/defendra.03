import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  DatabaseBackup,
  HardDrive,
  Monitor,
  RadioTower,
  ShieldOff,
  Wifi,
  WifiOff,
  Zap,
} from "lucide-react";

import { GlassCard } from "@/components/defendra/Card";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useTelemetry, formatRelative } from "@/hooks/useTelemetry";

function sevColor(sev?: string) {
  const s = (sev || "").toLowerCase();
  if (s === "critical") return "var(--danger)";
  if (s === "medium")   return "var(--cyan)";
  if (s === "low")      return "var(--success)";
  return "var(--warning)";
}


export default function Dashboard() {
  const navigate = useNavigate();
  const t = useTelemetry();
  const { user, isAdmin } = useCurrentUser();
  const firstName = useMemo(
    () => (user.full_name || user.email || "Analyst").split(/[ @]/)[0],
    [user.email, user.full_name],
  );
  const clock = t.now.toISOString().slice(11, 19);

  const { overview, trends, recentAlerts, recentLogs } = t;

  const timelineData = trends.map((p) => ({
    t: p.label,
    Logs:     p.logs,
    Alerts:   p.alerts,
    Critical: p.critical,
  }));

  return (
    <div className="space-y-4">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-3 px-1">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-xs text-muted-foreground">
            Welcome back, {firstName}. Real-time posture overview · UTC {clock}
          </p>
        </div>
      </header>

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          icon={<HardDrive className="h-5 w-5" />}
          label={isAdmin ? "Total Devices" : "Your Devices"}
          value={overview.total_devices.toString()}
          sub={isAdmin ? "All users in fleet" : "Linked to your account"}
          color="var(--cyan)"
          onClick={() => navigate("/devices")}
        />
        <StatCard
          icon={<AlertTriangle className="h-5 w-5" />}
          label="Critical Alerts"
          value={overview.critical_alerts.toString()}
          sub="Open incidents"
          color="var(--danger)"
          pulse={overview.critical_alerts > 0}
          onClick={() => navigate("/alerts")}
        />
        <StatCard
          icon={<DatabaseBackup className="h-5 w-5" />}
          label="Logs Today"
          value={overview.logs_today.toString()}
          sub={`${overview.pending_queue} pending sync`}
          color="var(--mint)"
          onClick={() => navigate("/logs")}
        />
      </div>

      {/* Device Overview + Recent Alerts */}
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <GlassCard
          title="Device Status Overview"
          subtitle="Live fleet health"
          icon={<Monitor className="h-4 w-4 text-[var(--cyan)]" />}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <DeviceRow icon={<Wifi className="h-4 w-4" />}       label="Online Devices"   value={overview.active_devices}  color="var(--success)" />
            <DeviceRow icon={<WifiOff className="h-4 w-4" />}    label="Offline Devices"  value={overview.offline_devices} color="var(--danger)"  />
            <DeviceRow icon={<ShieldOff className="h-4 w-4" />}  label="Isolated Devices" value={0}                        color="var(--warning)" />
            <DeviceRow icon={<RadioTower className="h-4 w-4" />} label="Limp Mode"        value={0}                        color="var(--purple)"  />
          </div>
          <div className="mt-4 space-y-2">
            <MiniBar label="Online"  value={overview.active_devices}  total={overview.total_devices} color="var(--success)" />
            <MiniBar label="Offline" value={overview.offline_devices} total={overview.total_devices} color="var(--danger)"  />
          </div>
        </GlassCard>

        {/* Recent Alerts */}
        <GlassCard
          title="Recent Alerts"
          subtitle="Latest security incidents"
          icon={<Zap className="h-4 w-4 text-[var(--warning)]" />}
        >
          {recentAlerts.length === 0 ? (
            <p className="py-8 text-center text-xs text-muted-foreground">No alerts yet.</p>
          ) : (
            <div className="space-y-2">
              {recentAlerts.map((a) => (
                <div key={a.id} className="glass-strong flex items-start gap-2.5 rounded-xl px-3 py-2.5">
                  <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: sevColor(a.severity) }} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs">{a.title}</p>
                    <p className="mt-0.5 text-[10px] text-muted-foreground tabular-nums">
                      {formatRelative(a.created_at)} ago
                    </p>
                  </div>
                  <span
                    className="shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold ring-1"
                    style={{ color: sevColor(a.severity), borderColor: sevColor(a.severity) }}
                  >
                    {a.severity.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>

      {/* Threat Monitoring Timeline */}
      <GlassCard
        title="Threat Monitoring Timeline"
        subtitle="Logs · alerts · critical events (last 7 days)"
        icon={<AlertTriangle className="h-4 w-4 text-[var(--danger)]" />}
      >
        {timelineData.length === 0 ? (
          <p className="py-16 text-center text-xs text-muted-foreground">No trend data available yet.</p>
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timelineData} margin={{ top: 4, right: 8, left: -12, bottom: 0 }}>
                <defs>
                  {[
                    { id: "g-logs",     color: "oklch(0.86 0.2 165)" },
                    { id: "g-alerts",   color: "oklch(0.7 0.24 22)"  },
                    { id: "g-critical", color: "oklch(0.7 0.18 195)" },
                  ].map(({ id, color }) => (
                    <linearGradient key={id} id={id} x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%"   stopColor={color} stopOpacity={0.4} />
                      <stop offset="100%" stopColor={color} stopOpacity={0}   />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid stroke="oklch(1 0 0 / 0.06)" />
                <XAxis dataKey="t"  stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <YAxis             stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <Tooltip contentStyle={{ background: "oklch(0.18 0.04 265 / 0.9)", border: "1px solid oklch(0.86 0.2 165 / 0.22)", borderRadius: 12, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area type="monotone" dataKey="Logs"     stroke="oklch(0.86 0.2 165)" strokeWidth={2} fill="url(#g-logs)"     />
                <Area type="monotone" dataKey="Alerts"   stroke="oklch(0.7 0.24 22)"  strokeWidth={2} fill="url(#g-alerts)"   />
                <Area type="monotone" dataKey="Critical" stroke="oklch(0.7 0.18 195)" strokeWidth={2} fill="url(#g-critical)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </GlassCard>

      {/* Recent Activity — from real logs API via telemetry */}
      <GlassCard
        title="Recent Activity"
        subtitle="Latest log events from the fleet"
        icon={<Clock className="h-4 w-4 text-[var(--mint)]" />}
      >
        {recentLogs.length === 0 ? (
          <p className="py-8 text-center text-xs text-muted-foreground">No recent activity.</p>
        ) : (
          <div className="overflow-hidden rounded-xl ring-1 ring-white/5">
            <table className="w-full text-left text-xs">
              <thead className="bg-white/5 text-[10px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  <Th>Message</Th>
                  <Th>Category</Th>
                  <Th>Severity</Th>
                  <Th>Time</Th>
                </tr>
              </thead>
              <tbody>
                {recentLogs.map((log) => (
                  <tr key={log.id} className="border-t border-white/5 transition hover:bg-white/[0.03]">
                    <Td className="font-medium">{log.message}</Td>
                    <Td>{log.category}</Td>
                    <Td><SevPill label={log.severity} /></Td>
                    <Td className="tabular-nums text-muted-foreground">
                      {new Date(log.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  sub,
  color,
  pulse,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  color: string;
  pulse?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="glass group relative w-full overflow-hidden rounded-3xl p-5 text-left transition-all hover:border-[var(--mint)]/40 hover:brightness-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--mint)]/50 shimmer-border cursor-pointer"
    >
      <div className="pointer-events-none absolute inset-x-6 -top-px h-px bg-gradient-to-r from-transparent via-[var(--mint)]/70 to-transparent" />
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl ring-1"
          style={{ background: `${color}18`, color, boxShadow: `0 0 18px -4px ${color}`, borderColor: `${color}40` }}>
          {icon}
        </div>
        {pulse && (
          <span className="flex h-2 w-2 items-center justify-center">
            <span className="absolute h-2 w-2 rounded-full bg-[var(--danger)] animate-ping" />
            <span className="h-2 w-2 rounded-full bg-[var(--danger)]" />
          </span>
        )}
      </div>
      <div className="mt-3">
        <div className="text-3xl font-bold tabular-nums tracking-tight" style={{ color }}>{value}</div>
        <div className="mt-0.5 text-sm font-medium">{label}</div>
        <div className="mt-0.5 text-[11px] text-muted-foreground">{sub}</div>
      </div>
    </button>
  );
}

function DeviceRow({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number; color: string }) {
  return (
    <div className="glass-strong flex items-center gap-3 rounded-xl px-4 py-3">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg ring-1"
        style={{ background: `${color}18`, color, borderColor: `${color}40` }}>
        {icon}
      </span>
      <div>
        <div className="text-[11px] text-muted-foreground">{label}</div>
        <div className="text-xl font-bold tabular-nums" style={{ color }}>{value}</div>
      </div>
    </div>
  );
}

function MiniBar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="text-muted-foreground">{label}</span>
        <span className="tabular-nums" style={{ color }}>{value} / {total}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 font-medium">{children}</th>;
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2.5 ${className}`}>{children}</td>;
}

function SevPill({ label }: { label: string }) {
  const color = sevColor(label);
  return (
    <span className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-medium ring-1"
      style={{ color, background: `${color}20`, borderColor: `${color}55` }}>
      <CheckCircle2 className="h-2.5 w-2.5" />
      {label}
    </span>
  );
}
