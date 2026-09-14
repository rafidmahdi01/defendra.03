import { useEffect, useState, type FormEvent } from "react";
import {
  Plus,
  Server,
  Search,
  Eye,
  ShieldOff,
  RefreshCw,
  Cpu,
  MemoryStick,
  MapPin,
  ChevronDown,
  Trash2,
} from "lucide-react";

import { GlassCard } from "@/components/defendra/Card";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { api } from "@/services/api";
import { formatDeviceLocation } from "@/services/deviceLocation";
import { useServiceConnected } from "@/hooks/useServiceConnected";
import { isViewCleared, setViewCleared } from "@/services/viewClear";

type Device = {
  id: number | string;
  hostname: string;
  ip_address: string;
  os_name?: string;
  status?: string;
  cpu_usage?: number;
  ram_usage?: number;
  location?: string;
  last_seen?: string | null;
  user_id?: string;
  user_email?: string;
  user_full_name?: string;
  user_name?: string;
};

const STATUS_OPTIONS = ["All", "Online", "Offline", "Isolated", "LimpMode"];
const DEVICES_VIEW_KEY = "devices";

export default function DevicesPage() {
  const { connected } = useServiceConnected();
  const { isAdmin, displayName } = useCurrentUser();
  const [devices, setDevices]       = useState<Device[]>([]);
  const [cleared, setCleared]       = useState(() => isViewCleared(DEVICES_VIEW_KEY));
  const [search, setSearch]         = useState("");
  const [statusFilter, setStatus]   = useState("All");
  const [showForm, setShowForm]     = useState(false);
  const [form, setForm]             = useState({ hostname: "", ip_address: "", os_name: "", location: "" });
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [actionBusyId, setActionBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");
  const [deletingAll, setDeletingAll] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get<Device[]>("/devices");
      setDevices(data);
    } catch {
      setDevices([]);
    }
  };

  const deleteAllDevices = async () => {
    if (!connected) return;
    
    const confirmed = window.confirm(
      `Are you sure you want to permanently delete all ${devices.length} device${devices.length !== 1 ? 's' : ''}? This action cannot be undone.`
    );
    
    if (!confirmed) return;
    
    setDeletingAll(true);
    setActionError("");
    
    try {
      await api.delete("/devices");
      setDevices([]);
      setViewCleared(DEVICES_VIEW_KEY, false);
      setCleared(false);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || "Failed to delete devices. Please try again.");
    } finally {
      setDeletingAll(false);
    }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!connected) return;
    load();
  }, [connected]);

  useEffect(() => {
    if (!connected) return;
    const id = setInterval(() => {
      load();
    }, 12_000);
    return () => clearInterval(id);
  }, [connected]);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    if (!connected) return;
    await api.post("/devices", form);
    setForm({ hostname: "", ip_address: "", os_name: "", location: "" });
    setShowForm(false);
    load();
  };

  const updateDeviceStatus = async (device: Device, status: string) => {
    if (!connected) return;
    setActionBusyId(String(device.id));
    setActionError("");
    try {
      const { data } = await api.put<Device>(`/devices/${device.id}`, { status });
      setDevices((prev) =>
        prev.map((item) => (String(item.id) === String(device.id) ? { ...item, ...data } : item)),
      );
      setSelectedDevice((prev) =>
        prev && String(prev.id) === String(device.id) ? { ...prev, ...data } : prev,
      );
    } catch {
      setActionError("Could not update device status. Try again.");
    } finally {
      setActionBusyId(null);
    }
  };

  const displayDevices = cleared ? [] : devices;

  const filtered = displayDevices.filter((d) => {
    const owner = d.user_name || d.user_full_name || d.user_email || "";
    const matchSearch =
      search === "" ||
      d.hostname.toLowerCase().includes(search.toLowerCase()) ||
      owner.toLowerCase().includes(search.toLowerCase()) ||
      d.ip_address.includes(search);
    const matchStatus =
      statusFilter === "All" ||
      (d.status || "").toLowerCase() === statusFilter.toLowerCase();
    return matchSearch && matchStatus;
  });

  const onlineCount = displayDevices.filter((d) => (d.status || "").toLowerCase() === "online").length;
  const locatedCount = displayDevices.filter((d) => {
    if ((d.location || "").trim()) return true;
    const ip = (d.ip_address || "").trim();
    return Boolean(ip && ip !== "127.0.0.1");
  }).length;

  return (
    <div className="space-y-4">
      {/* Page header */}
      <header className="flex flex-wrap items-end justify-between gap-3 px-1">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Devices</h1>
          <p className="text-xs text-muted-foreground">
            {isAdmin
              ? "All user endpoints across the fleet"
              : `Your protected PCs linked to ${displayName}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={!connected || devices.length === 0 || deletingAll}
            onClick={deleteAllDevices}
            className="flex items-center gap-1.5 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-3 py-2 text-xs font-medium text-[var(--danger)] transition hover:bg-[var(--danger)]/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Trash2 className="h-3.5 w-3.5" /> 
            {deletingAll ? "Deleting..." : "Delete All"}
          </button>
          <button
            type="button"
            disabled={!connected}
            onClick={() => connected && setShowForm((v) => !v)}
            className="flex items-center gap-2 rounded-xl bg-gradient-cyber px-4 py-2 text-sm font-semibold text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Plus className="h-4 w-4" />
            Register Device
          </button>
        </div>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          label={isAdmin ? "Total fleet devices" : "Your devices"}
          value={displayDevices.length}
        />
        <SummaryCard label="Online now" value={onlineCount} />
        <SummaryCard
          label={isAdmin ? "With live location" : "Your PCs located"}
          value={locatedCount}
        />
        <SummaryCard
          label={isAdmin ? "Offline / other" : "Not online"}
          value={Math.max(0, displayDevices.length - onlineCount)}
        />
      </div>

      {actionError ? (
        <div className="rounded-xl border border-[var(--danger)]/40 bg-[var(--danger)]/10 px-4 py-2 text-xs text-[var(--danger)]">
          {actionError}
        </div>
      ) : null}

      {/* Register form (collapsible) */}
      {showForm && (
        <GlassCard
          title="Register Endpoint"
          subtitle="Add a new device to the protection fleet"
          icon={<Plus className="h-4 w-4 text-[var(--mint)]" />}
        >
          <form onSubmit={create} className="grid gap-3 md:grid-cols-5">
            {(["hostname", "ip_address", "os_name", "location"] as const).map((field) => (
              <input
                key={field}
                disabled={!connected}
                className="h-10 rounded-xl border border-white/10 bg-white/5 px-3 text-sm placeholder:text-muted-foreground/70 focus:border-[var(--electric)]/50 focus:outline-none focus:ring-2 focus:ring-[var(--electric)]/20 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder={field.replace("_", " ")}
                value={form[field]}
                onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              />
            ))}
            <button
              type="submit"
              disabled={!connected}
              className="h-10 rounded-xl bg-gradient-cyber px-4 text-sm font-semibold text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Register
            </button>
          </form>
        </GlassCard>
      )}

      {/* Search + Filter bar */}
      <div className="glass rounded-2xl px-4 py-3 flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            disabled={!connected}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search Device (hostname, user, IP…)"
            className="h-9 w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-3 text-sm placeholder:text-muted-foreground/60 focus:border-[var(--mint)]/50 focus:outline-none focus:ring-1 focus:ring-[var(--mint)]/20 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="shrink-0 font-medium">Filter:</span>
          <div className="flex flex-wrap gap-1.5">
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt}
                type="button"
                disabled={!connected}
                onClick={() => connected && setStatus(opt)}
                className={`flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-all disabled:cursor-not-allowed disabled:opacity-40 ${
                  statusFilter === opt
                    ? "bg-[var(--mint)]/15 text-[var(--mint)] ring-1 ring-[var(--mint)]/30"
                    : "bg-white/5 text-muted-foreground hover:bg-white/10 hover:text-foreground"
                }`}
              >
                {opt}
                <ChevronDown className="h-3 w-3 opacity-50" />
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Device list table */}
      <GlassCard
        title={isAdmin ? "Fleet Device List" : "Your Device List"}
        subtitle={
          isAdmin
            ? `${filtered.length} device${filtered.length !== 1 ? "s" : ""} from all users`
            : `${filtered.length} of ${displayDevices.length} linked PC${displayDevices.length !== 1 ? "s" : ""}`
        }
        icon={<Server className="h-4 w-4 text-[var(--cyan)]" />}
      >
        <div className="overflow-hidden rounded-xl ring-1 ring-white/5">
          <table className="w-full text-left text-xs">
            <thead className="bg-white/5 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <Th>Device ID</Th>
                <Th>User Name</Th>
                <Th>IP Address</Th>
                <Th>Status</Th>
                <Th>CPU</Th>
                <Th>RAM</Th>
                <Th>Current Location</Th>
                <Th>Last Seen</Th>
                <Th>Action</Th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-3 py-8 text-center text-muted-foreground">
                    No devices match the current filter.
                  </td>
                </tr>
              ) : (
                filtered.map((d) => (
                  <tr key={d.id} className="border-t border-white/5 transition hover:bg-white/[0.03]">
                    <Td>
                      <div className="flex items-center gap-2 font-medium">
                        <Server className="h-3.5 w-3.5 shrink-0 text-[var(--cyan)]" />
                        {d.hostname}
                      </div>
                    </Td>
                    <Td className="text-muted-foreground">
                      {d.user_name || d.user_full_name || d.user_email || "—"}
                    </Td>
                    <Td className="tabular-nums">{d.ip_address}</Td>
                    <Td><StatusPill status={d.status} /></Td>
                    <Td><MeterCell icon={<Cpu className="h-3 w-3" />} value={d.cpu_usage} /></Td>
                    <Td><MeterCell icon={<MemoryStick className="h-3 w-3" />} value={d.ram_usage} /></Td>
                    <Td>
                      <LocationCell location={d.location} ipAddress={d.ip_address} />
                    </Td>
                    <Td className="tabular-nums text-muted-foreground">
                      {d.last_seen ? new Date(d.last_seen).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Never"}
                    </Td>
                    <Td>
                      <ActionButtons
                        device={d}
                        controlsEnabled={connected}
                        busy={actionBusyId === String(d.id)}
                        onView={() => setSelectedDevice(d)}
                        onIsolate={() => updateDeviceStatus(d, "isolated")}
                        onRecover={() => updateDeviceStatus(d, "online")}
                      />
                    </Td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {selectedDevice ? (
        <DeviceDetailModal
          device={selectedDevice}
          busy={actionBusyId === String(selectedDevice.id)}
          onClose={() => setSelectedDevice(null)}
          onIsolate={() => updateDeviceStatus(selectedDevice, "isolated")}
          onRecover={() => updateDeviceStatus(selectedDevice, "online")}
        />
      ) : null}
    </div>
  );
}

/* ── sub-components ─────────────────────────────────── */

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="glass rounded-2xl px-4 py-3">
      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2.5 font-medium">{children}</th>;
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2.5 ${className}`}>{children}</td>;
}

function StatusPill({ status }: { status?: string }) {
  const s = (status || "unknown").toLowerCase();
  const color =
    s === "online"   ? "var(--success)"  :
    s === "offline"  ? "var(--danger)"   :
    s === "isolated" ? "var(--warning)"  :
    s === "limpmode" ? "var(--purple)"   :
                       "var(--muted-foreground)";
  const label = status || "Unknown";
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[10px] font-medium ring-1"
      style={{ color, background: `${color}1f`, borderColor: `${color}55` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

function MeterCell({ icon, value }: { icon: React.ReactNode; value?: number }) {
  if (value == null) return <span className="text-muted-foreground">—</span>;
  const pct = Math.max(0, Math.min(100, value));
  const color = pct < 60 ? "var(--success)" : pct < 85 ? "var(--warning)" : "var(--danger)";
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-muted-foreground">{icon}</span>
      <span className="tabular-nums">{pct.toFixed(0)}%</span>
      <div className="hidden h-1 w-10 overflow-hidden rounded-full bg-white/5 sm:block">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function ActionButtons({
  device,
  controlsEnabled,
  busy,
  onView,
  onIsolate,
  onRecover,
}: {
  device: Device;
  controlsEnabled: boolean;
  busy: boolean;
  onView: () => void;
  onIsolate: () => void;
  onRecover: () => void;
}) {
  const s = (device.status || "").toLowerCase();
  const disabled = !controlsEnabled || busy;

  return (
    <div className="flex items-center gap-1.5">
      <button
        type="button"
        disabled={disabled}
        onClick={onView}
        className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-medium ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
        style={{ color: "var(--cyan)", background: "oklch(0.86 0.2 165 / 0.1)", borderColor: "oklch(0.86 0.2 165 / 0.3)" }}
      >
        <Eye className="h-3 w-3" /> View
      </button>

      {s === "online" && (
        <button
          type="button"
          disabled={disabled}
          onClick={onIsolate}
          className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-medium ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
          style={{ color: "var(--warning)", background: "oklch(0.84 0.17 80 / 0.1)", borderColor: "oklch(0.84 0.17 80 / 0.3)" }}
        >
          <ShieldOff className="h-3 w-3" /> {busy ? "…" : "Isolate"}
        </button>
      )}

      {(s === "limpmode" || s === "isolated") && (
        <button
          type="button"
          disabled={disabled}
          onClick={onRecover}
          className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-medium ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
          style={{ color: "var(--success)", background: "oklch(0.86 0.2 165 / 0.1)", borderColor: "oklch(0.86 0.2 165 / 0.3)" }}
        >
          <RefreshCw className="h-3 w-3" /> {busy ? "…" : "Recover"}
        </button>
      )}
    </div>
  );
}

function DeviceDetailModal({
  device,
  busy,
  onClose,
  onIsolate,
  onRecover,
}: {
  device: Device;
  busy: boolean;
  onClose: () => void;
  onIsolate: () => void;
  onRecover: () => void;
}) {
  const s = (device.status || "").toLowerCase();
  const owner = device.user_name || device.user_full_name || device.user_email || "—";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Close device details"
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="glass relative z-10 w-full max-w-lg rounded-3xl p-6 ring-1 ring-white/10">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">{device.hostname}</h2>
            <p className="text-xs text-muted-foreground">Device details</p>
          </div>
          <StatusPill status={device.status} />
        </div>

        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div className="sm:col-span-2 rounded-xl border border-[var(--mint)]/20 bg-[var(--mint)]/5 px-3 py-3">
            <dt className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-[var(--mint)]">
              <MapPin className="h-3.5 w-3.5" />
              Current Location
            </dt>
            <dd className="mt-1 text-sm font-semibold">
              {formatDeviceLocation(device.location, device.ip_address)}
            </dd>
          </div>
          <DetailRow label="Device ID" value={String(device.id)} />
          <DetailRow label="User" value={owner} />
          <DetailRow label="IP Address" value={device.ip_address || "—"} />
          <DetailRow label="Operating System" value={device.os_name || "—"} />
          <DetailRow
            label="Last Seen"
            value={
              device.last_seen
                ? new Date(device.last_seen).toLocaleString()
                : "Never"
            }
          />
          <DetailRow
            label="CPU Usage"
            value={device.cpu_usage != null ? `${device.cpu_usage.toFixed(0)}%` : "—"}
          />
          <DetailRow
            label="RAM Usage"
            value={device.ram_usage != null ? `${device.ram_usage.toFixed(0)}%` : "—"}
          />
        </dl>

        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-white/10 px-4 py-2 text-xs font-medium text-muted-foreground transition hover:bg-white/5 hover:text-foreground"
          >
            Close
          </button>
          {s === "online" ? (
            <button
              type="button"
              disabled={busy}
              onClick={onIsolate}
              className="flex items-center gap-1.5 rounded-xl bg-[var(--warning)]/15 px-4 py-2 text-xs font-semibold text-[var(--warning)] ring-1 ring-[var(--warning)]/30 transition hover:bg-[var(--warning)]/25 disabled:opacity-50"
            >
              <ShieldOff className="h-3.5 w-3.5" />
              {busy ? "Isolating…" : "Isolate Device"}
            </button>
          ) : null}
          {(s === "isolated" || s === "limpmode") ? (
            <button
              type="button"
              disabled={busy}
              onClick={onRecover}
              className="flex items-center gap-1.5 rounded-xl bg-[var(--success)]/15 px-4 py-2 text-xs font-semibold text-[var(--success)] ring-1 ring-[var(--success)]/30 transition hover:bg-[var(--success)]/25 disabled:opacity-50"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              {busy ? "Recovering…" : "Recover Device"}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function LocationCell({ location, ipAddress }: { location?: string | null; ipAddress?: string }) {
  const label = formatDeviceLocation(location, ipAddress);
  const hasLocation = Boolean((location || "").trim());
  return (
    <span
      className={`inline-flex max-w-[220px] items-start gap-1.5 ${
        hasLocation ? "text-foreground" : "text-muted-foreground"
      }`}
      title={label}
    >
      <MapPin className={`mt-0.5 h-3 w-3 shrink-0 ${hasLocation ? "text-[var(--mint)]" : ""}`} />
      <span className="line-clamp-2">{label}</span>
    </span>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
      <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-all font-medium">{value}</dd>
    </div>
  );
}
