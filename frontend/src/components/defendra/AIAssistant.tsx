import { useEffect, useRef, useState } from "react";
import {
  Sparkles,
  Send,
  ShieldCheck,
  AlertTriangle,
  Wand2,
  X,
  Bot,
  ChevronDown,
} from "lucide-react";

import { API_URL, clearWorkstationLink } from "@/services/api";

type Message = { role: "user" | "ai"; text: string };

const WELCOME_TEXT =
  "I'm Sentinel AI. Ask about health, threats, devices, logs, or emails. I'll analyze your security data and provide recommendations to strengthen your cyber resilience.";

/** True only for raw Google API quota payloads — not our own markdown banners (e.g. "429 / quota"). */
function looksLikeProviderQuotaPayload(text: string): boolean {
  const u = text.toUpperCase();
  if (u.includes("RESOURCE_EXHAUSTED")) return true;
  if (u.includes("429") || u.includes("RATE LIMIT")) return true;
  return false;
}

function friendlySentinelFailureMessage(raw: string): string {
  if (looksLikeProviderQuotaPayload(raw)) {
    return "Hugging Face reported a quota or rate limit. Sentinel should fall back to Firestore snapshot text; check your token and model access if it does not.";
  }
  if (raw.length > 500) {
    return "Sentinel hit an upstream error (details hidden). Check the backend terminal; snapshot replies should still work.";
  }
  return raw;
}

const QUICK_RECS = [
  {
    icon: AlertTriangle,
    color: "var(--danger)",
    title: "Isolate DC-EU-03",
    desc: "Lateral movement signatures detected from 10.42.18.7.",
    cta: "Isolate",
  },
  {
    icon: ShieldCheck,
    color: "var(--success)",
    title: "Rotate service keys",
    desc: "3 keys older than 90 days found in production scope.",
    cta: "Rotate",
  },
  {
    icon: Wand2,
    color: "var(--purple)",
    title: "Tune phishing model",
    desc: "Recent FP cluster on procurement domain. Apply trust list.",
    cta: "Apply",
  },
];

function parseOneSseDataBlock(block: string): { t?: string; error?: string } | null {
  const line = block.trim();
  if (!line.startsWith("data:")) return null;
  const raw = line.slice(5).trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw) as { t?: string; error?: string };
  } catch {
    return null;
  }
}

const SESSION_MSG =
  "Your session is missing or expired. Please sign in again to use Sentinel.";

function clearSessionAndGoLogin() {
  localStorage.removeItem("crps_token");
  localStorage.removeItem("crps_user");
  clearWorkstationLink();
  const path =
    (window.location.pathname.replace(/\/$/, "") || "/").toLowerCase();
  if (path !== "/login") window.location.replace("/login");
}

async function streamSentinelMessage(
  message: string,
  onDelta: (fullText: string) => void,
): Promise<void> {
  const token = localStorage.getItem("crps_token");
  if (!token) throw new Error(SESSION_MSG);

  const res = await fetch(`${API_URL}/api/sentinel/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  });

  if (res.status === 401) {
    clearSessionAndGoLogin();
    throw new Error(SESSION_MSG);
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = (await res.json()) as { detail?: unknown };
      if (typeof j.detail === "string") detail = j.detail;
      else if (Array.isArray(j.detail)) detail = j.detail.map((x: { msg?: string }) => x.msg).join(" ");
    } catch {
      /* keep detail */
    }
    throw new Error(friendlySentinelFailureMessage(detail));
  }

  const body = res.body;
  if (!body) throw new Error("Empty response from Sentinel.");

  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let acc = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const ev = parseOneSseDataBlock(block);
      if (!ev) continue;
      if (ev.error) throw new Error(friendlySentinelFailureMessage(ev.error));
      if (ev.t) {
        acc += ev.t;
        onDelta(acc);
      }
    }
  }

  if (buffer.trim()) {
    const ev = parseOneSseDataBlock(buffer);
    if (ev) {
      if (ev.error) throw new Error(friendlySentinelFailureMessage(ev.error));
      if (ev.t) {
        acc += ev.t;
        onDelta(acc);
      }
    }
  }
}

export function AIAssistantWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([{ role: "ai", text: WELCOME_TEXT }]);
  const [typing, setTyping] = useState(false);
  const [sendError, setSendError] = useState("");
  const [sentinelHuggingFaceLlm, setSentinelHuggingFaceLlm] = useState<boolean | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const applyHealthBody = (body: { sentinel_huggingface_llm?: boolean }) => {
    setSentinelHuggingFaceLlm(body.sentinel_huggingface_llm ?? false);
  };

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(5000) })
      .then((r) => r.json() as Promise<{ sentinel_huggingface_llm?: boolean }>)
      .then((body) => {
        if (!cancelled) applyHealthBody(body);
      })
      .catch(() => {
        if (!cancelled) setSentinelHuggingFaceLlm(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(5000) })
      .then((r) => r.json() as Promise<{ sentinel_huggingface_llm?: boolean }>)
      .then((body) => {
        if (!cancelled) applyHealthBody(body);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  const sendWithText = async (raw: string) => {
    const text = raw.trim();
    if (!text) return;
    setSendError("");
    setMessages((m) => [...m, { role: "user", text }]);
    setTyping(true);
    let accumulated = "";
    let sawChunk = false;

    try {
      await streamSentinelMessage(text, (next) => {
        if (!sawChunk) sawChunk = true;
        accumulated = next;
        setMessages((m) => {
          const copy = [...m];
          const last = copy[copy.length - 1];
          if (last?.role === "ai") {
            copy[copy.length - 1] = { role: "ai", text: accumulated };
          } else {
            copy.push({ role: "ai", text: accumulated });
          }
          return copy;
        });
      });

      if (!sawChunk || !accumulated.trim()) {
        setMessages((m) => {
          const copy = [...m];
          const last = copy[copy.length - 1];
          if (last?.role === "ai" && !last.text.trim()) {
            copy[copy.length - 1] = {
              role: "ai",
              text: "(Model returned no text. Check HUGGINGFACE_API_KEY, model access, and quota.)",
            };
          } else if (last?.role === "user") {
            copy.push({
              role: "ai",
              text: "(Model returned no text. Check HUGGINGFACE_API_KEY, model access, and quota.)",
            });
          }
          return copy;
        });
      }
    } catch (e) {
      const raw = e instanceof Error ? e.message : "Sentinel failed.";
      const msg = friendlySentinelFailureMessage(raw);
      setSendError(msg);
      setMessages((m) => {
        const copy = [...m];
        const last = copy[copy.length - 1];
        if (last?.role === "ai") {
          copy[copy.length - 1] = { role: "ai", text: msg };
        } else {
          copy.push({ role: "ai", text: msg });
        }
        return copy;
      });
    } finally {
      setTyping(false);
    }
  };

  const send = () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    void sendWithText(text);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <>
      <div
        className={`fixed bottom-24 right-5 z-[999] flex flex-col rounded-2xl shadow-2xl transition-all duration-300 origin-bottom-right ${
          open
            ? "w-[calc(100vw-2.5rem)] max-w-[340px] h-[520px] opacity-100 scale-100"
            : "w-0 h-0 opacity-0 scale-90 pointer-events-none"
        }`}
        style={{
          background: "oklch(0.13 0.04 265 / 0.97)",
          border: "1px solid oklch(0.86 0.2 165 / 0.22)",
          boxShadow: "0 24px 64px -8px oklch(0 0 0 / 0.9), 0 0 40px -12px #22c55e55",
          backdropFilter: "blur(40px)",
        }}
      >
        <div className="relative flex items-center gap-3 rounded-t-2xl p-4 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-green-500/10 to-transparent" />
          <div className="absolute -top-px left-1/4 right-1/4 h-px bg-gradient-to-r from-transparent via-green-500/60 to-transparent" />
          <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-green-500 to-green-700 shadow-lg">
            <Sparkles className="h-4 w-4 text-white" />
            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-[#0d1117] bg-green-400 animate-pulse" />
          </div>
          <div className="relative">
            <div className="text-sm font-semibold tracking-tight">Sentinel AI</div>
            <div className="text-[10px] text-green-400/80">
              {sentinelHuggingFaceLlm === true
                ? "Hugging Face + Firestore context"
                : sentinelHuggingFaceLlm === false
                  ? "Firestore snapshot (add Hugging Face key)"
                    : "Live context"}
            </div>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="relative ml-auto flex h-7 w-7 items-center justify-center rounded-lg bg-white/5 text-muted-foreground hover:bg-white/10 hover:text-foreground"
          >
            <ChevronDown className="h-4 w-4" />
          </button>
        </div>

        <div className="px-4 pb-2">
          <p className="mb-1.5 text-[9px] uppercase tracking-widest text-muted-foreground">Recommendations</p>
          <div
            className="flex gap-1.5 overflow-x-auto overscroll-x-contain pb-1 scrollbar-none"
            onWheel={(event) => {
              if (event.deltaY !== 0) {
                event.currentTarget.scrollLeft += event.deltaY;
                event.preventDefault();
              }
            }}
          >
            {QUICK_RECS.map((r) => (
              <button
                type="button"
                key={r.title}
                onClick={() => {
                  void sendWithText(`Scenario: ${r.title}. ${r.desc} What concrete steps should I take?`);
                }}
                className="flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[10px] font-medium ring-1 transition hover:brightness-125"
                style={{ color: r.color, background: `${r.color}18`, borderColor: `${r.color}40` }}
              >
                <r.icon className="h-3 w-3" />
                {r.title}
              </button>
            ))}
          </div>
        </div>

        <div className="mx-3 h-px bg-white/5" />

        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-2.5 scrollbar-none">
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-2 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
              {m.role === "ai" && (
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-green-500/20 mt-0.5">
                  <Bot className="h-3.5 w-3.5 text-green-400" />
                </div>
              )}
              <div
                className={`max-w-[82%] rounded-2xl px-2.5 py-2 text-[11px] leading-relaxed whitespace-pre-wrap break-words ${
                  m.role === "user"
                    ? "rounded-tr-sm bg-green-500/20 text-green-100 ring-1 ring-green-500/30"
                    : "rounded-tl-sm bg-white/[0.06] text-foreground ring-1 ring-white/8"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
          {typing && (
            <div className="flex gap-2">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-green-500/20 mt-0.5">
                <Bot className="h-3.5 w-3.5 text-green-400" />
              </div>
              <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm bg-white/[0.06] px-3 py-2.5 ring-1 ring-white/8">
                <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-bounce [animation-delay:0ms]" />
                <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-bounce [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-white/5 p-2.5">
          {sendError ? (
            <p className="mb-2 text-[10px] text-red-400/90 leading-snug">{sendError}</p>
          ) : null}
          <div className="flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2 ring-1 ring-white/8 focus-within:ring-green-500/30">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              placeholder="Ask Sentinel anything…"
              className="flex-1 bg-transparent text-xs placeholder:text-muted-foreground/60 focus:outline-none"
              disabled={typing}
            />
            <button
              type="button"
              onClick={send}
              disabled={!input.trim() || typing}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-green-500 text-black shadow-lg transition hover:bg-green-400 disabled:opacity-40"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
          <p className="mt-1.5 text-center text-[9px] text-muted-foreground/50">
            Sentinel AI · streaming · advisory only
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-5 right-5 z-[999] flex h-14 w-14 items-center justify-center rounded-full shadow-2xl transition-all hover:scale-110 active:scale-95"
        style={{
          background: "linear-gradient(135deg, #16a34a, #22c55e)",
          boxShadow: "0 0 32px -4px #22c55e99, 0 8px 24px -4px #00000088",
        }}
        title="Open Sentinel AI"
      >
        {open ? (
          <X className="h-6 w-6 text-white" />
        ) : (
          <div className="relative">
            <Sparkles className="h-6 w-6 text-white" />
            <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border-2 border-green-600 bg-white animate-ping" />
            <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-white" />
          </div>
        )}
      </button>
    </>
  );
}
