import { Fish, Cpu, Network, HeartPulse, MonitorSmartphone, DatabaseBackup } from "lucide-react";
import { GlassCard } from "./Card";
import { useTelemetry, formatRelative } from "@/hooks/useTelemetry";

function Ring({ value, color }: { value: number; color: string }) {
  const r = 24;
  const c = 2 * Math.PI * r;
  const off = c - (value / 100) * c;
  return (
    <svg viewBox="0 0 60 60" className="h-20 w-20">
      <circle cx="30" cy="30" r={r} stroke="oklch(1 0 0 / 0.07)" strokeWidth="4" fill="none" />
      <circle
        cx="30" cy="30" r={r}
        stroke={color} strokeWidth="4" fill="none"
        strokeDasharray={c} strokeDashoffset={off}
        strokeLinecap="round" transform="rotate(-90 30 30)"
        style={{ filter: `drop-shadow(0 0 10px ${color}) drop-shadow(0 0 18px ${color})`, transition: "stroke-dashoffset 0.8s ease" }}
      />
      <text x="30" y="34.5" textAnchor="middle" fontSize="14" fontWeight="700" fill="currentColor" className="tabular-nums">
        {value}
      </text>
    </svg>
  );
}

export function PhishingCard() {
  const { phishing } = useTelemetry();
  return (
    <GlassCard title="AI Phishing Defense" subtitle="LLM-powered email scan" icon={<Fish className="h-4 w-4 text-[var(--purple)]" />}>
      <div className="flex items-center gap-4">
        <Ring value={phishing.score} color="var(--purple)" />
        <div className="space-y-1.5 text-xs">
          <Row label="Scanned" value={phishing.scanned.toLocaleString()} />
          <Row label="Quarantined" value={phishing.quarantined.toLocaleString()} tone="warn" />
          <Row label="False positives" value={`${phishing.fpRate.toFixed(2)}%`} tone="ok" />
        </div>
      </div>
    </GlassCard>
  );
}

export function EndpointCard() {
  const { endpoint } = useTelemetry();
  return (
    <GlassCard title="Endpoint Security" subtitle="EDR agents online" icon={<Cpu className="h-4 w-4 text-[var(--cyan)]" />}>
      <div className="flex items-center gap-4">
        <Ring value={endpoint.score} color="var(--cyan)" />
        <div className="space-y-1.5 text-xs">
          <Row label="Devices" value={endpoint.devices.toLocaleString()} />
          <Row label="At risk" value={String(endpoint.atRisk)} tone="warn" />
          <Row label="Isolated" value={String(endpoint.isolated)} tone="bad" />
        </div>
      </div>
    </GlassCard>
  );
}

export function ZeroTrustCard() {
  const { zeroTrust } = useTelemetry();
  return (
    <GlassCard title="Zero Trust Network" subtitle="Continuous verification" icon={<Network className="h-4 w-4 text-[var(--electric)]" />}>
      <div className="space-y-3">
        <Bar label="Identity" value={zeroTrust.identity} color="var(--electric)" />
        <Bar label="Device Posture" value={zeroTrust.device} color="var(--cyan)" />
        <Bar label="Network Segment" value={zeroTrust.network} color="var(--purple)" />
        <Bar label="Workload" value={zeroTrust.workload} color="var(--warning)" />
      </div>
    </GlassCard>
  );
}

export function SystemHealthCard() {
  const { health } = useTelemetry();
  const items: [string, boolean][] = [
    ["SIEM", health.siem],
    ["XDR Engine", health.xdr],
    ["Identity Broker", health.identity],
    ["Backup Vault", health.vault],
  ];
  return (
    <GlassCard title="System Health" subtitle="Core services" icon={<HeartPulse className="h-4 w-4 text-[var(--success)]" />}>
      <div className="grid grid-cols-2 gap-2 text-xs">
        {items.map(([k, ok]) => (
          <div key={k} className="glass-strong flex items-center justify-between rounded-lg px-2.5 py-2">
            <span className="text-muted-foreground">{k}</span>
            <span className="flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-[var(--success)] animate-pulse-glow" : "bg-[var(--warning)]"}`} />
              <span className="text-[10px] font-medium">{ok ? "Operational" : "Degraded"}</span>
            </span>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

export function DevicesAlertsCard() {
  const { alerts, now } = useTelemetry();
  const nowMs = now.getTime();
  return (
    <GlassCard title="Active Alerts" subtitle="Triage queue" icon={<MonitorSmartphone className="h-4 w-4 text-[var(--danger)]" />}>
      <div className="space-y-2">
        {alerts.map((a) => (
          <div key={a.id} className="glass-strong flex items-center gap-3 rounded-lg px-3 py-2 animate-in fade-in slide-in-from-top-1">
            <span className={`rounded-md px-1.5 py-0.5 text-[9px] font-bold tracking-wider ${
              a.sev === "CRIT" ? "bg-[var(--danger)]/20 text-[var(--danger)] ring-1 ring-[var(--danger)]/40" :
              a.sev === "HIGH" ? "bg-[var(--warning)]/20 text-[var(--warning)] ring-1 ring-[var(--warning)]/40" :
              a.sev === "MED" ? "bg-[var(--cyan)]/15 text-[var(--cyan)] ring-1 ring-[var(--cyan)]/30" :
              "bg-white/5 text-muted-foreground ring-1 ring-white/10"
            }`}>{a.sev}</span>
            <span className="flex-1 truncate text-xs">{a.msg}</span>
            <span className="text-[10px] text-muted-foreground tabular-nums">{formatRelative(a.ts, nowMs)}</span>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

export function BackupCard() {
  const { backup } = useTelemetry();
  return (
    <GlassCard title="Backup & Recovery" subtitle="Immutable vault · last sync 4m ago" icon={<DatabaseBackup className="h-4 w-4 text-[var(--success)]" />}>
      <div className="flex items-center gap-4">
        <Ring value={backup.score} color="var(--success)" />
        <div className="space-y-1.5 text-xs">
          <Row label="Snapshots" value={backup.snapshots.toLocaleString()} />
          <Row label="RPO" value="< 5 min" tone="ok" />
          <Row label="RTO" value="< 30 min" tone="ok" />
        </div>
      </div>
    </GlassCard>
  );
}

function Row({ label, value, tone }: { label: string; value: string; tone?: "ok" | "warn" | "bad" }) {
  const c = tone === "ok" ? "text-[var(--success)]" : tone === "warn" ? "text-[var(--warning)]" : tone === "bad" ? "text-[var(--danger)]" : "text-foreground";
  return (
    <div className="flex items-center justify-between gap-6">
      <span className="text-muted-foreground">{label}</span>
      <span className={`font-medium ${c}`}>{value}</span>
    </div>
  );
}

function Bar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{value}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${value}%`, background: color, boxShadow: `0 0 10px ${color}` }}
        />
      </div>
    </div>
  );
}