import { useEffect, useRef, useState } from "react";
import { ShieldCheck, Plus, Trash2, RefreshCw } from "lucide-react";

import { GlassCard } from "@/components/defendra/Card";
import { api } from "@/services/api";
import { useServiceConnected } from "@/hooks/useServiceConnected";

type Entry = {
  id: string;
  process: string;
  note: string;
  added_at: string;
  added_by: string;
};

export default function WhitelistPage() {
  const { connected } = useServiceConnected();
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState(false);
  const [process, setProcess] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Entry[]>("/whitelist");
      setEntries(data);
    } catch {
      setEntries([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!process.trim()) return;
    setError("");
    try {
      await api.post("/whitelist", { process: process.trim(), note });
      setProcess("");
      setNote("");
      setAdding(false);
      load();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to add entry";
      setError(msg);
    }
  };

  const handleRemove = async (id: string) => {
    if (!connected) return;
    await api.delete(`/whitelist/${id}`);
    load();
  };

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3 px-1">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Process Whitelist</h1>
          <p className="text-xs text-muted-foreground">
            {entries.length} custom entr{entries.length === 1 ? "y" : "ies"} · agent checks this list every 5 minutes
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-muted-foreground transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            type="button"
            disabled={!connected}
            onClick={() => { setAdding(true); setTimeout(() => inputRef.current?.focus(), 50); }}
            className="flex items-center gap-1.5 rounded-xl bg-[var(--mint)] px-3 py-2 text-xs font-semibold text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Process
          </button>
        </div>
      </header>

      {/* Add form */}
      {adding && (
        <GlassCard
          title="Add to whitelist"
          subtitle="Enter a process name to allow it (e.g. spotify.exe)"
          icon={<Plus className="h-4 w-4 text-[var(--mint)]" />}
        >
          <form onSubmit={handleAdd} className="flex flex-col gap-3">
            <div className="flex flex-wrap gap-3">
              <input
                ref={inputRef}
                value={process}
                onChange={(e) => setProcess(e.target.value)}
                placeholder="process.exe"
                className="flex-1 min-w-[180px] rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-[var(--mint)]/50 focus:outline-none focus:ring-1 focus:ring-[var(--mint)]/30"
              />
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Note (optional)"
                className="flex-[2] min-w-[200px] rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-[var(--mint)]/50 focus:outline-none focus:ring-1 focus:ring-[var(--mint)]/30"
              />
            </div>
            {error && <p className="text-xs text-[var(--danger)]">{error}</p>}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={!process.trim()}
                className="rounded-xl bg-[var(--mint)] px-4 py-2 text-xs font-semibold text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Add
              </button>
              <button
                type="button"
                onClick={() => { setAdding(false); setError(""); setProcess(""); setNote(""); }}
                className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-muted-foreground transition hover:bg-white/10"
              >
                Cancel
              </button>
            </div>
          </form>
        </GlassCard>
      )}

      <GlassCard
        title="Custom whitelist"
        subtitle="Processes added here will never be killed by the agent"
        icon={<ShieldCheck className="h-4 w-4 text-[var(--mint)]" />}
      >
        <div className="overflow-hidden rounded-xl ring-1 ring-white/5">
          <table className="w-full text-left text-xs">
            <thead className="bg-white/5 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Process</th>
                <th className="px-3 py-2 font-medium">Note</th>
                <th className="px-3 py-2 font-medium">Added</th>
                <th className="px-3 py-2 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-muted-foreground">
                    {loading ? "Loading…" : "No custom entries. Built-in safe processes are always protected."}
                  </td>
                </tr>
              )}
              {entries.map((row) => (
                <tr key={row.id} className="border-t border-white/5 transition hover:bg-white/[0.03]">
                  <td className="px-3 py-2">
                    <span className="inline-flex items-center gap-1.5 rounded-md bg-[var(--mint)]/10 px-2 py-0.5 font-mono text-[11px] text-[var(--mint)] ring-1 ring-[var(--mint)]/20">
                      {row.process}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">{row.note || "—"}</td>
                  <td className="px-3 py-2 text-muted-foreground tabular-nums">
                    {new Date(row.added_at).toLocaleDateString()}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      disabled={!connected}
                      onClick={() => handleRemove(row.id)}
                      className="inline-flex items-center gap-1 rounded-lg border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-2.5 py-1 text-[10px] font-medium text-[var(--danger)] transition hover:bg-[var(--danger)]/20 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <Trash2 className="h-3 w-3" />
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}
