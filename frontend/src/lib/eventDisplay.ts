import type { EventRecord } from "./api";

export function money(amount: number | null | undefined, currency?: string | null): string {
  if (amount == null || Number.isNaN(Number(amount))) return "TBD";
  const cur = (currency || "EGP").toUpperCase().replace("EGB", "EGP");
  const n = Number(amount).toLocaleString();
  if (cur === "USD") return `$${n}`;
  return `${n} ${cur}`;
}

export type FilledBrief = {
  location: string | null;
  attendees: number | null;
  days: number | null;
  budget: number | null;
  eventType: string | null;
};

export function filledBrief(ev: EventRecord | null | undefined): FilledBrief {
  const req = (ev?.copilot_state?.requirements || {}) as Record<string, unknown>;
  const location = String(req.location || ev?.location || "").trim() || null;
  const attendeesRaw = req.attendees ?? (ev && ev.attendees > 0 ? ev.attendees : null);
  const attendees = attendeesRaw != null && Number(attendeesRaw) > 0 ? Number(attendeesRaw) : null;
  const daysRaw = req.duration_days;
  const days = daysRaw != null && Number(daysRaw) > 0 ? Number(daysRaw) : null;
  const budgetRaw = req.budget ?? (ev && ev.budget > 0 ? ev.budget : null);
  const budget = budgetRaw != null && Number(budgetRaw) > 0 ? Number(budgetRaw) : null;
  const eventType = String(req.event_type || "").trim() || null;
  return { location, attendees, days, budget, eventType };
}

export function progressFor(ev: EventRecord): number {
  if (ev.status === "completed") return 100;
  if (ev.status === "approved" || ev.status === "preparing") return 90;
  if (ev.status === "in_progress") return 80;
  if (ev.status === "planning") return 65;
  if (ev.status === "needs_decision") return 55;
  if (ev.status === "archived") return 100;
  const f = filledBrief(ev);
  return [f.location, f.attendees, f.days, f.budget].filter(Boolean).length * 10;
}

export function missionLine(ev: EventRecord | null | undefined): string {
  if (!ev) return "Waiting for an event brief.";
  const f = filledBrief(ev);
  const kind = f.eventType || ev.name || "event";
  const bits: string[] = [];
  if (f.days) bits.push(`${f.days}-day ${kind}`);
  else bits.push(kind);
  if (f.location) bits.push(`in ${f.location}`);
  if (f.attendees) bits.push(`for ${f.attendees} people`);
  if (f.budget) bits.push(`${money(f.budget, ev?.currency)} budget`);
  return bits.join(" ");
}

export function phaseCopy(phase: string, ev: EventRecord | null): string {
  if (ev?.status === "archived") return "This event is archived. Restore it to keep planning.";
  if (phase === "running") {
    return "Agents are planning venues, vendors, budget, and risks. I’ll stop if I need a decision.";
  }
  if (phase === "confirm") return "Brief looks complete. Proceed to run the planning team, or edit anything first.";
  if (phase === "decide") return "The planners hit a blocker. Pick an action — nothing fails silently in the background.";
  if (phase === "done") return "Plan is ready. Inspect Budget, Timeline, and Risks, or ask a what-if.";
  return "Tell me city, headcount, duration, and budget in EGP. Agents stay idle until you confirm.";
}

export function statusTone(status: string): "neutral" | "ok" | "warn" | "bad" | "info" {
  if (status === "approved" || status === "completed") return "ok";
  if (status === "planning" || status === "in_progress") return "info";
  if (status === "needs_human_review" || status === "needs_decision") return "warn";
  if (status === "archived") return "neutral";
  return "neutral";
}

export const CHIP_HINTS: Record<string, string> = {
  add_location: "e.g. Cairo",
  add_attendees: "e.g. 500 attendees",
  add_days: "e.g. 1 day",
  add_budget: "e.g. 150000 EGP",
  add_date: "e.g. November 2026",
  add_format: "indoor, outdoor, or hybrid",
  add_overnight: "hotels needed, or daytime only",
  write_location: "Type a city",
  write_attendees: "e.g. 500",
  write_days: "e.g. 1",
  write_budget: "e.g. 150000",
  write_date: "e.g. November 2026",
  write_format: "indoor, outdoor, or hybrid",
  write_overnight: "hotels or daytime only",
};
