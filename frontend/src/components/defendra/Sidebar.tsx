import {
  LayoutDashboard,
  ShieldAlert,
  Server,
  Bell,
  LineChart,
  Settings,
  ScrollText,
  Mail,
  Usb,
  DatabaseBackup,
  Chrome,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { DefendraLogo } from "./Logo";
import { useCurrentUser } from "@/hooks/useCurrentUser";


type Item = {
  to: string;
  icon: typeof LayoutDashboard;
  label: string;
};

const items: Item[] = [
  { to: "/",          icon: LayoutDashboard, label: "Dashboard" },
  { to: "/devices",   icon: Server,          label: "Devices"   },
  { to: "/emails",    icon: Mail,            label: "Emails"    },
  { to: "/usb",       icon: Usb,             label: "USB"       },
  { to: "/backups",   icon: DatabaseBackup,  label: "Backups"   },
  { to: "/extension", icon: Chrome,          label: "Browser"   },
  { to: "/alerts",    icon: Bell,            label: "Alerts"    },
  { to: "/analytics", icon: LineChart,       label: "Analytics" },
  { to: "/logs",      icon: ScrollText,      label: "Logs"      },
  { to: "/settings",  icon: Settings,        label: "Settings"  },
];

export function DefendraSidebar() {
  const { displayName, roleLabel } = useCurrentUser();

  return (
    <aside className="glass sticky top-4 ml-4 hidden h-[calc(100vh-2rem)] w-64 flex-col rounded-2xl p-4 lg:flex">
      <div className="px-2 py-3">
        <DefendraLogo />
      </div>
      <div className="my-3 h-px bg-gradient-to-r from-transparent via-border to-transparent" />
      <nav className="flex flex-1 flex-col gap-1">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all ${
                isActive
                  ? "bg-[var(--mint)] text-black shadow-[0_0_28px_-4px_var(--mint)]"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`flex h-8 w-8 items-center justify-center rounded-lg transition-all ${
                    isActive
                      ? "bg-black/15 text-black"
                      : "bg-white/5 group-hover:bg-white/10"
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                </span>
                <span className="font-medium tracking-tight">{item.label}</span>
                {isActive && (
                  <span className="ml-auto h-1.5 w-1.5 rounded-full bg-black/60 animate-pulse-glow" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="glass-strong mt-3 rounded-xl p-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <ShieldAlert className="h-3.5 w-3.5" />
          CRPS v1.0 · Secure
        </div>
        <div className="mt-2 flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-gradient-cyber" />
          <div className="min-w-0">
            <div className="truncate text-xs font-semibold">{displayName}</div>
            <div className="truncate text-[10px] text-muted-foreground">{roleLabel}</div>
          </div>
        </div>
      </div>
    </aside>
  );
}

export function MobileNav() {
  return (
    <div className="glass mx-4 mb-3 flex gap-1 overflow-x-auto rounded-xl p-1.5 lg:hidden">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/"}
          className={({ isActive }) =>
            `flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs transition ${
              isActive
                ? "bg-[var(--mint)] text-black"
                : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
            }`
          }
        >
          <item.icon className="h-3.5 w-3.5" />
          {item.label}
        </NavLink>
      ))}
    </div>
  );
}
