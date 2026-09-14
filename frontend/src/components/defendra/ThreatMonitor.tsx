import { Radar, ArrowUpRight } from "lucide-react";
import { GlassCard } from "./Card";
import { useTelemetry } from "@/hooks/useTelemetry";

const toneColor = {
  danger: "text-[var(--danger)]",
  success: "text-[var(--success)]",
  info: "text-[var(--cyan)]",
};

type Tone = "danger" | "success" | "info";

function pctDelta(arr: number[]): string {
  if (arr.length < 2) return "0%";
  const a = arr[arr.length - 2];
  const b = arr[arr.length - 1];
  if (!a) return "0%";
  const d = ((b - a) / a) * 100;
  return `${d >= 0 ? "+" : ""}${d.toFixed(1)}%`;
}

export function ThreatMonitor() {
  const t = useTelemetry();
  const riskLabel = t.riskScore < 25 ? "Low" : t.riskScore < 50 ? "Moderate" : t.riskScore < 70 ? "High" : "Critical";
  const stats: { label: string; value: string; delta: string; tone: Tone; data: number[] }[] = [
    { label: "Active Threats", value: String(t.activeThreats), delta: pctDelta(t.spark.danger), tone: "danger", data: t.spark.danger },
    { label: "Blocked / 24h", value: t.blocked24h.toLocaleString(), delta: pctDelta(t.spark.success), tone: "success", data: t.spark.success },
    { label: "Mean Response", value: `${(t.meanResponseSec / 60).toFixed(1)}m`, delta: pctDelta(t.spark.info), tone: "success", data: t.spark.info },
    { label: "Risk Score", value: riskLabel, delta: `${t.riskScore}/100`, tone: "info", data: t.spark.purple },
  ];
  return (
    <GlassCard
      title="Real-Time Threat Monitor"
      subtitle="Global telemetry · last 60 minutes"
      icon={<Radar className="h-4 w-4 text-[var(--cyan)]" />}
      action={
        <span className="flex items-center gap-1.5 rounded-full bg-[var(--success)]/10 px-2.5 py-1 text-[10px] font-medium text-[var(--success)] ring-1 ring-[var(--success)]/30">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)] animate-pulse-glow" />
          LIVE
        </span>
      }
    >
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4 lg:gap-0">
        {stats.map((s, i) => (
          <div
            key={s.label}
            className={`group/stat relative flex cursor-pointer flex-col justify-between rounded-2xl px-4 py-3 transition-all duration-300 hover:-translate-y-1 hover:bg-[var(--mint)]/5 hover:shadow-[0_18px_40px_-12px_var(--mint)] hover:ring-1 hover:ring-[var(--mint)]/40 ${
              i > 0 ? "lg:before:absolute lg:before:inset-y-3 lg:before:left-0 lg:before:w-px lg:before:bg-gradient-to-b lg:before:from-transparent lg:before:via-[var(--mint)]/30 lg:before:to-transparent" : ""
            }`}
          >
            <div className="truncate text-xs font-medium text-muted-foreground transition-colors group-hover/stat:text-[var(--mint)]">{s.label}</div>
            <div className="mt-1 text-2xl font-semibold leading-tight tracking-tight tabular-nums transition-transform duration-300 group-hover/stat:scale-105 group-hover/stat:[text-shadow:0_0_24px_var(--mint)] sm:text-3xl">
              {s.value}
            </div>
            <div className={`mt-2 flex items-center gap-1 text-[11px] ${toneColor[s.tone]}`}>
              <span
                className="flex h-4 w-4 items-center justify-center rounded-full"
                style={{ background: "currentColor", color: "currentColor" }}
              >
                <ArrowUpRight className="h-2.5 w-2.5 text-black" />
              </span>
              <span className="font-medium">{s.delta}</span>
            </div>
            <div className="pointer-events-none absolute inset-x-3 -top-2 mx-auto w-fit translate-y-1 rounded-md bg-[var(--mint)] px-2 py-0.5 text-[10px] font-semibold text-black opacity-0 shadow-[0_0_18px_var(--mint)] transition-all duration-300 group-hover/stat:-translate-y-2 group-hover/stat:opacity-100">
              {s.label} · live
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}
