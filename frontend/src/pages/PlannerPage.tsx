import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, Bot, Check, Loader2, MapPin, Send, Sparkles, Users, Wallet } from "lucide-react";
import { api, type AgentRun, type ChatAction, type ChatOut, type EventRecord, agentsForLatestRun, setActiveEventId } from "../lib/api";
import { CHIP_HINTS, filledBrief, missionLine, money, phaseCopy } from "../lib/eventDisplay";

type Msg = { role: "user" | "assistant"; text: string; actions?: ChatAction[]; impact?: Record<string, unknown> };

const PIPELINE = ["requirements", "venue", "vendor", "budget", "schedule", "logistics", "risk", "critic"] as const;

export function PlannerPage() {
  const { eventId } = useParams();
  const [event, setEvent] = useState<EventRecord | null>(null);
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      text: "Describe the event (type, city, size, days, budget). I’ll ask for anything still missing — date, indoor/outdoor, hotels — then confirm before agents run. Skip extras if you want defaults.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [live, setLive] = useState<string[]>([]);
  const [agents, setAgents] = useState<AgentRun[]>([]);
  const [phase, setPhase] = useState<string>("intake");
  const [actions, setActions] = useState<ChatAction[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const [hint, setHint] = useState("Instruct the agent...");

  function applyChatRows(rows: { role: string; content: string; actions?: ChatAction[] | null; phase?: string | null }[]) {
    if (!rows.length) return;
    setMessages(rows.map((r) => ({ role: r.role as Msg["role"], text: r.content, actions: r.actions || undefined })));
    const last = [...rows].reverse().find((r) => r.role === "assistant");
    if (last?.actions?.length) setActions(last.actions);
    if (last?.phase) setPhase(last.phase);
  }

  async function refreshPlanner() {
    if (!eventId) return;
    const [ev, rows] = await Promise.all([
      api<EventRecord>(`/api/events/${eventId}`),
      api<{ role: string; content: string; actions?: ChatAction[] | null; phase?: string | null }[]>(`/api/events/${eventId}/chat`),
    ]);
    setEvent(ev);
    const st = ev.copilot_state;
    applyChatRows(rows);
    if (st?.phase) setPhase(st.phase);
    if (st?.available_actions?.length) setActions(st.available_actions);
  }

  useEffect(() => {
    if (!eventId) return;
    setActiveEventId(eventId);
    refreshPlanner().catch(() => setEvent(null));
  }, [eventId]);

  useEffect(() => {
    if (!eventId) return;
    const load = () =>
      api<AgentRun[]>(`/api/events/${eventId}/agents`)
        .then(setAgents)
        .catch(() => {});
    load();
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [eventId]);

  useEffect(() => {
    if (!eventId) return;
    const es = new EventSource(`/api/events/${eventId}/agents/stream`);
    const push = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const line = [data.type, data.agent, data.message ?? data.status, data.duration_ms != null ? `${data.duration_ms}ms` : ""]
          .filter(Boolean)
          .join(" ");
        setLive((s) => [...s.slice(-20), line]);
        if (data.type === "plan_completed") {
          refreshPlanner().catch(() => {});
        }
      } catch {
        if (e.data) setLive((s) => [...s.slice(-20), String(e.data)]);
      }
    };
    for (const name of ["agent_started", "agent_completed", "agent_failed", "critic_issue", "plan_completed"]) {
      es.addEventListener(name, push);
    }
    es.onmessage = push;
    return () => es.close();
  }, [eventId]);

  async function send(text: string, actionId?: string) {
    if ((!text.trim() && !actionId) || !eventId) return;
    const promptChip = Boolean(actionId && (actionId.startsWith("write_") || actionId in CHIP_HINTS) && !actionId.startsWith("pick_"));
    setInput("");
    if (promptChip) {
      setHint(CHIP_HINTS[actionId as string] || "Instruct the agent...");
      inputRef.current?.focus();
    } else {
      setHint("Instruct the agent...");
      setMessages((m) => [...m, { role: "user", text: text.trim() || actionId || "" }]);
    }
    setBusy(true);
    try {
      const res = await api<ChatOut>("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: promptChip ? "" : text, event_id: eventId, action_id: actionId }),
      });
      setMessages((m) => [...m, { role: "assistant", text: res.reply, actions: res.actions, impact: (res.simulation as { impact?: Record<string, unknown> } | null)?.impact }]);
      setActions(res.actions || []);
      if (res.phase) setPhase(res.phase);
      api<EventRecord>(`/api/events/${eventId}`).then(setEvent).catch(() => {});
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: `Request failed: ${err}` }]);
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await send(input.trim());
  }

  const latest = new Map<string, AgentRun>();
  for (const r of agentsForLatestRun(agents)) latest.set(r.agent, r);
  const snap = event?.plan_snapshot || {};
  const risks =
    (snap.risks as {
      title: string;
      severity: string;
      explanation?: string;
      solutions?: string[];
      mitigation?: string;
    }[]) || [];
  const budget = snap.budget as { subtotal?: number } | undefined;
  const usedPct =
    event && event.budget > 0 && budget?.subtotal != null ? Math.min(100, Math.round((budget.subtotal / event.budget) * 100)) : 0;
  const brief = filledBrief(event);
  const graphLive = phase === "running" || latest.size > 0;
  const mission = missionLine(event);

  return (
    <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
      <div className="flex flex-col gap-6 lg:col-span-8">
        <div className="relative overflow-hidden rounded-lg border-2 border-black bg-nb-yellow p-5 shadow-nb-lg md:p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border-2 border-black bg-nb-magenta text-white shadow-nb-sm">
              <Sparkles size={22} />
            </div>
            <div>
              <div className="mb-2 inline-flex items-center gap-1.5 rounded bg-black px-2 py-0.5 font-mono text-xs font-bold uppercase tracking-wider text-white">
                <span className="inline-block h-2 w-2 rounded-full bg-nb-green" />
                {phase || "intake"}
              </div>
              <h1 className="mb-2 font-display text-xl font-extrabold leading-tight md:text-2xl lg:text-3xl">{mission}</h1>
              <p className="font-sans text-sm font-semibold leading-relaxed text-black/90 md:text-base">
                {phaseCopy(phase, event)}
              </p>
            </div>
          </div>
        </div>

        {event?.status === "archived" && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border-2 border-black bg-nb-pink px-4 py-3 shadow-nb">
            <p className="font-display text-sm font-extrabold uppercase">Archived — planning is paused</p>
            <button
              type="button"
              onClick={async () => {
                if (!eventId) return;
                await api(`/api/events/${eventId}/restore`, { method: "POST" });
                await refreshPlanner();
              }}
              className="rounded border-2 border-black bg-white px-3 py-1.5 font-display text-xs font-extrabold uppercase shadow-nb-sm"
            >
              Restore
            </button>
          </div>
        )}

        {graphLive ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {PIPELINE.map((name) => {
            const r = latest.get(name);
            const status = r?.status || "idle";
            const running = status === "running";
            const done = status === "completed";
            const failed = status === "failed";
            return (
              <div
                key={name}
                className={`relative flex flex-col justify-between rounded-lg border-2 p-4 shadow-nb-lg md:p-5 ${
                  running
                    ? "border-black bg-nb-cyan-light md:col-span-2"
                    : failed
                      ? "border-black bg-nb-pink"
                      : done
                        ? "border-black bg-white"
                        : "border-dashed border-black bg-white/80 md:col-span-2"
                }`}
              >
                <div>
                  <div className="mb-2.5 flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      {running ? (
                        <div className="relative flex h-3.5 w-3.5">
                          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-nb-magenta opacity-75" />
                          <span className="relative inline-flex h-3.5 w-3.5 rounded-full border border-black bg-nb-magenta" />
                        </div>
                      ) : (
                        <div
                          className={`flex h-7 w-7 items-center justify-center rounded border-2 border-black shadow-nb-sm ${
                            done ? "bg-nb-green" : failed ? "bg-nb-magenta text-white" : "bg-black/10"
                          }`}
                        >
                          {done ? <Check size={14} /> : <Loader2 size={14} />}
                        </div>
                      )}
                      <h3 className="font-display text-lg font-black capitalize">{name}</h3>
                    </div>
                    <span
                      className={`rounded border-2 px-2 py-0.5 font-mono text-xs font-black uppercase shadow-nb-sm ${
                        running
                          ? "border-black bg-nb-yellow"
                          : done
                            ? "border-black bg-nb-green/30"
                            : failed
                              ? "border-black bg-white"
                              : "border-black/40 bg-black/10 text-black/70"
                      }`}
                    >
                      {status}
                    </span>
                  </div>
                  <p className="mb-3 font-sans text-sm font-medium text-black/80">
                    {r?.output_summary || r?.task || "Waiting for this stage to start."}
                  </p>
                </div>
                {running && live.slice(-1)[0] && (
                  <div className="flex items-center gap-2 rounded-lg border-2 border-black bg-white p-3 font-mono text-xs font-bold shadow-nb-sm">
                    <Bot size={14} className="text-nb-magenta" />
                    {live.slice(-1)[0]}
                  </div>
                )}
                <div className="mt-2 inline-block w-fit rounded border border-black/30 bg-nb-bg px-2 py-1 font-mono text-xs font-bold text-black/70">
                  {r?.duration_ms ? `⏱ ${r.duration_ms}ms` : running ? "⏱ running" : "⏱ idle"}
                </div>
              </div>
            );
          })}
        </div>
        ) : (
          <div className="rounded-lg border-2 border-dashed border-black bg-white p-4 shadow-nb">
            <p className="mb-3 font-display text-sm font-extrabold uppercase">Planning team idle</p>
            <p className="mb-4 font-sans text-sm font-semibold text-black/70">
              Requirements → Venue → Vendor → Budget → Schedule → Logistics → Risk → Critic start after you tap Proceed.
            </p>
            <div className="flex flex-wrap gap-2">
              {PIPELINE.map((name) => (
                <span key={name} className="rounded border-2 border-black bg-nb-bg px-2 py-1 font-mono text-[10px] font-black uppercase">
                  {name}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="mt-2 flex flex-col rounded-lg border-2 border-black bg-white shadow-nb-lg">
          <div className="flex items-center justify-between border-b-2 border-black bg-nb-yellow p-3.5">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded border-2 border-black bg-white shadow-nb-sm">
                <Bot size={14} />
              </div>
              <h3 className="font-display text-base font-black md:text-lg">Agent Communications</h3>
            </div>
            <span className="rounded border border-black bg-white px-2 py-0.5 font-mono text-[11px] font-bold shadow-nb-sm">
              {busy ? "WORKING" : "ONLINE"}
            </span>
          </div>
          <div className="flex min-h-[160px] flex-col gap-3 bg-nb-bg p-4">
            {messages.map((m, i) => (
              <div key={i} className={`flex items-start gap-3 ${m.role === "user" ? "max-w-[92%] ml-auto flex-row-reverse" : "max-w-[92%]"}`}>
                {m.role === "assistant" && (
                  <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border-2 border-black bg-nb-cyan font-bold shadow-nb-sm">
                    <Bot size={18} />
                  </div>
                )}
                <div
                  className={`whitespace-pre-wrap rounded-lg border-2 border-black p-3.5 font-sans text-sm font-semibold leading-relaxed shadow-nb ${
                    m.role === "user" ? "rounded-tr-none bg-nb-magenta text-white" : "rounded-tl-none bg-white"
                  }`}
                >
                  {m.text}
                  {m.impact && (
                    <div className="mt-3 grid grid-cols-2 gap-1 border-t-2 border-black pt-2 font-mono text-[10px] font-bold uppercase">
                      {Object.entries(m.impact)
                        .filter(([k]) => !["change", "venue_from", "venue_to"].includes(k))
                        .map(([k, v]) => (
                          <span key={k}>
                            {k}: {String(v)}
                          </span>
                        ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="no-scrollbar sticky bottom-20 z-20 flex gap-2 overflow-x-auto border-t-2 border-black bg-white p-3 md:static md:bottom-auto">
            {actions.map((chip) => (
              <button
                key={chip.id}
                type="button"
                onClick={() => send(chip.id.startsWith("write_") ? "" : chip.label, chip.id)}
                className={`whitespace-nowrap rounded border-2 border-black px-3.5 py-1.5 font-display text-xs font-extrabold shadow-nb-sm active:translate-x-0.5 active:translate-y-0.5 ${
                  chip.id.startsWith("write_") ? "bg-white hover:bg-nb-bg" : "bg-nb-yellow hover:bg-nb-yellow-bright"
                }`}
              >
                {chip.label}
              </button>
            ))}
          </div>
          <form onSubmit={onSubmit} className="sticky bottom-4 z-20 border-t-2 border-black bg-white p-3 md:static md:bottom-auto">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                className="flex-1 rounded-lg border-2 border-black bg-white py-2.5 pl-3.5 pr-3 font-mono text-xs font-bold shadow-nb-sm placeholder-black/50 focus:outline-none focus:ring-2 focus:ring-nb-magenta md:text-sm"
                placeholder={hint}
              />
              <button
                disabled={busy}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border-2 border-black bg-nb-magenta text-white shadow-nb-sm hover:bg-black active:translate-x-0.5 active:translate-y-0.5 disabled:opacity-50"
              >
                <Send size={16} />
              </button>
            </div>
          </form>
        </div>
      </div>

      <aside className="flex flex-col gap-6 lg:col-span-4">
        <div className="sticky top-24 rounded-lg border-2 border-black bg-white p-5 shadow-nb-lg">
          <div className="mb-4 flex items-center justify-between border-b-2 border-black pb-3">
            <h2 className="flex items-center gap-2 font-display text-lg font-black">
              <div className="flex h-6 w-6 items-center justify-center rounded border-2 border-black bg-nb-cyan shadow-nb-sm">
                <Sparkles size={12} />
              </div>
              Event Summary
            </h2>
          </div>
          <div className="space-y-3.5">
            <SummaryRow icon={<MapPin size={16} />} tone="bg-nb-yellow" label="Location" value={brief.location || "TBD"} />
            <SummaryRow icon={<Users size={16} />} tone="bg-nb-pink" label="Attendees" value={brief.attendees ? `${brief.attendees} expected` : "TBD"} />
            <div className="rounded border-2 border-black bg-nb-bg p-2.5 shadow-nb-sm">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded border-2 border-black bg-nb-cyan font-bold">
                  <Wallet size={16} />
                </div>
                <div className="flex flex-1 items-end justify-between">
                  <div>
                    <div className="font-mono text-[10px] font-black uppercase text-black/60">Budget limit</div>
                    <div className="font-mono text-base font-black">
                      {brief.budget ? money(brief.budget, event?.currency) : "TBD"}
                    </div>
                  </div>
                  <span className="rounded border border-black bg-nb-green px-1.5 py-0.5 font-mono text-xs font-extrabold">
                    Allocated {usedPct}%
                  </span>
                </div>
              </div>
              <div className="h-3 overflow-hidden rounded-full border-2 border-black bg-white p-0.5">
                <div className="h-full rounded-full border-r border-black bg-nb-magenta" style={{ width: `${usedPct}%` }} />
              </div>
            </div>
          </div>
          <div className="mt-5 border-t-2 border-black pt-4">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h4 className="font-mono text-xs font-black uppercase tracking-wider">Risk assessment</h4>
              <Link
                to={`/events/${eventId}/risks`}
                className="flex items-center gap-1 rounded border-2 border-black bg-nb-pink px-2 py-0.5 font-mono text-xs font-black shadow-nb-sm"
              >
                {risks.length} Risks
              </Link>
            </div>
            <div className="space-y-2">
              {risks.slice(0, 3).map((r) => (
                <div
                  key={r.title}
                  className={`rounded border-2 border-black p-2.5 shadow-nb-sm ${
                    r.severity === "high" || r.severity === "critical" ? "bg-nb-pink/40" : "bg-nb-yellow/40"
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                    <span className="font-sans text-xs font-bold leading-snug">{r.title}</span>
                  </div>
                  <p className="mt-1 text-[11px] font-semibold leading-snug text-black/80">
                    {r.explanation || r.mitigation || ""}
                  </p>
                  {r.solutions?.[0] && (
                    <p className="mt-1 text-[11px] font-bold leading-snug">Solution: {r.solutions[0]}</p>
                  )}
                </div>
              ))}
              {risks.length === 0 && <p className="text-xs font-semibold text-black/60">No risks yet — run a plan.</p>}
            </div>
            {live.length > 0 && (
              <ol className="mt-4 max-h-40 space-y-1 overflow-auto font-mono text-[10px]">
                {live.slice(-8).map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}

function SummaryRow({ icon, tone, label, value }: { icon: React.ReactNode; tone: string; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded border-2 border-black bg-nb-bg p-2.5 shadow-nb-sm">
      <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded border-2 border-black font-bold ${tone}`}>{icon}</div>
      <div>
        <div className="font-mono text-[10px] font-black uppercase text-black/60">{label}</div>
        <div className="font-display text-sm font-extrabold">{value}</div>
      </div>
    </div>
  );
}
