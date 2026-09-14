import type { ReactNode } from "react";

export function GlassCard({
  children,
  className = "",
  title,
  subtitle,
  icon,
  action,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className={`glass group relative overflow-hidden rounded-3xl p-5 transition-all hover:border-[var(--mint)]/40 ${className}`}>
      <div className="pointer-events-none absolute inset-x-6 -top-px h-px bg-gradient-to-r from-transparent via-[var(--mint)]/70 to-transparent" />
      <div className="pointer-events-none absolute -inset-px rounded-3xl opacity-0 transition-opacity duration-500 group-hover:opacity-100"
        style={{ boxShadow: "0 0 0 1px var(--mint), 0 0 32px -8px var(--mint)" }}
      />
      {(title || icon) && (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            {icon && (
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--mint)]/10 ring-1 ring-[var(--mint)]/30 text-[var(--mint)]">
                {icon}
              </div>
            )}
            <div>
              {title && <div className="text-sm font-semibold tracking-tight">{title}</div>}
              {subtitle && <div className="text-[11px] text-muted-foreground">{subtitle}</div>}
            </div>
          </div>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}