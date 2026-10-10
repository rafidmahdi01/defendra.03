import { type FormEvent, useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Shield,
  Wifi,
  WifiOff,
  UserPlus,
  Users,
  ScrollText,
  Bell,
  Server,
  Check,
  KeyRound,
  ShieldCheck,
  Mail,
  Save,
} from "lucide-react";
import { GlassCard } from "@/components/defendra/Card";
import { useConnectivitySync } from "@/hooks/useConnectivitySync";
import { formatRelative } from "@/hooks/useTelemetry";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useServiceConnected } from "@/hooks/useServiceConnected";
import { api } from "@/services/api";

type PolicyKey =
  | "autoReconnectWifi"
  | "scanEmailBeforeOpening"
  | "blockUnknownUsb"
  | "enableAutomaticBackup"
  | "enableLimpModeRecovery"
  | "isolateInfectedDevice";

type Policies = Record<PolicyKey, boolean>;

const POLICY_LABELS: { key: PolicyKey; label: string }[] = [
  { key: "autoReconnectWifi", label: "WiFi toggle" },
  { key: "scanEmailBeforeOpening", label: "Email scan" },
  { key: "blockUnknownUsb", label: "USB block" },
  { key: "enableAutomaticBackup", label: "Backup" },
  { key: "enableLimpModeRecovery", label: "Recovery" },
  { key: "isolateInfectedDevice", label: "Isolation" },
];

const DEFAULT_POLICIES: Policies = {
  autoReconnectWifi: true,
  scanEmailBeforeOpening: true,
  blockUnknownUsb: true,
  enableAutomaticBackup: false,
  enableLimpModeRecovery: false,
  isolateInfectedDevice: false,
};

const HARDENING_ITEMS = [
  "Rotate JWT Secret",
  "Restrict CORS",
  "Enable TLS",
  "Backup + Vault",
];

type FleetUser = {
  id: string;
  email: string;
  full_name: string;
  is_online: boolean;
  last_login_at: string | null;
  last_login_ip: string | null;
};

type LoginEvent = {
  user_id: string | null;
  email: string | null;
  full_name: string | null;
  ip_address: string | null;
  created_at: string;
};

type UserActivityData = {
  users: FleetUser[];
  login_events: LoginEvent[];
};

type ActivityLog = {
  id: string;
  message: string;
  category: string;
  created_at: string;
};

type ActivityAlert = {
  id: string;
  title: string;
  created_at: string;
};

type EmailScannerSettings = {
  email_address: string | null;
  is_configured: boolean;
};

type ManagedUser = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
};

const inputClass =
  "h-10 w-full rounded-xl border border-white/10 bg-white/5 px-3 text-sm focus:border-[var(--mint)]/50 focus:outline-none focus:ring-1 focus:ring-[var(--mint)]/20";

export default function SettingsPage() {
  const navigate = useNavigate();
  const { connected } = useServiceConnected();
  const { isAdmin, displayName, roleLabel } = useCurrentUser();
  const { online, pending } = useConnectivitySync(null);

  const [policies, setPolicies] = useState<Policies>(DEFAULT_POLICIES);
  const [invite, setInvite] = useState({
    email: "",
    full_name: "",
    password: "",
    role: "user" as "user" | "admin",
  });
  const [inviteBusy, setInviteBusy] = useState(false);
  const [inviteMsg, setInviteMsg] = useState("");
  const [inviteErr, setInviteErr] = useState("");

  const [userActivity, setUserActivity] = useState<UserActivityData>({
    users: [],
    login_events: [],
  });
  const [recentLogs, setRecentLogs] = useState<ActivityLog[]>([]);
  const [recentAlerts, setRecentAlerts] = useState<ActivityAlert[]>([]);
  const [activityLoading, setActivityLoading] = useState(false);
  const [emailSettings, setEmailSettings] = useState({
    email_address: "",
    email_password: "",
    is_configured: false,
  });
  const [managedUsers, setManagedUsers] = useState<ManagedUser[]>([]);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [approvingUserId, setApprovingUserId] = useState<string | null>(null);
  const [emailSettingsBusy, setEmailSettingsBusy] = useState(false);
  const [emailSettingsMsg, setEmailSettingsMsg] = useState("");
  const [emailSettingsErr, setEmailSettingsErr] = useState("");

  const loadUserActivity = useCallback(async () => {
    if (!isAdmin || !connected) {
      setUserActivity({ users: [], login_events: [] });
      return;
    }
    setActivityLoading(true);
    try {
      const { data } = await api.get<UserActivityData>("/auth/user-activity");
      setUserActivity({
        users: Array.isArray(data?.users) ? data.users : [],
        login_events: Array.isArray(data?.login_events) ? data.login_events : [],
      });
    } catch {
      setUserActivity({ users: [], login_events: [] });
    } finally {
      setActivityLoading(false);
    }
  }, [connected, isAdmin]);

  const loadFleetActivity = useCallback(async () => {
    if (!isAdmin || !connected) return;
    try {
      const [logsRes, alertsRes] = await Promise.all([
        api.get<ActivityLog[]>("/logs?limit=8"),
        api.get<ActivityAlert[]>("/alerts?limit=5"),
      ]);
      setRecentLogs(Array.isArray(logsRes.data) ? logsRes.data : []);
      setRecentAlerts(Array.isArray(alertsRes.data) ? alertsRes.data : []);
    } catch {
      setRecentLogs([]);
      setRecentAlerts([]);
    }
  }, [connected, isAdmin]);

  const refreshAdminActivity = useCallback(async () => {
    await Promise.all([loadUserActivity(), loadFleetActivity()]);
  }, [loadUserActivity, loadFleetActivity]);

  const loadEmailSettings = useCallback(async () => {
    if (!connected) return;
    try {
      const path = isAdmin && selectedUserId
        ? `/auth/users/${selectedUserId}/email-scanner-settings`
        : "/auth/email-scanner-settings";
      const { data } = await api.get<EmailScannerSettings>(path);
      setEmailSettings((current) => ({
        ...current,
        email_address: data?.email_address || "",
        email_password: "",
        is_configured: data?.is_configured || false,
      }));
    } catch {
      setEmailSettings((current) => ({ ...current, email_password: "", is_configured: false }));
    }
  }, [connected, isAdmin, selectedUserId]);

  const loadManagedUsers = useCallback(async () => {
    if (!isAdmin || !connected) return;
    try {
      const { data } = await api.get<ManagedUser[]>('/auth/users');
      const users = Array.isArray(data) ? data : [];
      setManagedUsers(users);
      setSelectedUserId((current) => current || users[0]?.id || "");
    } catch {
      setManagedUsers([]);
      setSelectedUserId("");
    }
  }, [connected, isAdmin]);

  const submitEmailSettings = useCallback(async () => {
    setEmailSettingsBusy(true);
    setEmailSettingsErr("");
    setEmailSettingsMsg("");
    try {
      const path = isAdmin && selectedUserId
        ? `/auth/users/${selectedUserId}/email-scanner-settings`
        : "/auth/email-scanner-settings";
      await api.post(path, {
        email_address: emailSettings.email_address.trim(),
        email_password: emailSettings.email_password,
      });
      setEmailSettings((current) => ({ ...current, email_password: "", is_configured: true }));
      setEmailSettingsMsg("Email scanner credentials saved. The agent will use them on the next scan cycle.");
    } catch (error: unknown) {
      const detail =
        error && typeof error === "object" && "response" in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setEmailSettingsErr(typeof detail === "string" ? detail : "Could not save email scanner settings.");
    } finally {
      setEmailSettingsBusy(false);
    }
  }, [emailSettings.email_address, emailSettings.email_password, isAdmin, selectedUserId]);

  const approveUser = useCallback(async (userId: string) => {
    setApprovingUserId(userId);
    try {
      await api.patch(`/auth/users/${userId}/approve`);
      
      // Update local state to reflect approval
      setManagedUsers((users) =>
        users.map((user) =>
          user.id === userId ? { ...user, is_active: true } : user
        )
      );
      
      setInviteMsg("User approved successfully. They can now log in.");
      setTimeout(() => setInviteMsg(""), 5000);
    } catch (error: unknown) {
      const detail =
        error && typeof error === "object" && "response" in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setInviteErr(typeof detail === "string" ? detail : "Failed to approve user.");
      setTimeout(() => setInviteErr(""), 5000);
    } finally {
      setApprovingUserId(null);
    }
  }, []);

  useEffect(() => {
    if (!isAdmin) return;
    refreshAdminActivity();
  }, [isAdmin, refreshAdminActivity]);

  useEffect(() => {
    if (!isAdmin) return;
    loadManagedUsers();
  }, [isAdmin, loadManagedUsers]);

  useEffect(() => {
    if (!isAdmin) return;
    loadEmailSettings();
  }, [isAdmin, loadEmailSettings]);

  useEffect(() => {
    if (isAdmin) {
      loadEmailSettings();
    }
  }, [isAdmin, selectedUserId, loadEmailSettings]);

  useEffect(() => {
    if (isAdmin) return;
    loadEmailSettings();
  }, [isAdmin, loadEmailSettings]);

  useEffect(() => {
    if (!isAdmin || !connected) return;
    const id = setInterval(refreshAdminActivity, 15_000);
    return () => clearInterval(id);
  }, [connected, isAdmin, refreshAdminActivity]);

  useEffect(() => {
    if (!isAdmin || !connected) return;
    const wsUrl = import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000/ws/dashboard";
    const socket = new WebSocket(wsUrl);
    socket.onmessage = (message) => {
      try {
        const payload = JSON.parse(message.data) as {
          event?: string;
          data?: { role?: string };
        };
        if (payload.event === "user.login" && payload.data?.role === "admin") {
          return;
        }
        if (
          payload.event === "user.login" ||
          payload.event === "user.logout" ||
          payload.event === "log.created" ||
          payload.event === "alert.created"
        ) {
          refreshAdminActivity();
        }
      } catch {
        /* ignore */
      }
    };
    return () => socket.close();
  }, [connected, isAdmin, refreshAdminActivity]);

  const toggle = (key: PolicyKey) =>
    setPolicies((p) => ({ ...p, [key]: !p[key] }));

  const submitInvite = async (event: FormEvent) => {
    event.preventDefault();
    setInviteErr("");
    setInviteMsg("");
    setInviteBusy(true);
    try {
      await api.post("/auth/register", {
        email: invite.email.trim(),
        full_name: invite.full_name.trim(),
        password: invite.password,
        role: invite.role,
      });
      setInviteMsg(`Account created for ${invite.email.trim()}`);
      setInvite({ email: "", full_name: "", password: "", role: "user" });
      await refreshAdminActivity();
    } catch (e: unknown) {
      const detail =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setInviteErr(typeof detail === "string" ? detail : "Could not create account.");
    } finally {
      setInviteBusy(false);
    }
  };

  const monitoredUsers = userActivity.users;
  const loginHistory = userActivity.login_events;
  const deviceActions = recentLogs.filter((l) =>
    ["device", "usb", "command"].includes((l.category || "").toLowerCase()),
  );

  if (isAdmin) {
    return (
      <div className="space-y-5">
        <header className="flex flex-wrap items-end justify-between gap-3 px-1">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">Admin Settings</h1>
              <span className="rounded-full bg-[var(--mint)]/15 px-2 py-0.5 text-[10px] font-semibold text-[var(--mint)] ring-1 ring-[var(--mint)]/30">
                {roleLabel}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Monitor user logins, review activity, and create dashboard accounts
            </p>
          </div>
          <p className="text-xs text-muted-foreground">
            Signed in as <span className="font-medium text-foreground">{displayName}</span>
          </p>
        </header>

        {/* Login details table */}
        <GlassCard
          title="User Login Details"
          subtitle="All dashboard users (admin accounts hidden)"
          icon={<Users className="h-4 w-4" />}
        >
          {activityLoading && monitoredUsers.length === 0 ? (
            <p className="text-xs text-muted-foreground">Loading users…</p>
          ) : monitoredUsers.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No user accounts yet. Create one below — users will appear here when they log in.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-white/5">
              <table className="w-full min-w-[640px] text-left text-xs">
                <thead>
                  <tr className="border-b border-white/5 text-[10px] uppercase tracking-wider text-muted-foreground">
                    <th className="px-3 py-2 font-medium">Name</th>
                    <th className="px-3 py-2 font-medium">Email</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2 font-medium">Last login</th>
                    <th className="px-3 py-2 font-medium">IP address</th>
                  </tr>
                </thead>
                <tbody>
                  {monitoredUsers.map((u) => (
                    <tr key={u.id} className="border-b border-white/5 last:border-0">
                      <td className="px-3 py-2.5 font-medium">{u.full_name}</td>
                      <td className="px-3 py-2.5 text-muted-foreground">{u.email}</td>
                      <td className="px-3 py-2.5">
                        <StatusBadge online={u.is_online} />
                      </td>
                      <td className="px-3 py-2.5 text-muted-foreground">
                        {u.last_login_at ? `${formatRelative(u.last_login_at)} ago` : "Never"}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-[10px] text-muted-foreground">
                        {u.last_login_ip || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </GlassCard>

        {/* User activity */}
        <GlassCard
          title="User Activity"
          subtitle="Recent sign-ins, device events, and alerts from user accounts"
          icon={<ShieldCheck className="h-4 w-4" />}
        >
          <div className="grid gap-6 md:grid-cols-3">
            <ActivitySection title="Recent logins" icon={<Users className="h-3.5 w-3.5" />} empty="No login events yet">
              {loginHistory.map((event, idx) => (
                <li key={`${event.user_id}-${event.created_at}-${idx}`} className="text-xs">
                  <span className="font-medium">{event.full_name || event.email || "User"}</span>
                  <div className="text-[10px] text-muted-foreground">
                    {formatRelative(event.created_at)} ago
                    {event.ip_address ? ` · ${event.ip_address}` : ""}
                  </div>
                </li>
              ))}
            </ActivitySection>
            <ActivitySection title="Device actions" icon={<Server className="h-3.5 w-3.5" />} empty="No device events">
              {(deviceActions.length ? deviceActions : recentLogs.slice(0, 4)).map((log) => (
                <li key={log.id} className="text-xs">
                  <span className="line-clamp-2">{log.message}</span>
                  <div className="text-[10px] text-muted-foreground">
                    {formatRelative(log.created_at)} ago
                  </div>
                </li>
              ))}
            </ActivitySection>
            <ActivitySection title="Alerts triggered" icon={<Bell className="h-3.5 w-3.5" />} empty="No alerts">
              {recentAlerts.map((alert) => (
                <li key={alert.id} className="text-xs">
                  <span className="font-medium">{alert.title}</span>
                  <div className="text-[10px] text-muted-foreground">
                    {formatRelative(alert.created_at)} ago
                  </div>
                </li>
              ))}
            </ActivitySection>
          </div>
          <div className="mt-5 flex justify-center border-t border-white/5 pt-4">
            <button
              type="button"
              onClick={() => navigate("/logs")}
              className="flex items-center gap-2 rounded-xl border border-[var(--mint)]/30 bg-[var(--mint)]/10 px-6 py-2.5 text-sm font-semibold text-[var(--mint)] transition hover:bg-[var(--mint)]/20"
            >
              <ScrollText className="h-4 w-4" />
              View Full Activity Logs
            </button>
          </div>
        </GlassCard>

        {/* Create user account */}
        <GlassCard
          title="Create User Account"
          subtitle="Add a new dashboard user (default role: User)"
          icon={<UserPlus className="h-4 w-4" />}
          className="overflow-visible"
        >
          <form onSubmit={submitInvite} className="mx-auto grid max-w-2xl gap-3 sm:grid-cols-2">
            <label className="block space-y-1 text-sm sm:col-span-2">
              <span className="text-[11px] font-medium text-muted-foreground">Email</span>
              <input
                type="email"
                required
                autoComplete="off"
                value={invite.email}
                onChange={(e) => setInvite((x) => ({ ...x, email: e.target.value }))}
                className={inputClass}
                placeholder="user@company.com"
              />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="text-[11px] font-medium text-muted-foreground">Full name</span>
              <input
                type="text"
                required
                minLength={2}
                value={invite.full_name}
                onChange={(e) => setInvite((x) => ({ ...x, full_name: e.target.value }))}
                className={inputClass}
                placeholder="Jane Doe"
              />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="text-[11px] font-medium text-muted-foreground">Password</span>
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={invite.password}
                onChange={(e) => setInvite((x) => ({ ...x, password: e.target.value }))}
                className={inputClass}
                placeholder="Min. 8 characters"
              />
            </label>
            <label className="block space-y-1 text-sm sm:col-span-2">
              <span className="text-[11px] font-medium text-muted-foreground">Role</span>
              <select
                value={invite.role}
                onChange={(e) =>
                  setInvite((x) => ({ ...x, role: e.target.value as "user" | "admin" }))
                }
                className={`${inputClass} appearance-none`}
              >
                <option value="user" className="bg-[#111]">User</option>
                <option value="admin" className="bg-[#111]">Admin</option>
              </select>
            </label>
            {inviteErr && (
              <p className="text-xs text-[var(--danger)] sm:col-span-2">{inviteErr}</p>
            )}
            {inviteMsg && (
              <p className="text-xs text-[var(--success)] sm:col-span-2">{inviteMsg}</p>
            )}
            <div className="sm:col-span-2 flex justify-center pt-1">
              <button
                type="submit"
                disabled={inviteBusy}
                className="w-full max-w-sm rounded-xl bg-gradient-cyber px-6 py-2.5 text-sm font-semibold text-black transition hover:brightness-110 disabled:opacity-50"
              >
                {inviteBusy ? "Creating…" : "Create User Account"}
              </button>
            </div>
          </form>
        </GlassCard>

        {/* User Management & Approval */}
        <GlassCard
          title="User Management"
          subtitle="Manage users and approve pending accounts"
          icon={<Users className="h-4 w-4" />}
          className="overflow-visible"
        >
          {managedUsers.length === 0 ? (
            <p className="text-center text-sm text-muted-foreground py-4">
              No users found. Create a user account above.
            </p>
          ) : (
            <div className="space-y-2">
              {managedUsers.map((user) => (
                <div
                  key={user.id}
                  className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3 hover:bg-white/[0.04] transition"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{user.full_name}</p>
                      {!user.is_active && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-[var(--warning)]/10 px-2 py-0.5 text-[10px] font-semibold text-[var(--warning)] ring-1 ring-[var(--warning)]/20">
                          Pending Approval
                        </span>
                      )}
                      {user.is_active && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-[var(--success)]/10 px-2 py-0.5 text-[10px] font-semibold text-[var(--success)] ring-1 ring-[var(--success)]/20">
                          Active
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {user.email} · {user.role}
                    </p>
                  </div>
                  {!user.is_active && (
                    <button
                      onClick={() => approveUser(user.id)}
                      disabled={approvingUserId === user.id}
                      className="flex items-center gap-1.5 rounded-lg bg-[var(--mint)]/10 px-3 py-1.5 text-xs font-semibold text-[var(--mint)] transition hover:bg-[var(--mint)]/20 disabled:opacity-50 ring-1 ring-[var(--mint)]/20"
                    >
                      {approvingUserId === user.id ? (
                        <>
                          <span className="h-3 w-3 animate-spin rounded-full border-2 border-[var(--mint)]/30 border-t-[var(--mint)]" />
                          Approving...
                        </>
                      ) : (
                        <>
                          <Check className="h-3 w-3" />
                          Approve
                        </>
                      )}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        <GlassCard
          title="Email Scanner Setup"
          subtitle={isAdmin ? "Choose a user and manage the Gmail account used by their agent" : "This mailbox is locked to your account"}
          icon={<Mail className="h-4 w-4" />}
          className="overflow-visible"
        >
          {isAdmin ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void submitEmailSettings();
              }}
              className="mx-auto grid max-w-2xl gap-3 sm:grid-cols-2"
            >
              <label className="block space-y-1 text-sm sm:col-span-2">
                <span className="text-[11px] font-medium text-muted-foreground">User</span>
                <select
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(e.target.value)}
                  className={`${inputClass} appearance-none`}
                >
                  {managedUsers.map((user) => (
                    <option key={user.id} value={user.id} className="bg-[#111]">
                      {user.full_name} ({user.email})
                    </option>
                  ))}
                </select>
              </label>
              <label className="block space-y-1 text-sm sm:col-span-2">
                <span className="text-[11px] font-medium text-muted-foreground">Email address</span>
                <input
                  type="email"
                  required
                  autoComplete="off"
                  value={emailSettings.email_address}
                  onChange={(e) =>
                    setEmailSettings((current) => ({ ...current, email_address: e.target.value }))
                  }
                  className={inputClass}
                  placeholder="alerts@company.com"
                />
              </label>
              <label className="block space-y-1 text-sm sm:col-span-2">
                <span className="text-[11px] font-medium text-muted-foreground">Email password / app password</span>
                <input
                  type="password"
                  required
                  autoComplete="new-password"
                  value={emailSettings.email_password}
                  onChange={(e) =>
                    setEmailSettings((current) => ({ ...current, email_password: e.target.value }))
                  }
                  className={inputClass}
                  placeholder="Gmail app password"
                />
              </label>
              <p className="text-[11px] text-muted-foreground sm:col-span-2">
                The selected user will only be able to use this mailbox. Their dashboard view stays read-only.
              </p>
              {emailSettingsErr && (
                <p className="text-xs text-[var(--danger)] sm:col-span-2">{emailSettingsErr}</p>
              )}
              {emailSettingsMsg && (
                <p className="text-xs text-[var(--success)] sm:col-span-2">{emailSettingsMsg}</p>
              )}
              <div className="sm:col-span-2 flex justify-center pt-1">
                <button
                  type="submit"
                  disabled={emailSettingsBusy || !selectedUserId}
                  className="inline-flex w-full max-w-sm items-center justify-center gap-2 rounded-xl bg-gradient-cyber px-6 py-2.5 text-sm font-semibold text-black transition hover:brightness-110 disabled:opacity-50"
                >
                  <Save className="h-4 w-4" />
                  {emailSettingsBusy ? "Saving…" : "Save Email Scanner Settings"}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
                  <div className="text-[11px] font-medium text-muted-foreground">Registered account email</div>
                  <div className="mt-1 text-sm font-medium">{displayName}</div>
                </div>
                <div className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
                  <div className="text-[11px] font-medium text-muted-foreground">Scanner status</div>
                  <div className="mt-1 text-sm font-medium">
                    {emailSettings.is_configured ? "Locked to this account" : "Not configured yet"}
                  </div>
                </div>
              </div>
              <div className="rounded-xl border border-[var(--mint)]/20 bg-[var(--mint)]/5 px-3 py-2 text-xs text-muted-foreground">
                Your mailbox is managed by the admin. You can view it here, but only an admin can change it.
              </div>
              <div className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
                <div className="text-[11px] font-medium text-muted-foreground">Email address</div>
                <div className="mt-1 text-sm font-medium">{emailSettings.email_address || "Not set"}</div>
              </div>
            </div>
          )}
        </GlassCard>

        <div className="mx-auto grid max-w-4xl grid-cols-1 gap-4 md:grid-cols-2">
          <SecurityPoliciesCard policies={policies} onToggle={toggle} />
          {isAdmin && <IntegrationsSettingsCard />}
          <ConnectivityCard online={online} pending={pending} />
        </div>
      </div>
    );
  }

  /* ── Regular user settings (2×2 wireframe) ── */
  return (
    <div className="space-y-5">
      <header className="px-1">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-xs text-muted-foreground">
          Security policies, user management, and platform configuration
        </p>
      </header>

      <div className="mx-auto grid max-w-4xl grid-cols-1 gap-4 md:grid-cols-2">
        <SecurityPoliciesCard policies={policies} onToggle={toggle} />

        <GlassCard title="Create Account" icon={<UserPlus className="h-4 w-4" />}>
          <div className="space-y-2 text-sm">
            <p className="font-medium text-muted-foreground">Admin access required</p>
            <p className="text-xs text-muted-foreground">Only admins can create users.</p>
          </div>
        </GlassCard>

        <ConnectivityCard online={online} pending={pending} />

        <GlassCard title="Security Hardening" icon={<KeyRound className="h-4 w-4" />}>
          <ul className="space-y-2">
            {HARDENING_ITEMS.map((item) => (
              <li
                key={item}
                className="flex items-center gap-2.5 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2 text-sm"
              >
                <Check className="h-4 w-4 shrink-0 text-[var(--mint)]" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </GlassCard>
      </div>
    </div>
  );
}

function StatusBadge({ online }: { online: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
        online
          ? "bg-[var(--success)]/15 text-[var(--success)]"
          : "bg-white/5 text-muted-foreground"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          online ? "bg-[var(--success)] animate-pulse" : "bg-white/30"
        }`}
      />
      {online ? "Online" : "Offline"}
    </span>
  );
}

function SecurityPoliciesCard({
  policies,
  onToggle,
}: {
  policies: Policies;
  onToggle: (key: PolicyKey) => void;
}) {
  return (
    <GlassCard title="Security Policies" icon={<Shield className="h-4 w-4" />}>
      <ul className="space-y-2">
        {POLICY_LABELS.map(({ key, label }) => (
          <li key={key}>
            <button
              type="button"
              onClick={() => onToggle(key)}
              className="flex w-full items-center gap-3 rounded-lg px-1 py-1.5 text-left text-sm transition hover:bg-white/[0.04]"
            >
              <span
                className={`text-base leading-none ${
                  policies[key] ? "text-[var(--mint)]" : "text-muted-foreground/50"
                }`}
                aria-hidden
              >
                {policies[key] ? "●" : "○"}
              </span>
              <span className={policies[key] ? "text-foreground" : "text-muted-foreground"}>
                {label}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </GlassCard>
  );
}

function ConnectivityCard({ online, pending }: { online: boolean; pending: number }) {
  return (
    <GlassCard
      title="Connectivity"
      icon={
        online ? (
          <Wifi className="h-4 w-4 text-[var(--success)]" />
        ) : (
          <WifiOff className="h-4 w-4 text-[var(--danger)]" />
        )
      }
    >
      <dl className="space-y-2 text-sm">
        <div className="flex items-baseline gap-2">
          <dt className="text-muted-foreground">Status:</dt>
          <dd className={`font-semibold ${online ? "text-[var(--success)]" : "text-[var(--danger)]"}`}>
            {online ? "Online" : "Offline"}
          </dd>
        </div>
        <div className="flex items-baseline gap-2">
          <dt className="text-muted-foreground">Logs:</dt>
          <dd className="font-semibold tabular-nums">{pending}</dd>
        </div>
        <dd className="text-xs text-muted-foreground">Queued entries</dd>
      </dl>
    </GlassCard>
  );
}

function ActivitySection({
  title,
  icon,
  empty,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  empty: string;
  children: React.ReactNode;
}) {
  const items = Array.isArray(children) ? children : [children];
  const hasContent = items.some((c) => c !== null && c !== undefined && c !== false);

  return (
    <div>
      <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {icon}
        {title}
      </div>
      {hasContent ? (
        <ul className="space-y-2.5">{children}</ul>
      ) : (
        <p className="text-xs text-muted-foreground">{empty}</p>
      )}
    </div>
  );
}

export function IntegrationsSettingsCard() {
  const [keys, setKeys] = useState({
    VIRUSTOTAL_API_KEY: "",
    HUGGINGFACE_API_KEY: "",
    SMTP_PASSWORD: "",
  });
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  useEffect(() => {
    api.get("/settings/integrations")
      .then(({ data }) => setKeys((prev) => ({ ...prev, ...data })))
      .catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setStatusMsg("");
    try {
      await api.put("/settings/integrations", keys);
      setStatusMsg("Settings saved successfully.");
    } catch {
      setStatusMsg("Failed to save integration settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <GlassCard
      title="AI & Third-Party Integrations"
      subtitle="Configure external threat intelligence, AI engines, and email notifications"
      icon={<KeyRound className="h-4 w-4 text-[var(--cyan)]" />}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {Object.entries(keys).map(([key, val]) => (
          <div key={key} className="space-y-1">
            <label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              {key.replace(/_/g, " ")}
            </label>
            <input
              type="password"
              value={val as string}
              onChange={(e) => setKeys({ ...keys, [key]: e.target.value })}
              className="h-9 w-full rounded-xl border border-white/10 bg-white/5 px-3 text-xs placeholder:text-muted-foreground/60 focus:border-[var(--mint)]/50 focus:outline-none"
            />
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{statusMsg}</span>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1.5 rounded-xl bg-gradient-cyber px-4 py-2 text-xs font-semibold text-black transition hover:brightness-110 disabled:opacity-40"
        >
          <Save className="h-3.5 w-3.5" />
          {saving ? "Saving..." : "Save Settings"}
        </button>
      </div>
    </GlassCard>
  );
}
