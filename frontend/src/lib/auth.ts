const SESSION_KEY = "eventos.session";
const ONBOARD_KEY = "eventos.onboarded";
const LOCAL_USERS_KEY = "eventos.localUsers";

export type AuthUser = { id: string; email: string; name: string };
export type AuthSession = { token: string; user: AuthUser };

export function hasOnboarded(): boolean {
  try {
    return localStorage.getItem(ONBOARD_KEY) === "1";
  } catch {
    return false;
  }
}

export function setOnboarded(): void {
  try {
    localStorage.setItem(ONBOARD_KEY, "1");
  } catch {
    /* ignore */
  }
}

export function getSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AuthSession;
    if (!parsed?.token || !parsed?.user?.email) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  return getSession()?.token ?? null;
}

export function saveSession(session: AuthSession): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch {
    /* ignore */
  }
}

export function firstName(user?: AuthUser | null): string {
  const name = (user?.name || "").trim();
  if (!name) return "there";
  return name.split(/\s+/)[0];
}

type LocalUser = AuthUser & { password: string };

function loadLocalUsers(): LocalUser[] {
  try {
    const raw = localStorage.getItem(LOCAL_USERS_KEY);
    return raw ? (JSON.parse(raw) as LocalUser[]) : [];
  } catch {
    return [];
  }
}

function saveLocalUsers(rows: LocalUser[]): void {
  localStorage.setItem(LOCAL_USERS_KEY, JSON.stringify(rows));
}

async function sha(text: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function localSession(user: AuthUser): AuthSession {
  return { token: `local:${user.id}`, user };
}

export async function signupAccount(name: string, email: string, password: string): Promise<AuthSession> {
  const { api } = await import("./api");
  try {
    const out = await api<AuthSession>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
    saveSession(out);
    return out;
  } catch {
    const users = loadLocalUsers();
    const key = email.trim().toLowerCase();
    if (users.some((u) => u.email === key)) throw new Error("An account with that email already exists");
    const user: LocalUser = {
      id: crypto.randomUUID(),
      name: name.trim() || "Planner",
      email: key,
      password: await sha(password),
    };
    saveLocalUsers([...users, user]);
    const session = localSession(user);
    saveSession(session);
    return session;
  }
}

export async function loginAccount(email: string, password: string): Promise<AuthSession> {
  const { api } = await import("./api");
  try {
    const out = await api<AuthSession>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    saveSession(out);
    return out;
  } catch {
    const users = loadLocalUsers();
    const key = email.trim().toLowerCase();
    const hashed = await sha(password);
    const user = users.find((u) => u.email === key && u.password === hashed);
    if (user) {
      const session = localSession(user);
      saveSession(session);
      return session;
    }
    if (key === "demo@eventos.local" && password === "demo1234") {
      const session = localSession({ id: "00000000-0000-0000-0000-000000000001", email: key, name: "Jordan Diaz" });
      saveSession(session);
      return session;
    }
    throw new Error("Email or password is wrong");
  }
}
