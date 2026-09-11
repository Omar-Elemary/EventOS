import Constants from "expo-constants";
import AsyncStorage from "@react-native-async-storage/async-storage";

export const STORAGE_KEY = "eventos.apiBase";
export const DEMO_EVENT_ID = "11111111-1111-1111-1111-111111111111";

export function guessApiBase(): string {
  const hostUri = Constants.expoConfig?.hostUri || Constants.expoGoConfig?.debuggerHost || "";
  const host = hostUri.split(":")[0];
  if (host && host !== "localhost" && host !== "127.0.0.1") {
    return `http://${host}:8000`;
  }
  return "http://192.168.1.7:8000";
}

let base = guessApiBase();

export function getApiBase() {
  return base;
}

export function setApiBase(url: string) {
  base = url.replace(/\/$/, "");
}

export async function loadSavedApiBase() {
  const saved = await AsyncStorage.getItem(STORAGE_KEY);
  if (saved) setApiBase(saved);
  return getApiBase();
}

export async function persistApiBase(url: string) {
  setApiBase(url);
  await AsyncStorage.setItem(STORAGE_KEY, getApiBase());
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function pingApi(url?: string): Promise<boolean> {
  const root = (url ?? base).replace(/\/$/, "");
  try {
    const res = await fetch(`${root}/api/events`, { headers: { Accept: "application/json" } });
    return res.ok;
  } catch {
    return false;
  }
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
  copilot_state?: {
    phase?: string;
    missing_fields?: string[];
    requirements?: Record<string, unknown>;
    available_actions?: { id: string; label: string; payload?: Record<string, unknown> }[];
  } | null;
};

export type ChatAction = { id: string; label: string; payload?: Record<string, unknown> };

export type ChatOut = {
  reply: string;
  intent: string;
  run_id?: string | null;
  phase?: string | null;
  policy?: string | null;
  missing_fields?: string[];
  actions?: ChatAction[];
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
};

export function agentsForLatestRun(rows: AgentRun[]): AgentRun[] {
  if (!rows.length) return [];
  const runId = rows[rows.length - 1]?.run_id;
  if (!runId) return rows;
  return rows.filter((r) => r.run_id === runId);
}

const ACTIVE_EVENT_KEY = "eventos.activeEventId";

export async function getActiveEventId(): Promise<string> {
  const saved = await AsyncStorage.getItem(ACTIVE_EVENT_KEY);
  return saved || DEMO_EVENT_ID;
}

export async function setActiveEventId(id: string) {
  await AsyncStorage.setItem(ACTIVE_EVENT_KEY, id);
}

export async function deleteEvent(id: string): Promise<void> {
  await api<{ ok: boolean }>(`/api/events/${id}`, { method: "DELETE" });
  const current = await getActiveEventId();
  if (current === id) {
    await AsyncStorage.removeItem(ACTIVE_EVENT_KEY);
  }
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
      currency: "USD",
      user_request: note?.trim() || null,
    }),
  });
  await setActiveEventId(ev.id);
  return ev;
}
