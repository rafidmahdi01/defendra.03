import { ArrowDownRight, ArrowUpRight, LineChart } from "lucide-react";

import { GlassCard } from "./Card";
import { useTelemetry } from "@/hooks/useTelemetry";

export function AnalyticsChart() {
  const { trends, overview } = useTelemetry();

  const alertsSeries = trends.map((p) => p.alerts);
  const logsSeries = trends.map((p) => p.logs);

  const totalEvents = trends.reduce((s, p) => s + p.alerts + p.logs, 0);
  const fallbackTotal = overview.logs_today + overview.critical_alerts;
  const totalDisplay = (totalEvents > 0 ? totalEvents : fallbackTotal).toLocaleString();

  let pct: number | null = null;
  if (trends.length >= 2) {
    const mid = Math.floor(trends.length / 2);
    const first = trends.slice(0, mid).reduce((s, p) => s + p.alerts + p.logs, 0);
    const second = trends.slice(mid).reduce((s, p) => s + p.alerts + p.logs, 0);
    if (first > 0) pct = Math.round(((second - first) / first) * 1000) / 10;
    else if (second > 0) pct = 100;
    else pct = 0;
  }

  const cyan = "#22d3ee";
  const magenta = "#ec4899";
  const series = [
    { name: "Alerts", color: cyan, data: alertsSeries.length ? alertsSeries : [0] },
    { name: "Logs", color: magenta, data: logsSeries.length ? logsSeries : [0] },
  ];

  const dataMax = Math.max(1, ...series.flatMap((s) => s.data));
  const toPct = (v: number) => Math.max(4, Math.min(98, (v / dataMax) * 100));

  const sample = (arr: number[], n = 8) => {
    if (arr.length <= 1) return Array.from({ length: n }, () => arr[0] ?? 0);
    const out: number[] = [];
    for (let i = 0; i < n; i++) {
      const idx = Math.round((i / (n - 1)) * (arr.length - 1));
      out.push(arr[idx]);
    }
    return out;
  };

  const sampleLabels = (labels: string[], n: number) => {
    if (!labels.length) return Array.from({ length: n }, (_, i) => String(i + 1));
    const out: string[] = [];
    for (let i = 0; i < n; i++) {
      const idx = Math.round((i / Math.max(1, n - 1)) * (labels.length - 1));
      out.push(labels[idx] ?? "—");
    }
    return out;
  };

  const w = 100;
  const h = 50;
  const pad = { l: 9, r: 3, t: 3, b: 6 };
  const iw = w - pad.l - pad.r;
  const ih = h - pad.t - pad.b;

  const yTicks = [100, 80, 60, 40, 20, 0];
  const nPts = 8;
  const xLabels = sampleLabels(trends.map((p) => p.label), nPts);

  return (
    <GlassCard
      title="Threat Analytics"
      subtitle="Alerts & log volume · last 7 days (fleet)"
      icon={<LineChart className="h-4 w-4" />}
      action={
        <div className="flex gap-3 text-[10px] text-muted-foreground">
          {series.map((s) => (
            <span key={s.name} className="flex items-center gap-1.5">
              <span
                className="h-1.5 w-3 rounded-full"
                style={{ background: s.color, boxShadow: `0 0 8px ${s.color}` }}
              />
              {s.name}
            </span>
          ))}
        </div>
      }
    >
      <div className="mb-3">
        <div className="text-3xl font-semibold tracking-tight tabular-nums">{totalDisplay}</div>
        <div className="mt-0.5 flex items-center gap-1.5 text-xs">
          {pct !== null ? (
            <>
              <span
                className={`flex h-4 w-4 items-center justify-center rounded-full ${pct >= 0 ? "bg-[var(--mint)]" : "bg-[var(--danger)]/80"}`}
              >
                {pct >= 0 ? (
                  <ArrowUpRight className="h-2.5 w-2.5 text-black" />
                ) : (
                  <ArrowDownRight className="h-2.5 w-2.5 text-white" />
                )}
              </span>
              <span className={pct >= 0 ? "font-medium text-[var(--mint)]" : "font-medium text-[var(--danger)]"}>
                {pct > 0 ? "+" : ""}
                {pct}%
              </span>
              <span className="text-muted-foreground">vs prior half of window</span>
            </>
          ) : (
            <span className="text-muted-foreground">Collecting trend data…</span>
          )}
        </div>
      </div>
      <div className="relative h-64">
        <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="h-full w-full overflow-visible">
          <defs>
            {series.map((s, i) => (
              <linearGradient id={`fill-${i}`} key={i} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={s.color} stopOpacity="0.45" />
                <stop offset="100%" stopColor={s.color} stopOpacity="0" />
              </linearGradient>
            ))}
            <filter id="line-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="0.35" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {yTicks.map((_, i) => {
            const y = pad.t + (i / (yTicks.length - 1)) * ih;
            return (
              <line
                key={`h${i}`}
                x1={pad.l}
                x2={pad.l + iw}
                y1={y}
                y2={y}
                stroke="oklch(1 0 0 / 0.06)"
                strokeWidth="0.15"
              />
            );
          })}
          {xLabels.map((_, i) => {
            const x = pad.l + (i / (xLabels.length - 1)) * iw;
            return (
              <line
                key={`v${i}`}
                x1={x}
                x2={x}
                y1={pad.t}
                y2={pad.t + ih}
                stroke="oklch(1 0 0 / 0.06)"
                strokeWidth="0.15"
              />
            );
          })}

          {series.map((s, i) => {
            const sampled = sample(s.data, xLabels.length);
            const pts = sampled.map((d, idx) => ({
              x: pad.l + (idx / (xLabels.length - 1)) * iw,
              y: pad.t + ih - (toPct(d) / 100) * ih,
            }));
            const lineD = pts.map((p, idx) => `${idx === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
            const areaD = `${lineD} L ${pts[pts.length - 1].x} ${pad.t + ih} L ${pts[0].x} ${pad.t + ih} Z`;
            return (
              <g key={i}>
                <path d={areaD} fill={`url(#fill-${i})`} style={{ transition: "all 0.6s ease" }} />
                <path
                  d={lineD}
                  fill="none"
                  stroke={s.color}
                  strokeWidth="0.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  filter="url(#line-glow)"
                  style={{ transition: "all 0.6s ease" }}
                />
                {pts.map((p, idx) => (
                  <g key={idx}>
                    <circle cx={p.x} cy={p.y} r="0.9" fill={s.color} style={{ filter: `drop-shadow(0 0 2px ${s.color})` }} />
                    <circle cx={p.x} cy={p.y} r="0.4" fill="#0a0a0a" />
                  </g>
                ))}
              </g>
            );
          })}
        </svg>

        <div className="pointer-events-none absolute left-0 top-0 flex h-[calc(100%-1.25rem)] w-7 flex-col justify-between py-[0.6rem] text-[9px] tabular-nums text-muted-foreground/70">
          {yTicks.map((v) => (
            <span key={v}>{v}</span>
          ))}
        </div>
        <div className="absolute inset-x-0 bottom-1 ml-7 mr-2 flex justify-between gap-0.5 text-[9px] font-medium tracking-tight text-muted-foreground/70">
          {xLabels.map((l) => (
            <span key={l} className="max-w-[2.5rem] truncate text-center">
              {l}
            </span>
          ))}
        </div>
      </div>
    </GlassCard>
  );
}
