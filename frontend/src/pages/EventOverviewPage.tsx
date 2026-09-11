import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Sparkles, Plus, Trash2 } from "lucide-react";
import { api, deleteEvent, type EventRecord, setActiveEventId } from "../lib/api";
import { filledBrief, money, progressFor } from "../lib/eventDisplay";
import { Badge, BrutalButton, ErrorState, PageKicker, Skeleton } from "../components/ui";
import { PipelineStrip } from "../components/PipelineStrip";

type Activity = { id: string; at: string; actor: string; summary: string; state_version: number };

export function EventOverviewPage() {
  const { eventId } = useParams();
  const nav = useNavigate();
  const [ev, setEv] = useState<EventRecord | null>(null);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [risks, setRisks] = useState<
    { title: string; severity: string; explanation?: string; solutions?: string[]; mitigation?: string }[]
  >([]);
  const [budget, setBudget] = useState<{ remaining?: number; subtotal?: number; explanation?: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [objectives, setObjectives] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function load() {
    if (!eventId) return;
    const event = await api<EventRecord>(`/api/events/${eventId}`);
    setEv(event);
    setDescription(event.description || "");
    setObjectives((event.objectives || []).join("\n"));
    api<Activity[]>(`/api/events/${eventId}/activity`).then(setActivity).catch(() => setActivity([]));
    api<{ title: string; severity: string; explanation?: string; solutions?: string[]; mitigation?: string }[]>(
      `/api/events/${eventId}/risks`,
    )
      .then(setRisks)
      .catch(() => setRisks([]));
    api<{ remaining?: number; subtotal?: number; explanation?: string[] }>(`/api/events/${eventId}/budget`)
      .then(setBudget)
      .catch(() => setBudget(null));
  }

  useEffect(() => {
    if (!eventId) return;
    setActiveEventId(eventId);
    load().catch((e) => setError(String(e)));
  }, [eventId]);

  if (error) return <ErrorState message={error} />;
  if (!ev) return <Skeleton className="h-64" />;

  const brief = filledBrief(ev);
  const pct = progressFor(ev);

  async function saveBrief() {
    setSaving(true);
    try {
      await api(`/api/events/${ev!.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          description,
          objectives: objectives
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean),
        }),
      });
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function setMode(mode: string) {
    await api(`/api/events/${ev!.id}`, { method: "PATCH", body: JSON.stringify({ data_mode: mode }) });
    await load();
  }

  async function duplicate() {
    const copy = await api<EventRecord>(`/api/events/${ev!.id}/duplicate`, { method: "POST" });
    window.location.href = `/events/${copy.id}`;
  }

  async function remove() {
    if (deleting) return;
    if (!window.confirm(`Delete “${ev.name}”? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await deleteEvent(ev.id);
      nav("/events", { replace: true });
    } catch (err) {
      setDeleting(false);
      window.alert(err instanceof Error ? err.message : "Could not delete this event.");
    }
  }

  return (
    <div>
      <PageKicker>
        {ev.status} · {ev.copilot_state?.phase || "intake"} · v{ev.event_state_version ?? 0} ·{" "}
        {ev.data_mode === "live" ? "Live Egypt Data" : "Mock Demo Data"}
      </PageKicker>
      <div className="mb-10 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="font-display text-3xl font-extrabold uppercase tracking-tight md:text-5xl">{ev.name}</h1>
          <p className="mt-3 font-sans text-base font-semibold text-black/75">
            {[brief.location || "Location TBD", brief.attendees ? `${brief.attendees} attendees` : "Headcount TBD", brief.days ? `${brief.days} day${brief.days === 1 ? "" : "s"}` : "Duration TBD"]
              .join(" · ")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setMode(ev.data_mode === "live" ? "mock" : "live")}
            className="rounded-lg border-2 border-black bg-white px-3 py-2 font-display text-xs font-extrabold uppercase shadow-nb"
          >
            {ev.data_mode === "live" ? "Switch to mock" : "Live Egypt Data"}
          </button>
          <button onClick={duplicate} className="rounded-lg border-2 border-black bg-white px-3 py-2 font-display text-xs font-extrabold uppercase shadow-nb">
            Duplicate
          </button>
          <button
            onClick={remove}
            disabled={deleting}
            className="inline-flex items-center gap-1 rounded-lg border-2 border-black bg-white px-3 py-2 font-display text-xs font-extrabold uppercase text-nb-magenta shadow-nb disabled:opacity-50"
          >
            <Trash2 size={14} /> {deleting ? "Deleting…" : "Delete"}
          </button>
          {ev.status === "archived" ? (
            <button
              onClick={async () => {
                await api(`/api/events/${ev.id}/restore`, { method: "POST" });
                await load();
              }}
              className="rounded-lg border-2 border-black bg-nb-yellow px-3 py-2 font-display text-xs font-extrabold uppercase shadow-nb"
            >
              Restore
            </button>
          ) : (
            <button
              onClick={async () => {
                await api(`/api/events/${ev.id}/archive`, { method: "POST" });
                nav("/", { replace: true });
              }}
              className="rounded-lg border-2 border-black bg-white px-3 py-2 font-display text-xs font-extrabold uppercase shadow-nb"
            >
              Archive
            </button>
          )}
          <Link
            to="/events/new"
            className="inline-flex items-center gap-1 rounded-lg border-2 border-black bg-white px-4 py-2.5 font-display text-xs font-extrabold uppercase tracking-wider shadow-nb"
          >
            <Plus size={14} /> New event
          </Link>
          <Link to={`/events/${ev.id}/planner`}>
            <BrutalButton>
              <Sparkles size={14} /> Ask AI
            </BrutalButton>
          </Link>
        </div>
      </div>

      <section className="mb-8 grid grid-cols-2 gap-3.5 md:grid-cols-4">
        <Metric label="Budget" value={brief.budget ? money(brief.budget, ev.currency) : "TBD"} />
        <Metric label="Planned spend" value={budget?.subtotal != null ? money(budget.subtotal, ev.currency) : "—"} />
        <Metric label="Remaining" value={budget?.remaining != null ? money(budget.remaining, ev.currency) : "—"} />
        <Metric label="Key risks" value={String(risks.length)} accent={risks.length > 0} />
      </section>

      <div className="mb-4 rounded-lg border-2 border-black bg-white p-4 shadow-nb">
        <div className="mb-1.5 flex items-center justify-between font-display text-xs font-bold uppercase">
          <span>Overall Progress</span>
          <span className="rounded border border-black bg-neo-yellow px-1.5 py-0.5 font-mono text-[11px]">{pct}%</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full border-2 border-black bg-[#e5e5e5] p-px">
          <div className="h-full rounded-full border-r-2 border-black bg-neo-yellow" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="mb-8">
        <PipelineStrip eventId={ev.id} />
      </div>

      <section className="mb-8 rounded-lg border-2 border-black bg-white p-5 shadow-nb">
        <h2 className="mb-3 font-display text-xl font-extrabold uppercase">Event brief</h2>
        <p className="mb-3 text-sm font-semibold text-black/70">
          Optional fields improve the plan. The copilot still only asks for city, headcount, duration, and budget.
        </p>
        <label className="mb-1 block font-mono text-xs font-extrabold uppercase">Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="mb-3 w-full rounded-lg border-2 border-black p-2 text-sm font-semibold"
          rows={3}
        />
        <label className="mb-1 block font-mono text-xs font-extrabold uppercase">Objectives (one per line)</label>
        <textarea
          value={objectives}
          onChange={(e) => setObjectives(e.target.value)}
          className="mb-3 w-full rounded-lg border-2 border-black p-2 text-sm font-semibold"
          rows={3}
        />
        <BrutalButton disabled={saving} onClick={saveBrief}>
          Save brief
        </BrutalButton>
      </section>

      <div className="mb-3 flex items-end justify-between gap-3">
        <h2 className="font-display text-xl font-extrabold uppercase">Key risks</h2>
        <Link to={`/events/${eventId}/risks`} className="font-mono text-xs font-black uppercase underline">
          Risk Center
        </Link>
      </div>
      <ul className="mb-8 space-y-2">
        {risks.slice(0, 5).map((r) => (
          <li key={r.title} className="rounded-lg border-2 border-black bg-white px-4 py-3 shadow-nb-sm">
            <div className="flex justify-between gap-3">
              <span className="font-display font-bold">{r.title}</span>
              <Badge tone={r.severity === "critical" || r.severity === "high" ? "bad" : r.severity === "medium" ? "warn" : "ok"}>
                {r.severity}
              </Badge>
            </div>
            <p className="mt-2 text-sm font-semibold leading-relaxed text-black/80">
              {r.explanation || r.mitigation || "See Risk Center for details."}
            </p>
            {r.solutions?.[0] && (
              <p className="mt-1 text-sm font-semibold">
                <span className="font-display font-extrabold uppercase">Try: </span>
                {r.solutions[0]}
              </p>
            )}
          </li>
        ))}
        {risks.length === 0 && (
          <p className="rounded-lg border-2 border-dashed border-black bg-white p-4 text-sm font-semibold">
            No risks yet — run the planner.
          </p>
        )}
      </ul>

      <h2 className="mb-3 font-display text-xl font-extrabold uppercase">Activity</h2>
      <ol className="space-y-2">
        {activity.slice(0, 20).map((a) => (
          <li key={a.id} className="rounded-lg border-2 border-black bg-white px-4 py-2 text-sm font-semibold shadow-nb-sm">
            <span className="font-mono text-xs font-bold">{a.at ? new Date(a.at).toLocaleTimeString() : ""}</span>{" "}
            <span className="font-display font-extrabold uppercase">{a.actor}</span> — {a.summary}
          </li>
        ))}
        {activity.length === 0 && <p className="text-sm font-semibold text-black/70">No activity yet.</p>}
      </ol>
    </div>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`rounded-lg border-2 border-black p-5 shadow-nb ${accent ? "bg-neo-pink/10" : "bg-white"}`}>
      <p className="font-display text-xs font-bold uppercase tracking-wider text-black/70">{label}</p>
      <p className={`mt-1 font-display text-xl font-extrabold ${accent ? "text-neo-pink" : ""}`}>{value}</p>
    </div>
  );
}
