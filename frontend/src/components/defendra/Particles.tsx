import { memo } from "react";

export const Particles = memo(function Particles() {
  const dots = Array.from({ length: 12 });
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute -left-32 -top-20 h-[520px] w-[520px] rounded-full bg-[var(--mint)]/20 blur-[160px]" />
      <div className="absolute right-[-80px] top-1/4 h-[460px] w-[460px] rounded-full bg-[var(--purple)]/20 blur-[160px]" />
      <div className="absolute inset-0 opacity-[0.4] mix-blend-screen"
        style={{ background: "radial-gradient(ellipse at 50% -10%, oklch(0.86 0.2 165 / 0.15), transparent 55%)" }}
      />
      {dots.map((_, i) => {
        const left = (i * 137) % 100;
        const top = (i * 53) % 100;
        return (
          <span
            key={i}
            className="absolute h-1 w-1 rounded-full bg-white/30 animate-float-slow"
            style={{
              left: `${left}%`,
              top: `${top}%`,
              animationDelay: `${(i % 6) * 0.8}s`,
            }}
          />
        );
      })}
      <div className="absolute inset-0 opacity-[0.05]" style={{
        backgroundImage: "linear-gradient(oklch(0.86 0.2 165 / 0.4) 1px, transparent 1px), linear-gradient(90deg, oklch(0.86 0.2 165 / 0.4) 1px, transparent 1px)",
        backgroundSize: "96px 96px",
        maskImage: "radial-gradient(ellipse at 50% 40%, black 30%, transparent 75%)",
        WebkitMaskImage: "radial-gradient(ellipse at 50% 40%, black 30%, transparent 75%)",
      }} />
    </div>
  );
});
