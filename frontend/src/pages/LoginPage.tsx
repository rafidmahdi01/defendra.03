import { useEffect, useState, type FormEvent } from "react";
import {
  Eye,
  EyeOff,
  HelpCircle,
  KeyRound,
  Lock,
  Mail,
  User,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { AppFooter } from "@/components/defendra/AppFooter";
import { CursorFx } from "@/components/defendra/CursorFx";
import { DefendraLogo } from "@/components/defendra/Logo";
import { Particles } from "@/components/defendra/Particles";
import { api, API_URL } from "@/services/api";
import { notifyAuthChanged } from "@/hooks/useCurrentUser";

type Mode = "login" | "register";

function formatAuthError(err: unknown, apiUrl: string): string {
  const e = err as {
    code?: string;
    name?: string;
    message?: string;
    response?: { status?: number; data?: { detail?: unknown } };
  };
  if (e?.name === "CanceledError" || e?.code === "ERR_CANCELED") {
    return e?.message || "Request was canceled.";
  }
  if (!e?.response) {
    return `Cannot reach the API at ${apiUrl}. Start the backend (for example: npm run backend:dev from the project root), then try again. If you use a custom API URL, set VITE_API_URL.`;
  }
  const detail = e.response.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item: { msg?: string; type?: string }) => item?.msg || JSON.stringify(item))
      .filter(Boolean)
      .join(" ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  if (e.response.status === 401) {
    return "Invalid email or password. If this is a new install, use “bootstrap first admin” below to create the admin account first.";
  }
  return "Request failed. Check your credentials or server logs.";
}

/* ── server connectivity probe ─────────────────────────────────────── */
function useServerStatus() {
  const [status, setStatus] = useState<"checking" | "connected" | "offline" | "no_firebase">("checking");

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      if (!navigator.onLine) { if (!cancelled) setStatus("offline"); return; }
      fetch(`${API_URL}/health`, { method: "GET", signal: AbortSignal.timeout(5000) })
        .then(async (r) => {
          if (cancelled) return;
          if (!r.ok) {
            setStatus("offline");
            return;
          }
          try {
            const body = (await r.json()) as { firebase_configured?: boolean };
            if (body.firebase_configured === false) {
              setStatus("no_firebase");
            } else {
              setStatus("connected");
            }
          } catch {
            setStatus("connected");
          }
        })
        .catch(() => { if (!cancelled) setStatus("offline"); });
    };
    check();
    const id = setInterval(check, 10_000);
    window.addEventListener("online", check);
    window.addEventListener("offline", check);
    return () => {
      cancelled = true;
      clearInterval(id);
      window.removeEventListener("online", check);
      window.removeEventListener("offline", check);
    };
  }, []);

  return status;
}

/* ── main page ──────────────────────────────────────────────────────── */
export default function LoginPage() {
  const navigate = useNavigate();
  const serverStatus = useServerStatus();

  const [mode, setMode] = useState<Mode>("login");
  const [form, setForm] = useState({
    email: "admin@example.com",
    password: "",
    full_name: "Security Admin",
  });
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setInfo("");
    setLoading(true);
    try {
      if (mode === "register") {
        await api.post("/auth/bootstrap-admin", form);
        setInfo("Administrator created. You can now sign in.");
        setMode("login");
      } else {
        const { data } = await api.post("/auth/login", {
          email: form.email,
          password: form.password,
        });
        localStorage.setItem("crps_token", data.access_token);
        localStorage.setItem(
          "crps_user",
          JSON.stringify({
            ...data.user,
            role: data.user?.role || data.role,
          }),
        );
        notifyAuthChanged();
        navigate("/");
      }
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      if (mode === "register" && status === 403) {
        setError(
          typeof detail === "string"
            ? `${detail} Sign in as an admin and create more accounts under Settings.`
            : "Bootstrap only works before any users exist. Sign in as an admin and add accounts under Settings.",
        );
      } else {
        setError(formatAuthError(err, API_URL));
      }
    } finally {
      setLoading(false);
    }
  };

  const forgotPassword = () => {
    setInfo("Contact your system administrator to reset your password.");
  };

  const statusConfig = {
    checking:    { icon: <Wifi className="h-3.5 w-3.5 animate-pulse" />, label: "Checking server…",           dot: "bg-[var(--warning)]" },
    connected:   { icon: <Wifi className="h-3.5 w-3.5" />,               label: "Server connected",            dot: "bg-[var(--success)]" },
    no_firebase: { icon: <Wifi className="h-3.5 w-3.5" />,               label: "API up — needs Firebase config", dot: "bg-[var(--warning)]" },
    offline:     { icon: <WifiOff className="h-3.5 w-3.5" />,             label: "Server offline",               dot: "bg-[var(--danger)]" },
  }[serverStatus];

  return (
    <div className="relative flex min-h-screen flex-col">
      <CursorFx />
      <Particles />

      {/* ── TOP BANNER ─────────────────────────────────────────────── */}
      <header className="glass-strong mx-4 mt-4 rounded-2xl px-6 py-4">
        <div className="flex items-center gap-5">
          <DefendraLogo className="scale-95 sm:scale-100" />

          {/* Right-side shimmer stripe */}
          <div className="ml-auto hidden items-center gap-6 sm:flex">
            <div className="text-right text-xs text-muted-foreground">
              <div className="text-[10px] uppercase tracking-widest text-[var(--mint)]/60">
                Classification
              </div>
              <div className="font-semibold">CONFIDENTIAL</div>
            </div>
            <div className="h-10 w-px bg-gradient-to-b from-transparent via-[var(--mint)]/40 to-transparent" />
            <KeyRound className="h-5 w-5 text-[var(--mint)]/50" />
          </div>
        </div>

        {/* Shimmer line under header */}
        <div className="mt-4 h-px w-full bg-gradient-to-r from-transparent via-[var(--mint)]/50 to-transparent" />
      </header>

      {/* ── CENTRED LOGIN CARD ──────────────────────────────────────── */}
      <main className="flex flex-1 items-center justify-center px-4 py-8">
        <div className="w-full max-w-sm">
          {/* Card glow halo */}
          <div className="pointer-events-none absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--mint)]/10 blur-[100px]" />

          <div className="glass relative overflow-hidden rounded-3xl p-8 shimmer-border">
            {/* Top accent line */}
            <div className="pointer-events-none absolute inset-x-6 -top-px h-px bg-gradient-to-r from-transparent via-[var(--mint)]/80 to-transparent" />

            {/* Card header */}
            <div className="mb-6 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--mint)]/10 ring-1 ring-[var(--mint)]/30">
                <Lock className="h-5 w-5 text-[var(--mint)]" />
              </div>
              <h2 className="text-lg font-semibold tracking-tight">
                {mode === "login" ? "Login Panel" : "Create Administrator"}
              </h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {mode === "login"
                  ? "Secure access · JWT authenticated"
                  : "First-run setup · bootstrap admin account"}
              </p>
            </div>

            <form onSubmit={submit} className="space-y-3">
              {/* Full name (register only) */}
              {mode === "register" && (
                <InputField
                  icon={<User className="h-4 w-4" />}
                  label="Full Name"
                  placeholder="Security Admin"
                  value={form.full_name}
                  onChange={(v) => setForm({ ...form, full_name: v })}
                />
              )}

              {/* Username / email */}
              <InputField
                icon={<Mail className="h-4 w-4" />}
                label="Username"
                type="email"
                placeholder="admin@example.com"
                value={form.email}
                onChange={(v) => setForm({ ...form, email: v })}
              />

              {/* Password */}
              <PasswordInput
                label="Password"
                placeholder="Enter your password"
                autoComplete="current-password"
                value={form.password}
                visible={passwordVisible}
                onToggle={() => setPasswordVisible((v) => !v)}
                onChange={(v) => setForm({ ...form, password: v })}
              />

              {/* Feedback banners */}
              {error && (
                <div className="rounded-xl border border-[var(--danger)]/40 bg-[var(--danger)]/10 px-3 py-2 text-xs text-[var(--danger)]">
                  {error}
                </div>
              )}
              {info && (
                <div className="rounded-xl border border-[var(--success)]/40 bg-[var(--success)]/10 px-3 py-2 text-xs text-[var(--success)]">
                  {info}
                </div>
              )}

              {/* Login button */}
              <button
                type="submit"
                disabled={loading}
                className="relative mt-1 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-gradient-cyber font-semibold text-primary-foreground transition-all hover:brightness-110 disabled:opacity-60 glow-blue"
              >
                {loading ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground" />
                ) : (
                  <Lock className="h-4 w-4" />
                )}
                {loading ? "Processing…" : mode === "login" ? "Login" : "Create Administrator"}
              </button>

              {/* Forgot Password (login mode only) */}
              {mode === "login" && (
                <button
                  type="button"
                  onClick={forgotPassword}
                  className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-white/10 bg-white/5 py-2.5 text-xs font-medium text-muted-foreground transition hover:bg-white/10 hover:text-foreground"
                >
                  <HelpCircle className="h-3.5 w-3.5" />
                  Forgot Password
                </button>
              )}

              {/* Divider */}
              <div className="flex items-center gap-3 py-1">
                <div className="flex-1 border-t border-white/5" />
                <span className="text-[10px] uppercase tracking-widest text-muted-foreground/50">or</span>
                <div className="flex-1 border-t border-white/5" />
              </div>

              {mode === "login" ? (
                <p className="text-center text-xs text-muted-foreground">
                  Need to add a user?{" "}
                  <Link
                    to="/register"
                    className="font-semibold text-[var(--mint)] transition hover:underline"
                  >
                    Create Account
                  </Link>
                </p>
              ) : (
                <button
                  type="button"
                  onClick={() => { setMode("login"); setError(""); setInfo(""); }}
                  className="w-full text-center text-xs text-muted-foreground transition hover:text-[var(--mint)]"
                >
                  ← Back to sign in
                </button>
              )}

              {mode === "login" ? (
                <button
                  type="button"
                  onClick={() => { setMode("register"); setError(""); setInfo(""); }}
                  className="w-full text-center text-[10px] text-muted-foreground/70 transition hover:text-[var(--mint)]"
                >
                  First run only — bootstrap first admin →
                </button>
              ) : null}
            </form>
          </div>
        </div>
      </main>

      <AppFooter />

      {/* ── BOTTOM STATUS BAR ──────────────────────────────────────── */}
      <footer className="glass-strong mx-4 mb-4 rounded-2xl px-5 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Status indicator */}
          <div className="flex items-center gap-2 text-muted-foreground">
            <span
              className={`h-2 w-2 rounded-full ${statusConfig.dot} ${
                serverStatus === "connected" ? "animate-pulse-glow" : ""
              }`}
            />
            <span className="flex items-center gap-1.5 font-medium text-foreground">
              {statusConfig.icon}
              {statusConfig.label}
            </span>
          </div>

          {/* Middle: breadcrumb-style states */}
          <div className="hidden items-center gap-2 text-muted-foreground sm:flex">
            <StatusChip
              label="Server Connected"
              active={serverStatus === "connected"}
              color="var(--success)"
            />
            <span className="text-white/20">/</span>
            <StatusChip
              label="Offline"
              active={serverStatus === "offline"}
              color="var(--danger)"
            />
            <span className="text-white/20">/</span>
            <StatusChip
              label="Sync Pending"
              active={false}
              color="var(--warning)"
            />
          </div>

          {/* Right: API endpoint */}
          <div className="text-[10px] tabular-nums text-muted-foreground/60">
            API: {API_URL}
          </div>
        </div>
      </footer>
    </div>
  );
}

/* ── sub-components ─────────────────────────────────────────────────── */

function InputField({
  icon,
  label,
  type = "text",
  placeholder,
  value,
  onChange,
}: {
  icon: React.ReactNode;
  label: string;
  type?: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </label>
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
          {icon}
        </span>
        <input
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-11 w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-4 text-sm placeholder:text-muted-foreground/50 focus:border-[var(--electric)]/50 focus:outline-none focus:ring-2 focus:ring-[var(--electric)]/20"
        />
      </div>
    </div>
  );
}

function PasswordInput({
  label,
  placeholder,
  value,
  visible,
  onToggle,
  onChange,
  autoComplete,
}: {
  label: string;
  placeholder: string;
  value: string;
  visible: boolean;
  onToggle: () => void;
  onChange: (v: string) => void;
  autoComplete?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </label>
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
          <Lock className="h-4 w-4" />
        </span>
        <input
          type="text"
          name="password"
          autoComplete={autoComplete}
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          data-lpignore="true"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`h-11 w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-10 text-sm placeholder:text-muted-foreground/50 focus:border-[var(--electric)]/50 focus:outline-none focus:ring-2 focus:ring-[var(--electric)]/20 ${
            visible ? "" : "password-masked"
          }`}
        />
        <button
          type="button"
          tabIndex={-1}
          onMouseDown={(e) => e.preventDefault()}
          onClick={onToggle}
          aria-label={visible ? "Hide password" : "Show password"}
          aria-pressed={visible}
          className="absolute right-3 top-1/2 z-10 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          {visible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

function StatusChip({
  label,
  active,
  color,
}: {
  label: string;
  active: boolean;
  color: string;
}) {
  return (
    <span
      className="flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-medium ring-1 transition"
      style={
        active
          ? { color, background: `${color}20`, borderColor: `${color}55` }
          : { color: "oklch(0.72 0.03 250)", background: "transparent", borderColor: "oklch(1 0 0 / 0.05)" }
      }
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: active ? color : "oklch(0.72 0.03 250 / 0.4)" }}
      />
      {label}
    </span>
  );
}
