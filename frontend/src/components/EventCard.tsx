import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, MapPin, Trash2 } from "lucide-react";
import { deleteEvent, type EventRecord } from "../lib/api";
import { filledBrief, money, progressFor, statusTone } from "../lib/eventDisplay";
import { Badge } from "./ui";

export function EventCard({ ev, onDeleted }: { ev: EventRecord; onDeleted?: (id: string) => void }) {
  const brief = filledBrief(ev);
  const pct = progressFor(ev);
  const phase = ev.copilot_state?.phase || "intake";
  const missing = ev.copilot_state?.missing_fields || [];
  const riskCount = Array.isArray(ev.plan_snapshot?.risks) ? (ev.plan_snapshot!.risks as unknown[]).length : 0;
  const [deleting, setDeleting] = useState(false);

  async function remove() {
    if (deleting) return;
    if (!window.confirm(`Delete “${ev.name}”? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await deleteEvent(ev.id);
      onDeleted?.(ev.id);
    } catch (err) {
      setDeleting(false);
      window.alert(err instanceof Error ? err.message : "Could not delete this event.");
    }
  }

  return (
    <article className="flex flex-col rounded-xl border-2 border-black bg-white p-4 shadow-nb-lg">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <h3 className="font-display text-lg font-extrabold leading-snug">{ev.name}</h3>
          <p className="mt-1 flex items-center gap-1 font-sans text-xs font-bold uppercase text-black/70">
            <MapPin size={12} /> {brief.location || "Location TBD"}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Badge tone={statusTone(ev.status)}>{ev.status}</Badge>
          <span className="font-mono text-[10px] font-black uppercase text-black/60">{phase}</span>
        </div>
      </div>
      <div className="mb-3 grid grid-cols-3 gap-2">
        <Mini label="People" value={brief.attendees != null ? String(brief.attendees) : "TBD"} />
        <Mini label="Days" value={brief.days != null ? String(brief.days) : "TBD"} />
        <Mini label="Budget" value={brief.budget != null ? money(brief.budget, ev.currency) : "TBD"} />
      </div>
      <div className="mb-2 flex items-center justify-between font-display text-[10px] font-bold uppercase">
        <span>Progress</span>
        <span className="rounded border border-black bg-nb-yellow px-1.5 py-0.5 font-mono">{pct}%</span>
      </div>
      <div className="mb-3 h-2.5 overflow-hidden rounded-full border-2 border-black bg-[#e5e5e5] p-px">
        <div className="h-full rounded-full bg-nb-magenta" style={{ width: `${pct}%` }} />
      </div>
      <p className="mb-3 font-sans text-xs font-semibold text-black/70">
        {missing.length ? `Still need: ${missing.join(", ")}` : riskCount ? `${riskCount} risk${riskCount === 1 ? "" : "s"} on the plan` : "Brief ready — open details or the planner"}
      </p>
      <div className="mt-auto flex gap-2">
        <Link
          to={`/events/${ev.id}`}
          className="flex flex-1 items-center justify-center gap-1 rounded-lg border-2 border-black bg-nb-yellow py-2 font-display text-xs font-extrabold uppercase shadow-nb-sm"
        >
          Details <ArrowRight size={12} />
        </Link>
        <Link
          to={`/events/${ev.id}/planner`}
          className="flex flex-1 items-center justify-center rounded-lg border-2 border-black bg-white py-2 font-display text-xs font-extrabold uppercase shadow-nb-sm"
        >
          Planner
        </Link>
        <button
          type="button"
          onClick={remove}
          disabled={deleting}
          className="inline-flex items-center justify-center rounded-lg border-2 border-black bg-white px-3 py-2 font-display text-xs font-extrabold uppercase text-nb-magenta shadow-nb-sm disabled:opacity-50"
          title="Delete event"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </article>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border-2 border-black bg-nb-bg p-1.5 text-center">
      <p className="font-mono text-[9px] font-black uppercase text-black/60">{label}</p>
      <p className="truncate font-display text-xs font-extrabold">{value}</p>
    </div>
  );
}
