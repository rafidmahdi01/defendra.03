import logoSrc from "@/assets/defendra-logo.png";

export function DefendraLogo({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="relative">
        <div className="absolute inset-0 rounded-xl bg-[var(--mint)]/40 blur-xl opacity-80" />
        <img
          src={logoSrc}
          alt="Defendra.AI logo"
          loading="lazy"
          width={56}
          height={56}
          className="relative h-14 w-14 rounded-xl object-cover ring-1 ring-[var(--mint)]/40"
        />
      </div>
      <div className="flex flex-col leading-none">
        <span className="text-2xl font-bold tracking-tight text-gradient-cyber">
          Defendra.AI
        </span>
      </div>
    </div>
  );
}