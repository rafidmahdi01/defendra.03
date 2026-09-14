import { useMemo, useState, type FormEvent } from "react";
import {
  Eye,
  EyeOff,
  Lock,
  Mail,
  Shield,
  User,
  UserPlus,
} from "lucide-react";
import { Link } from "react-router-dom";

import { AppFooter } from "@/components/defendra/AppFooter";
import { CursorFx } from "@/components/defendra/CursorFx";
import { DefendraLogo } from "@/components/defendra/Logo";
import { Particles } from "@/components/defendra/Particles";
import { isAdminRole, readStoredUser } from "@/hooks/useCurrentUser";
import { api } from "@/services/api";

type FieldErrors = {
  full_name?: string;
  email?: string;
  password?: string;
  confirm_password?: string;
  role?: string;
  form?: string;
};

type PasswordStrength = "empty" | "weak" | "fair" | "good" | "strong";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function scorePassword(password: string): PasswordStrength {
  if (!password) return "empty";
  let score = 0;
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;
  if (score <= 2) return "weak";
  if (score === 3) return "fair";
  if (score === 4) return "good";
  return "strong";
}

const STRENGTH_META: Record<
  Exclude<PasswordStrength, "empty">,
  { label: string; width: string; color: string }
> = {
  weak: { label: "Weak", width: "25%", color: "var(--danger)" },
  fair: { label: "Fair", width: "50%", color: "var(--warning)" },
  good: { label: "Good", width: "75%", color: "var(--electric)" },
  strong: { label: "Strong", width: "100%", color: "var(--success)" },
};

function formatRegisterError(err: unknown): string {
  const e = err as { response?: { data?: { detail?: unknown }; status?: number } };
  const detail = e.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item: { msg?: string }) => item?.msg)
      .filter(Boolean)
      .join(" ");
  }
  if (e.response?.status === 409) {
    return "This email is already registered. Try logging in instead.";
  }
  return "Registration failed. Please try again.";
}

export default function RegisterPage() {
  const isAdmin = isAdminRole(readStoredUser().role);

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    confirm_password: "",
    role: "user" as "user" | "admin",
  });
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  const strength = useMemo(() => scorePassword(form.password), [form.password]);

  const validate = (values = form): FieldErrors => {
    const errors: FieldErrors = {};
    const name = values.full_name.trim();
    const email = values.email.trim();

    if (!name) {
      errors.full_name = "Full name is required.";
    } else if (name.length < 2) {
      errors.full_name = "Full name must be at least 2 characters.";
    }

    if (!email) {
      errors.email = "Email address is required.";
    } else if (!EMAIL_RE.test(email)) {
      errors.email = "Enter a valid email address.";
    }

    if (!values.password) {
      errors.password = "Password is required.";
    } else if (values.password.length < 8) {
      errors.password = "Password must be at least 8 characters.";
    }

    if (!values.confirm_password) {
      errors.confirm_password = "Please confirm your password.";
    } else if (values.password !== values.confirm_password) {
      errors.confirm_password = "Passwords do not match.";
    }

    if (!values.role) {
      errors.role = "Select a role.";
    }

    return errors;
  };

  const touch = (field: string) =>
    setTouched((t) => ({ ...t, [field]: true }));

  const showError = (field: keyof FieldErrors) =>
    touched[field] ? fieldErrors[field] : undefined;

  const handleBlur = (field: keyof typeof form) => {
    touch(field);
    setFieldErrors(validate());
  };

  const handleChange = (field: keyof typeof form, value: string) => {
    const next = { ...form, [field]: value };
    setForm(next);
    if (touched[field] || field === "confirm_password") {
      setFieldErrors(validate(next));
    }
    if (success) setSuccess("");
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSuccess("");
    setTouched({
      full_name: true,
      email: true,
      password: true,
      confirm_password: true,
      role: true,
    });

    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setLoading(true);
    try {
      await api.post("/auth/register", {
        email: form.email.trim(),
        full_name: form.full_name.trim(),
        password: form.password,
        role: form.role,
      });
      setSuccess(`Account created successfully for ${form.email.trim()}. You can now log in.`);
      setForm({
        full_name: "",
        email: "",
        password: "",
        confirm_password: "",
        role: "user",
      });
      setTouched({});
      setFieldErrors({});
    } catch (err) {
      setFieldErrors({ form: formatRegisterError(err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen flex-col">
      <CursorFx />
      <Particles />

      <header className="glass-strong mx-4 mt-4 rounded-2xl px-6 py-4">
        <div className="flex items-center gap-5">
          <DefendraLogo className="scale-95 sm:scale-100" />
        </div>
        <div className="mt-4 h-px w-full bg-gradient-to-r from-transparent via-[var(--mint)]/50 to-transparent" />
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-8">
        <div className="relative w-full max-w-md">
          <div className="pointer-events-none absolute left-1/2 top-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--mint)]/10 blur-[100px]" />

          <div className="glass relative overflow-hidden rounded-3xl p-6 sm:p-8 shimmer-border">
            <div className="pointer-events-none absolute inset-x-6 -top-px h-px bg-gradient-to-r from-transparent via-[var(--mint)]/80 to-transparent" />

            <div className="mb-6 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--mint)]/10 ring-1 ring-[var(--mint)]/30">
                <UserPlus className="h-5 w-5 text-[var(--mint)]" />
              </div>
              <h2 className="text-lg font-semibold tracking-tight">Create Account</h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Sign up for your Defendra dashboard account
              </p>
            </div>

            {success ? (
              <div className="mb-4 rounded-xl border border-[var(--success)]/40 bg-[var(--success)]/10 px-3 py-2 text-xs text-[var(--success)]">
                {success}
              </div>
            ) : null}

            {fieldErrors.form ? (
              <div className="mb-4 rounded-xl border border-[var(--danger)]/40 bg-[var(--danger)]/10 px-3 py-2 text-xs text-[var(--danger)]">
                {fieldErrors.form}
              </div>
            ) : null}

            <form onSubmit={submit} className="space-y-4" noValidate>
              <Field
                icon={<User className="h-4 w-4" />}
                label="Full Name"
                name="full_name"
                placeholder="Jane Doe"
                value={form.full_name}
                error={showError("full_name")}
                onBlur={() => handleBlur("full_name")}
                onChange={(v) => handleChange("full_name", v)}
              />

              <Field
                icon={<Mail className="h-4 w-4" />}
                label="Email Address"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="user@company.com"
                value={form.email}
                error={showError("email")}
                onBlur={() => handleBlur("email")}
                onChange={(v) => handleChange("email", v)}
              />

              <div>
                <Field
                  icon={<Lock className="h-4 w-4" />}
                  label="Password"
                  name="password"
                  type="text"
                  masked={!showPassword}
                  autoComplete="new-password"
                  placeholder="Min. 8 characters"
                  value={form.password}
                  error={showError("password")}
                  onBlur={() => handleBlur("password")}
                  onChange={(v) => handleChange("password", v)}
                  trailing={
                    <button
                      type="button"
                      tabIndex={-1}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => setShowPassword((s) => !s)}
                      className="absolute right-3 top-1/2 z-10 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      aria-pressed={showPassword}
                    >
                      {showPassword ? (
                        <Eye className="h-4 w-4" />
                      ) : (
                        <EyeOff className="h-4 w-4" />
                      )}
                    </button>
                  }
                />
                {form.password ? (
                  <div className="mt-2 space-y-1">
                    <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{
                          width:
                            strength === "empty"
                              ? "0%"
                              : STRENGTH_META[strength].width,
                          background:
                            strength === "empty"
                              ? "transparent"
                              : STRENGTH_META[strength].color,
                        }}
                      />
                    </div>
                    {strength !== "empty" ? (
                      <p
                        className="text-[10px] font-medium"
                        style={{ color: STRENGTH_META[strength].color }}
                      >
                        Password strength: {STRENGTH_META[strength].label}
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>

              <Field
                icon={<Lock className="h-4 w-4" />}
                label="Confirm Password"
                name="confirm_password"
                type="text"
                masked={!showPassword}
                autoComplete="new-password"
                placeholder="Re-enter password"
                value={form.confirm_password}
                error={showError("confirm_password")}
                onBlur={() => handleBlur("confirm_password")}
                onChange={(v) => handleChange("confirm_password", v)}
              />

              <div>
                <label
                  htmlFor="role"
                  className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground"
                >
                  Role
                </label>
                <div className="relative">
                  <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                    <Shield className="h-4 w-4" />
                  </span>
                  <select
                    id="role"
                    name="role"
                    value={form.role}
                    onBlur={() => handleBlur("role")}
                    onChange={(e) =>
                      handleChange("role", e.target.value as "user" | "admin")
                    }
                    className={`h-11 w-full appearance-none rounded-xl border bg-white/5 pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--electric)]/20 ${
                      showError("role")
                        ? "border-[var(--danger)]/50 focus:border-[var(--danger)]/50"
                        : "border-white/10 focus:border-[var(--electric)]/50"
                    }`}
                  >
                    <option value="user" className="bg-[#111]">
                      User
                    </option>
                    {isAdmin ? (
                      <option value="admin" className="bg-[#111]">
                        Admin
                      </option>
                    ) : null}
                  </select>
                </div>
                {showError("role") ? (
                  <p className="mt-1 text-[11px] text-[var(--danger)]">{fieldErrors.role}</p>
                ) : null}
              </div>

              <button
                type="submit"
                disabled={loading}
                className="mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-gradient-cyber font-semibold text-primary-foreground transition-all hover:brightness-110 disabled:opacity-60 glow-blue"
              >
                {loading ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground" />
                ) : (
                  <UserPlus className="h-4 w-4" />
                )}
                {loading ? "Creating…" : "Create Account"}
              </button>

              <p className="pt-1 text-center text-xs text-muted-foreground">
                Already have an account?{" "}
                <Link
                  to="/login"
                  className="font-semibold text-[var(--mint)] transition hover:underline"
                >
                  Login
                </Link>
              </p>
            </form>
          </div>
        </div>
      </main>

      <AppFooter />
    </div>
  );
}

function Field({
  icon,
  label,
  name,
  type = "text",
  placeholder,
  value,
  error,
  onChange,
  onBlur,
  autoComplete,
  trailing,
  masked,
}: {
  icon: React.ReactNode;
  label: string;
  name: string;
  type?: string;
  placeholder: string;
  value: string;
  error?: string;
  onChange: (v: string) => void;
  onBlur: () => void;
  autoComplete?: string;
  trailing?: React.ReactNode;
  masked?: boolean;
}) {
  return (
    <div>
      <label
        htmlFor={name}
        className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground"
      >
        {label}
      </label>
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
          {icon}
        </span>
        <input
          id={name}
          name={name}
          type={masked !== undefined ? "text" : type}
          autoComplete={autoComplete}
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          placeholder={placeholder}
          value={value}
          onBlur={onBlur}
          onChange={(e) => onChange(e.target.value)}
          className={`h-11 w-full rounded-xl border bg-white/5 pl-9 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-[var(--electric)]/20 ${
            trailing ? "pr-10" : "pr-4"
          } ${masked ? "password-masked" : ""} ${
            error
              ? "border-[var(--danger)]/50 focus:border-[var(--danger)]/50"
              : "border-white/10 focus:border-[var(--electric)]/50"
          }`}
        />
        {trailing}
      </div>
      {error ? <p className="mt-1 text-[11px] text-[var(--danger)]">{error}</p> : null}
    </div>
  );
}
