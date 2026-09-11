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
  return { location, attendees, days, budget };
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
