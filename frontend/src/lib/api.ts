import { getToken } from "./auth";

const API = String(import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  return `${API}${path}`;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
  });
  const text = await res.text();
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`.trim();
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      if (typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      if (res.status === 404 && path.startsWith("/api")) {
        detail =
          "API not found (404). This static Vercel site has no FastAPI. Use the local app at http://127.0.0.1:5173, or rebuild with VITE_API_URL set to a hosted API.";
      }
    }
    throw new Error(detail);
  }
  if (text.trimStart().startsWith("<")) {
    throw new Error("API is not configured. Set VITE_API_URL to the FastAPI server.");
  }
  return JSON.parse(text) as T;
}

export type EventRecord = {
  id: string;
  name: string;
  location: string | null;
  attendees: number;
  duration_days: number;
  budget: number;
  currency: string;
  status: string;
  start_date: string | null;
  user_request: string | null;
  plan_snapshot: Record<string, unknown> | null;
  description?: string | null;
  objectives?: string[] | null;
  tags?: string[] | null;
  deadline?: string | null;
  data_mode?: string;
  event_state_version?: number;
  created_at?: string | null;
  updated_at?: string | null;
  archived_at?: string | null;
  copilot_state?: {
    phase?: string;
    missing_fields?: string[];
    graph_status?: string;
    requirements?: Record<string, unknown>;
    available_actions?: { id: string; label: string; payload?: Record<string, unknown> }[];
    last_simulation?: Record<string, unknown> | null;
  } | null;
};

export type ChatAction = { id: string; label: string; payload?: Record<string, unknown> };

export type ChatOut = {
  reply: string;
  intent: string;
  run_id?: string | null;
  simulation?: Record<string, unknown> | null;
  phase?: string | null;
  policy?: string | null;
  missing_fields?: string[];
  actions?: ChatAction[];
  event_id?: string | null;
  copilot_state?: EventRecord["copilot_state"];
};

export type AgentRun = {
  id: string;
  agent: string;
  status: string;
  task: string;
  input_summary: string;
  output_summary: string;
  duration_ms: number;
  iteration: number;
  errors: string[];
  run_id: string;
  timestamp?: string;
};

/** Keep pipeline cards on the current job so an old failed run is not shown as live status. */
export function latestRunId(rows: AgentRun[]): string | null {
  if (!rows.length) return null;
  return rows[rows.length - 1]?.run_id || null;
}

export function agentsForLatestRun(rows: AgentRun[]): AgentRun[] {
  const runId = latestRunId(rows);
  if (!runId) return [];
  return rows.filter((r) => r.run_id === runId);
}

export const DEMO_EVENT_ID = "11111111-1111-1111-1111-111111111111";
const ACTIVE_EVENT_KEY = "eventos.activeEventId";

function copilotCacheKey(eventId: string) {
  return `eventos.copilot.${eventId}`;
}

function eventCacheKey(eventId: string) {
  return `eventos.event.${eventId}`;
}

export function readCachedCopilot(eventId: string): EventRecord["copilot_state"] | null {
  try {
    const raw = sessionStorage.getItem(copilotCacheKey(eventId));
    return raw ? (JSON.parse(raw) as EventRecord["copilot_state"]) : null;
  } catch {
    return null;
  }
}

export function writeCachedCopilot(eventId: string, state: EventRecord["copilot_state"] | null | undefined) {
  if (!eventId || !state) return;
  try {
    sessionStorage.setItem(copilotCacheKey(eventId), JSON.stringify(state));
  } catch {
    /* ignore */
  }
}

export function readCachedEvent(eventId: string): EventRecord | null {
  try {
    const raw = sessionStorage.getItem(eventCacheKey(eventId));
    return raw ? (JSON.parse(raw) as EventRecord) : null;
  } catch {
    return null;
  }
}

export function writeCachedEvent(ev: EventRecord | null | undefined) {
  if (!ev?.id) return;
  try {
    sessionStorage.setItem(eventCacheKey(ev.id), JSON.stringify(ev));
    if (ev.copilot_state) writeCachedCopilot(ev.id, ev.copilot_state);
  } catch {
    /* ignore */
  }
}

export function getActiveEventId(): string {
  try {
    return localStorage.getItem(ACTIVE_EVENT_KEY) || DEMO_EVENT_ID;
  } catch {
    return DEMO_EVENT_ID;
  }
}

export function setActiveEventId(id: string) {
  try {
    localStorage.setItem(ACTIVE_EVENT_KEY, id);
  } catch {
    /* ignore */
  }
}

export function notifyEventsChanged() {
  window.dispatchEvent(new Event("eventos-events-changed"));
}

export async function deleteEvent(id: string): Promise<void> {
  await api<{ ok: boolean }>(`/api/events/${id}`, { method: "DELETE" });
  if (getActiveEventId() === id) {
    try {
      localStorage.removeItem(ACTIVE_EVENT_KEY);
    } catch {
      /* ignore */
    }
  }
  notifyEventsChanged();
}

export async function createBlankEvent(name: string, note?: string): Promise<EventRecord> {
  const ev = await api<EventRecord>("/api/events", {
    method: "POST",
    body: JSON.stringify({
      name: name.trim() || "Untitled event",
      location: null,
      attendees: 0,
      duration_days: 1,
      budget: 0,
      currency: "EGP",
      user_request: note?.trim() || null,
    }),
  });
  setActiveEventId(ev.id);
  writeCachedEvent(ev);
  return ev;
}
