import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  Eye,
  Inbox,
  Paperclip,
  Search,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Trash2,
  User2,
  Zap,
} from "lucide-react";

import { GlassCard } from "@/components/defendra/Card";
import { useServiceConnected } from "@/hooks/useServiceConnected";
import { api } from "@/services/api";
import { isViewCleared, setViewCleared } from "@/services/viewClear";

type EmailAlert = {
  id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  created_at: string;
  device_id?: string | null;
  rule_name?: string | null;
};

const EMAILS_VIEW_KEY = "emails";
const STATUS_OPTIONS = ["All", "open", "acknowledged", "resolved"] as const;

function isEmailThreat(alert: EmailAlert) {
  return (
    (alert.rule_name || "").toLowerCase() === "email_threat" ||
    (alert.title || "").toLowerCase().includes("email")
  );
}

function parseDetail(description: string, prefix: string): string {
  const line = description
    .split("\n")
    .find((row) => row.toLowerCase().startsWith(prefix.toLowerCase()));
  return line ? line.slice(prefix.length).trim() : "";
}

function normalizeRisk(severity: string): "High" | "Medium" | "Low" {
  const value = severity.toLowerCase();
  if (value === "critical" || value === "high") return "High";
  if (value === "medium" || value === "warning") return "Medium";
  return "Low";
}

function riskColor(risk: string) {
  if (risk === "High") return "var(--danger)";
  if (risk === "Medium") return "var(--warning)";
  return "var(--success)";
}

function statusColor(status: string) {
  const s = status.toLowerCase();
  if (s === "resolved") return "var(--success)";
  if (s === "open") return "var(--danger)";
  return "var(--warning)";
}

export default function EmailsPage() {
  const { connected } = useServiceConnected();
  const [emails, setEmails] = useState<EmailAlert[]>([]);
  const [cleared, setCleared] = useState(() => isViewCleared(EMAILS_VIEW_KEY));
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<string>("All");
  const [statusFilter, setStatusFilter] = useState<string>("All");
  const [selected, setSelected] = useState<EmailAlert | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await api.get<EmailAlert[]>("/alerts?limit=200");
        setEmails((Array.isArray(data) ? data : []).filter(isEmailThreat));
      } catch {
        setEmails([]);
      }
    };
    load();
  }, [connected]);

  const riskOptions = useMemo(
    () => ["All", ...Array.from(new Set(emails.map((email) => normalizeRisk(email.severity))))],
    [emails],
  );

  const filtered = (cleared ? [] : emails).filter((email) => {
    const sender = parseDetail(email.description, "From:") || email.title;
    const subject = parseDetail(email.description, "Subject:") || email.description.slice(0, 80);
    const matchSearch =
      search === "" ||
      sender.toLowerCase().includes(search.toLowerCase()) ||
      subject.toLowerCase().includes(search.toLowerCase()) ||
      email.description.toLowerCase().includes(search.toLowerCase());
    const matchRisk = riskFilter === "All" || normalizeRisk(email.severity) === riskFilter;
    const matchStatus = statusFilter === "All" || email.status === statusFilter;
    return matchSearch && matchRisk && matchStatus;
  });

  const mailLive = connected && emails.length > 0 && !cleared;

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3 px-1">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Email Security</h1>
          <p className="text-xs text-muted-foreground">AI-powered phishing detection · live alert feed</p>
        </div>
        <button
          type="button"
          disabled={!connected || (emails.length === 0 && cleared)}
          onClick={() => {
            if (!connected) return;
            
            const confirmed = window.confirm(
              `Are you sure you want to clear all ${emails.length} email threat alert${emails.length !== 1 ? 's' : ''}? This will dismiss them from view.`
            );
            
            if (!confirmed) return;
            
            setViewCleared(EMAILS_VIEW_KEY, true);
            setCleared(true);
            setSelected(null);
          }}
          className="flex items-center gap-1.5 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-3 py-2 text-xs font-medium text-[var(--danger)] transition hover:bg-[var(--danger)]/20 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Trash2 className="h-3.5 w-3.5" /> Clear All
        </button>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <MiniStat icon={<Inbox className="h-5 w-5" />} label="Threat Alerts" value={(cleared ? 0 : emails.length).toString()} color="var(--cyan)" />
        <MiniStat icon={<ShieldAlert className="h-5 w-5" />} label="High Risk" value={(cleared ? 0 : emails.filter((email) => normalizeRisk(email.severity) === "High").length).toString()} color="var(--warning)" />
        <MiniStat icon={<ShieldCheck className="h-5 w-5" />} label="Resolved" value={(cleared ? 0 : emails.filter((email) => email.status === "resolved").length).toString()} color="var(--success)" />
      </div>

      <GlassCard
        title="Email Threat Filter"
        subtitle="Search and filter incoming email scan results"
        icon={<Search className="h-4 w-4 text-[var(--mint)]" />}
      >
        <div className="flex flex-wrap items-center gap-4">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              disabled={!connected}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search sender, subject, or details…"
              className="h-9 w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-3 text-sm placeholder:text-muted-foreground/60 focus:border-[var(--mint)]/50 focus:outline-none focus:ring-1 focus:ring-[var(--mint)]/20 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="shrink-0 font-medium text-muted-foreground">Risk:</span>
            <div className="flex gap-1">
              {riskOptions.map((option) => (
                <FilterBtn
                  key={option}
                  label={option}
                  active={riskFilter === option}
                  disabled={!connected || emails.length === 0}
                  onClick={() => setRiskFilter(option)}
                />
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="shrink-0 font-medium text-muted-foreground">Status:</span>
            <div className="flex gap-1">
              {STATUS_OPTIONS.map((option) => (
                <FilterBtn
                  key={option}
                  label={option}
                  active={statusFilter === option}
                  disabled={!connected || emails.length === 0}
                  onClick={() => setStatusFilter(option)}
                />
              ))}
            </div>
          </div>
        </div>
      </GlassCard>

      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <GlassCard
          title="Incoming Email Scan Results"
          subtitle={`${filtered.length} email${filtered.length !== 1 ? "s" : ""} shown`}
          icon={<ShieldAlert className="h-4 w-4 text-[var(--danger)]" />}
        >
          <div className="overflow-hidden rounded-xl ring-1 ring-white/5">
            <table className="w-full text-left text-xs">
              <thead className="bg-white/5 text-[10px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  <Th>Sender</Th>
                  <Th>Subject</Th>
                  <Th>Risk</Th>
                  <Th>Rule</Th>
                  <Th>Action</Th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">
                      No emails match the current filter.
                    </td>
                  </tr>
                ) : (
                  filtered.map((email) => (
                    <tr
                      key={email.id}
                      onClick={() => connected && emails.length > 0 && setSelected(email)}
                      className={`border-t border-white/5 transition ${
                        connected && emails.length > 0 ? "cursor-pointer hover:bg-white/[0.04]" : "cursor-default opacity-80"
                      } ${selected?.id === email.id ? "bg-white/[0.06] ring-inset ring-1 ring-[var(--mint)]/20" : ""}`}
                    >
                      <Td className="text-muted-foreground">{parseDetail(email.description, "From:") || "—"}</Td>
                      <Td className="font-medium">{parseDetail(email.description, "Subject:") || email.title}</Td>
                      <Td><RiskPill risk={normalizeRisk(email.severity)} /></Td>
                      <Td className="text-muted-foreground">
                        <span className="inline-flex items-center gap-1">
                          <Paperclip className="h-3 w-3 shrink-0" />
                          {email.rule_name || "email_threat"}
                        </span>
                      </Td>
                      <Td><ActionBtn status={email.status} /></Td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </GlassCard>

        <GlassCard
          title="Selected Email Details"
          subtitle={selected ? (parseDetail(selected.description, "From:") || selected.title) : "Click a row to inspect"}
          icon={<Eye className="h-4 w-4 text-[var(--cyan)]" />}
        >
          {selected ? (
            <div className="space-y-3">
              <DetailRow icon={<User2 className="h-3.5 w-3.5" />} label="Sender" value={parseDetail(selected.description, "From:") || "Unknown"} valueColor="var(--muted-foreground)" />
              <DetailRow icon={<Zap className="h-3.5 w-3.5" />} label="Threat Severity" value={selected.severity} valueColor={selected.severity.toLowerCase() === "critical" ? "var(--danger)" : "var(--warning)"} />
              <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent" />
              <DetailRow icon={<AlertTriangle className="h-3.5 w-3.5" />} label="Detection Details" value={selected.description} valueColor="var(--muted-foreground)" />
              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  disabled={!mailLive || !selected}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-semibold ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
                  style={{ color: "var(--danger)", background: "oklch(0.7 0.24 22 / 0.12)", borderColor: "oklch(0.7 0.24 22 / 0.4)" }}
                >
                  <ShieldX className="h-3.5 w-3.5" /> Block
                </button>
                <button
                  type="button"
                  disabled={!mailLive || !selected}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-semibold ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
                  style={{ color: "var(--warning)", background: "oklch(0.84 0.17 80 / 0.12)", borderColor: "oklch(0.84 0.17 80 / 0.4)" }}
                >
                  <ShieldAlert className="h-3.5 w-3.5" /> Quarantine
                </button>
                <button
                  type="button"
                  disabled={!mailLive || !selected}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-semibold ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
                  style={{ color: "var(--success)", background: "oklch(0.86 0.2 165 / 0.12)", borderColor: "oklch(0.86 0.2 165 / 0.4)" }}
                >
                  <ShieldCheck className="h-3.5 w-3.5" /> Allow
                </button>
              </div>
            </div>
          ) : (
            <p className="py-8 text-center text-xs text-muted-foreground">Select an email row to view threat analysis details.</p>
          )}
        </GlassCard>
      </div>
    </div>
  );
}

function RiskPill({ risk }: { risk: string }) {
  const color = riskColor(risk);
  return (
    <span
      className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-semibold ring-1"
      style={{ color, background: `${color}1f`, borderColor: `${color}55` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {risk}
    </span>
  );
}

function ActionBtn({ status }: { status: string }) {
  const color = statusColor(status);
  const s = status.toLowerCase();
  const Icon = s === "resolved" ? ShieldCheck : s === "open" ? ShieldAlert : ShieldX;
  return (
    <span
      className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-semibold ring-1"
      style={{ color, background: `${color}1f`, borderColor: `${color}55` }}
    >
      <Icon className="h-3 w-3" />
      {status}
    </span>
  );
}

function MiniStat({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="glass relative overflow-hidden rounded-3xl p-5 shimmer-border">
      <div className="pointer-events-none absolute inset-x-6 -top-px h-px bg-gradient-to-r from-transparent via-[var(--mint)]/70 to-transparent" />
      <div className="flex h-10 w-10 items-center justify-center rounded-xl ring-1" style={{ background: `${color}18`, color, borderColor: `${color}40` }}>
        {icon}
      </div>
      <div className="mt-3 text-2xl font-bold tabular-nums" style={{ color }}>
        {value}
      </div>
      <div className="mt-0.5 text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

function FilterBtn({
  label,
  active,
  onClick,
  disabled,
}: {
  label: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-all disabled:cursor-not-allowed disabled:opacity-40 ${
        active
          ? "bg-[var(--mint)]/15 text-[var(--mint)] ring-1 ring-[var(--mint)]/30"
          : "bg-white/5 text-muted-foreground hover:bg-white/10 hover:text-foreground"
      }`}
    >
      {label}
      <ChevronDown className="h-3 w-3 opacity-50" />
    </button>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2.5 font-medium">{children}</th>;
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2.5 ${className}`}>{children}</td>;
}

function DetailRow({
  icon,
  label,
  value,
  valueColor,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <div className="glass-strong rounded-xl px-3 py-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground shrink-0">
          <span style={{ color: valueColor }}>{icon}</span>
          {label}
        </div>
        <span className="text-right text-[11px] font-semibold" style={{ color: valueColor }}>
          {value}
        </span>
      </div>
    </div>
  );
}