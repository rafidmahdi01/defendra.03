import { useCallback, useEffect, useRef, useState } from "react";
import {
  type LucideIcon,
  LayoutDashboard,
  Server,
  Mail,
  Usb,
  DatabaseBackup,
  Chrome,
  Bell,
  Settings,
  ScrollText,
  LineChart,
  LogOut,
  ShieldCheck,
  ShieldAlert,
  ShieldOff,
  CheckCircle2,
  Trash2,
  X,
  Link2,
  ListChecks,
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { DefendraLogo } from "./Logo";
import { api, clearWorkstationLink, isElectronApp, isWorkstationLinked } from "@/services/api";
import { notifyAuthChanged } from "@/hooks/useCurrentUser";
import { formatRelative } from "@/hooks/useTelemetry";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useServiceConnected } from "@/hooks/useServiceConnected";

type NavItem = {
  to: string;
  icon: typeof LayoutDashboard;
  label: string;
};

const navItems: NavItem[] = [
  { to: "/",          icon: LayoutDashboard, label: "Dashboard" },
  { to: "/devices",   icon: Server,          label: "Devices"   },
  { to: "/emails",    icon: Mail,            label: "Emails"    },
  { to: "/usb",       icon: Usb,             label: "USB"       },
  { to: "/backups",   icon: DatabaseBackup,  label: "Backups"   },
  { to: "/extension", icon: Chrome,          label: "Browser"   },
  { to: "/alerts",    icon: Bell,            label: "Alerts"    },
  { to: "/analytics", icon: LineChart,       label: "Analytics" },
  { to: "/logs",       icon: ScrollText,   label: "Logs"      },
  { to: "/whitelist",  icon: ListChecks,   label: "Whitelist" },
  { to: "/settings",   icon: Settings,     label: "Settings"  },
];

type Notif = {
  id: string;
  icon: LucideIcon;
  color: string;
  title: string;
  desc: string;
  time: string;
  read: boolean;
};

type ApiAlertRow = {
  id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  created_at: string;
};

function severityColor(sev: string): string {
  const s = sev.toLowerCase();
  if (s === "critical") return "var(--danger)";
  if (s === "high") return "var(--danger)";
  if (s === "medium") return "var(--warning)";
  if (s === "low") return "var(--success)";
  return "var(--cyan)";
}

function pickNotifIcon(title: string, desc: string): LucideIcon {
  const t = `${title} ${desc}`.toLowerCase();
  if (t.includes("usb") || t.includes("removable")) return Usb;
  if (t.includes("email") || t.includes("phish") || t.includes("mail")) return Mail;
  if (t.includes("backup")) return DatabaseBackup;
  if (t.includes("device") && (t.includes("offline") || t.includes("online") || t.includes("reconnect"))) return ShieldOff;
  return ShieldAlert;
}


export function TopBar() {
  const navigate = useNavigate();
  const { connected } = useServiceConnected();
  const { displayName, roleLabel } = useCurrentUser();

  const [bellOpen, setBellOpen] = useState(false);
  const [rawAlerts, setRawAlerts] = useState<ApiAlertRow[]>([]);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(() => new Set());
  const [localReadIds, setLocalReadIds] = useState<Set<string>>(() => new Set());
  const [wsLinked, setWsLinked] = useState(() => isWorkstationLinked());
  const [clearingNotifs, setClearingNotifs] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const navRef = useRef<HTMLElement>(null);

  const electron = isElectronApp();

  useEffect(() => {
    const syncWs = () => setWsLinked(isWorkstationLinked());
    window.addEventListener("crps-workstation-linked", syncWs);
    window.addEventListener("crps-workstation-unlinked", syncWs);
    return () => {
      window.removeEventListener("crps-workstation-linked", syncWs);
      window.removeEventListener("crps-workstation-unlinked", syncWs);
    };
  }, []);

  const loadAlerts = useCallback(async () => {
    if (!connected || (electron && !wsLinked)) {
      setRawAlerts([]);
      return;
    }
    try {
      const { data } = await api.get<ApiAlertRow[]>("/alerts?limit=20");
      setRawAlerts(Array.isArray(data) ? data : []);
    } catch {
      setRawAlerts([]);
    }
  }, [connected, electron, wsLinked]);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  // Refresh bell + /alerts when the agent posts a new alert via WebSocket
  useEffect(() => {
    if (!connected || (electron && !wsLinked)) return;

    const wsUrl = import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000/ws/dashboard";
    const socket = new WebSocket(wsUrl);

    socket.onmessage = (message) => {
      try {
        const payload = JSON.parse(message.data) as { event?: string };
        if (
          payload.event === "alert.created" ||
          payload.event === "alert.updated" ||
          payload.event === "alerts.cleared"
        ) {
          loadAlerts();
        }
      } catch {
        /* ignore malformed frames */
      }
    };

    return () => socket.close();
  }, [connected, electron, wsLinked, loadAlerts]);

  useEffect(() => {
    if (bellOpen && connected) loadAlerts();
  }, [bellOpen, connected, loadAlerts]);

  useEffect(() => {
    if (!connected || (electron && !wsLinked)) setBellOpen(false);
  }, [connected, electron, wsLinked]);

  const notifs: Notif[] = rawAlerts
    .filter((a) => !dismissedIds.has(a.id))
    .map((a) => ({
      id: a.id,
      icon: pickNotifIcon(a.title, a.description),
      color: severityColor(a.severity),
      title: a.title,
      desc: a.description,
      time: `${formatRelative(a.created_at)} ago`,
      read: a.status === "resolved" || localReadIds.has(a.id),
    }));

  const unread = notifs.filter((n) => !n.read).length;

  const markAllRead = () =>
    setLocalReadIds((prev) => {
      const next = new Set(prev);
      notifs.forEach((n) => next.add(n.id));
      return next;
    });

  const dismiss = (id: string) => {
    setDismissedIds((prev) => new Set(prev).add(id));
  };

  const clearAllNotifications = async () => {
    if (!connected || clearingNotifs) return;
    setClearingNotifs(true);
    try {
      await api.delete("/alerts");
      setRawAlerts([]);
      setDismissedIds(new Set());
      setLocalReadIds(new Set());
    } catch {
      setDismissedIds((prev) => {
        const next = new Set(prev);
        rawAlerts.forEach((a) => next.add(a.id));
        return next;
      });
      setRawAlerts([]);
    } finally {
      setClearingNotifs(false);
    }
  };

  // Add horizontal scroll wheel support for navigation
  useEffect(() => {
    const navElement = navRef.current;
    if (!navElement) return;

    const handleWheel = (e: WheelEvent) => {
      // Only handle horizontal scrolling or convert vertical to horizontal
      if (e.deltaY !== 0) {
        e.preventDefault();
        navElement.scrollLeft += e.deltaY;
      }
    };

    navElement.addEventListener("wheel", handleWheel, { passive: false });
    return () => navElement.removeEventListener("wheel", handleWheel);
  }, []);

  // Close panel when clicking outside
  useEffect(() => {
    if (!bellOpen) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setBellOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [bellOpen]);

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      /* best-effort — still clear local session */
    }
    localStorage.removeItem("crps_token");
    localStorage.removeItem("crps_user");
    notifyAuthChanged();
    clearWorkstationLink();
    navigate("/login");
  };

  return (
    <header className="glass sticky top-0 z-30 mx-0 flex items-center gap-0 px-4 py-3 border-b border-[var(--glass-border)]">
      {/* Logo */}
      <div className="flex shrink-0 items-center pr-4 border-r border-[var(--glass-border)]">
        <DefendraLogo />
      </div>

      {/* Nav links */}
      <nav ref={navRef} className="flex flex-1 items-center gap-1 overflow-x-auto px-4 scrollbar-none">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex shrink-0 items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-medium transition-all ${
                isActive
                  ? "bg-[var(--mint)]/15 text-[var(--mint)] ring-1 ring-[var(--mint)]/30"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <item.icon className={`h-3.5 w-3.5 shrink-0 ${isActive ? "text-[var(--mint)]" : ""}`} />
                <span>{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Right section */}
      <div className="flex shrink-0 items-center gap-2 pl-3 border-l border-[var(--glass-border)]">
        {electron && !wsLinked && (
          <button
            type="button"
            title="Connect this computer"
            onClick={() => window.dispatchEvent(new Event("crps-open-workstation-modal"))}
            className="hidden items-center gap-1.5 rounded-xl border border-[var(--warning)]/40 bg-[var(--warning)]/10 px-3 py-2 text-[11px] font-semibold text-[var(--warning)] transition hover:bg-[var(--warning)]/20 sm:flex"
          >
            <Link2 className="h-3.5 w-3.5" />
            Connect PC
          </button>
        )}
        <div className="hidden items-center gap-1.5 rounded-lg bg-white/5 px-2.5 py-1.5 text-[11px] text-muted-foreground sm:flex">
          <ShieldCheck className="h-3 w-3 text-[var(--success)]" />
          <span className="text-foreground font-medium">Hardened</span>
        </div>

        {/* Bell button + dropdown */}
        <div ref={panelRef} className="relative">
          <button
            type="button"
            title={
              !connected
                ? "Connect to the server to load notifications"
                : electron && !wsLinked
                  ? "Connect this computer first"
                  : "Notifications"
            }
            disabled={!connected || (electron && !wsLinked)}
            onClick={() => connected && !(electron && !wsLinked) && setBellOpen((v) => !v)}
            className="glass relative flex h-9 w-9 items-center justify-center rounded-xl transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Bell className={`h-4 w-4 transition ${bellOpen ? "text-[var(--mint)]" : ""}`} />
            {unread > 0 && (
              <span className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-[var(--danger)] text-[8px] font-bold text-white">
                {unread}
              </span>
            )}
          </button>

          {/* Notification panel */}
          {bellOpen && (
            <div
              className="absolute right-0 top-full mt-2 w-[340px] rounded-2xl shadow-2xl overflow-hidden"
              style={{
                background: "oklch(0.13 0.04 265 / 0.97)",
                border: "1px solid oklch(0.86 0.2 165 / 0.22)",
                boxShadow: "0 24px 64px -8px oklch(0 0 0 / 0.9)",
                backdropFilter: "blur(40px)",
              }}
            >
              {/* Panel header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <Bell className="h-4 w-4 text-[var(--mint)]" />
                  <span className="text-sm font-semibold">Notifications</span>
                  {notifs.length > 0 && (
                    <span className="rounded-full bg-[var(--danger)]/20 px-1.5 py-0.5 text-[9px] font-bold text-[var(--danger)] ring-1 ring-[var(--danger)]/30">
                      {notifs.length}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={markAllRead}
                    disabled={notifs.length === 0}
                    className="text-[10px] text-[var(--mint)] hover:underline disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Mark all read
                  </button>
                  <button
                    type="button"
                    onClick={clearAllNotifications}
                    disabled={!connected || notifs.length === 0 || clearingNotifs}
                    className="flex items-center gap-1 text-[10px] text-[var(--danger)] hover:underline disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <Trash2 className={`h-3 w-3 ${clearingNotifs ? "animate-pulse" : ""}`} />
                    Clear
                  </button>
                </div>
              </div>

              {/* Notification list */}
              <div className="max-h-[360px] overflow-y-auto">
                {notifs.length === 0 ? (
                  <div className="py-10 text-center text-xs text-muted-foreground">
                    <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-[var(--success)]/40" />
                    All caught up — no new notifications
                  </div>
                ) : (
                  notifs.map((n) => (
                    <div
                      key={n.id}
                      className={`group relative flex items-start gap-3 px-4 py-3 border-b border-white/[0.04] transition hover:bg-white/[0.04] ${
                        !n.read ? "bg-white/[0.03]" : ""
                      }`}
                    >
                      {/* Unread dot */}
                      {!n.read && (
                        <span className="absolute left-2 top-4 h-1.5 w-1.5 rounded-full bg-[var(--mint)]" />
                      )}
                      {/* Icon */}
                      <span
                        className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ring-1"
                        style={{ background: `${n.color}18`, color: n.color, borderColor: `${n.color}40` }}
                      >
                        <n.icon className="h-4 w-4" />
                      </span>
                      {/* Text */}
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-semibold">{n.title}</p>
                        <p className="mt-0.5 text-[10px] text-muted-foreground leading-relaxed">{n.desc}</p>
                        <p className="mt-1 text-[9px] text-muted-foreground/60">{n.time}</p>
                      </div>
                      {/* Dismiss */}
                      <button
                        onClick={() => dismiss(n.id)}
                        className="mt-0.5 hidden h-5 w-5 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-white/10 hover:text-foreground group-hover:flex"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-white/5 px-4 py-2.5 text-center">
                <button
                  onClick={() => { setBellOpen(false); navigate("/alerts"); }}
                  className="text-[11px] text-[var(--mint)] hover:underline"
                >
                  View all alerts →
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User */}
        <div className="glass flex items-center gap-2 rounded-xl px-2 py-1.5">
          <div className="h-7 w-7 rounded-lg bg-gradient-cyber" />
          <div className="hidden text-xs leading-tight md:block">
            <div className="font-semibold">{displayName}</div>
            <div className="text-[10px] text-muted-foreground">{roleLabel}</div>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={logout}
          title="Sign out"
          className="glass flex h-9 w-9 items-center justify-center rounded-xl hover:bg-white/10"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
