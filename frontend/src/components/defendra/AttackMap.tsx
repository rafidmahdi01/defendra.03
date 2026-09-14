import { Globe2 } from "lucide-react";
import { GlassCard } from "./Card";
import { useTelemetry } from "@/hooks/useTelemetry";

const levelColor = (l: string) =>
  l === "high" ? "var(--danger)" : l === "med" ? "var(--warning)" : "var(--cyan)";

export function AttackMap() {
  const { geo: points } = useTelemetry();
  const hot = [...points].sort((a, b) => b.intensity - a.intensity).slice(0, 5);
  return (
    <GlassCard
      title="Live Attack Heatmap"
      subtitle="Origin of inbound threats · realtime"
      icon={<Globe2 className="h-4 w-4 text-[var(--electric)]" />}
      className="h-full"
      action={
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <Legend color="var(--danger)" label="Critical" />
          <Legend color="var(--warning)" label="Elevated" />
          <Legend color="var(--cyan)" label="Low" />
        </div>
      }
    >
      <div className="relative h-72 w-full overflow-hidden rounded-xl bg-gradient-to-b from-white/[0.02] to-transparent ring-1 ring-white/5">
        <div className="absolute inset-0 opacity-30" style={{
          backgroundImage: "radial-gradient(circle at 1px 1px, oklch(0.85 0.16 200 / 0.5) 1px, transparent 0)",
          backgroundSize: "12px 12px",
          maskImage: "radial-gradient(ellipse 70% 60% at 50% 50%, #000 40%, transparent 100%)",
        }} />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-12 bg-gradient-to-b from-[var(--cyan)]/10 to-transparent animate-scan" />
        <svg viewBox="0 0 100 70" className="absolute inset-0 h-full w-full">
          {points.map((p, i) => (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r={0.4 + p.intensity * 0.7} fill={levelColor(p.level)} style={{ transition: "all 0.8s ease" }} />
              <circle cx={p.x} cy={p.y} r={1 + p.intensity * 1.5} fill={levelColor(p.level)} opacity={0.2 + p.intensity * 0.4}>
                <animate attributeName="r" values={`${1 + p.intensity};${2.5 + p.intensity * 2};${1 + p.intensity}`} dur={`${1.6 + (1 - p.intensity) * 1.4}s`} repeatCount="indefinite" begin={`${i * 0.2}s`} />
                <animate attributeName="opacity" values="0.6;0;0.6" dur={`${1.6 + (1 - p.intensity) * 1.4}s`} repeatCount="indefinite" begin={`${i * 0.2}s`} />
              </circle>
            </g>
          ))}
          {[
            [points[3], points[2]],
            [points[7], points[3]],
            [points[6], points[2]],
            [points[8], points[1]],
          ].map(([a, b], i) => (
            <line
              key={i}
              x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke="var(--electric)" strokeWidth="0.2" strokeDasharray="1 1" opacity="0.6"
            />
          ))}
        </svg>
        <div className="absolute bottom-3 left-3 right-3 flex flex-wrap gap-1.5">
          {hot.map((p) => (
            <span key={p.label} className="rounded-md bg-white/5 px-2 py-0.5 text-[10px] ring-1 ring-white/10" style={{ color: levelColor(p.level) }}>
              {p.label} · {Math.round(p.intensity * 100)}
            </span>
          ))}
        </div>
      </div>
    </GlassCard>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1">
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color, boxShadow: `0 0 6px ${color}` }} />
      {label}
    </span>
  );
}