import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Bot, Check, MapPin, Plus, ShieldAlert } from "lucide-react";
import { api, DEMO_EVENT_ID, type AgentRun, type EventRecord, agentsForLatestRun } from "../lib/api";
import { Badge, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { EventCard } from "../components/EventCard";
import { filledBrief, money, progressFor } from "../lib/eventDisplay";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export function DashboardPage() {
  const [events, setEvents] = useState<EventRecord[] | null>(null);
  const [agents, setAgents] = useState<AgentRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<EventRecord[]>("/api/events")
      .then(setEvents)
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!events?.length) {
      setAgents([]);
      return;
    }
    const featured = events.find((e) => e.id === DEMO_EVENT_ID) || events[0];
    api<AgentRun[]>(`/api/events/${featured.id}/agents`)
      .then(setAgents)
      .catch(() => setAgents([]));
  }, [events]);

  if (error) return <ErrorState message={error} />;
  if (!events) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
    );
  }

  const planned = events.reduce((s, e) => s + (e.budget || 0), 0);
  const risks = events.flatMap((e) => {
    const raw = e.plan_snapshot?.risks;
    return Array.isArray(raw) ? (raw as { severity?: string }[]) : [];
  });
  const high = risks.filter((r) => r.severity === "high" || r.severity === "critical").length;
  const featured = events.find((e) => e.id === DEMO_EVENT_ID) || events[0];
  const featuredRisks = (
    Array.isArray(featured?.plan_snapshot?.risks) ? (featured.plan_snapshot!.risks as { severity?: string }[]) : []
  ).filter((r) => r.severity === "high" || r.severity === "critical").length;
  const pct = featured ? progressFor(featured) : 0;
  const featuredBrief = featured ? filledBrief(featured) : null;
  const scoped = agentsForLatestRun(agents);
  const latest = new Map<string, AgentRun>();
  for (const a of scoped) latest.set(a.agent, a);
  const pipeline = ["requirements", "venue", "vendor", "budget", "schedule", "logistics", "risk", "critic"];
  const running = scoped.filter((a) => a.status === "running");

  return (
    <div>
      <div className="mb-6 pt-2">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 border-2 border-black bg-neo-cyan px-3 py-1 font-display text-xs font-bold uppercase tracking-wider shadow-neo-sm">
              <span className="h-2 w-2 rounded-full bg-black" />
              System Live • {events.length} Event{events.length === 1 ? "" : "s"} Active
            </div>
            <h1 className="mb-2 font-display text-4xl font-extrabold uppercase leading-[1.05] tracking-tight sm:text-5xl">
              {greeting()},
              <br />
              Omar
            </h1>
            <p className="font-sans text-base font-semibold text-black/80">
              Your AI planning team is working on {events.length} active event{events.length === 1 ? "" : "s"}.
            </p>
          </div>
          <Link
            to="/events/new"
            className="inline-flex items-center justify-center gap-2 rounded-lg border-2 border-black bg-nb-magenta px-4 py-3 font-display text-sm font-extrabold uppercase tracking-wider text-white shadow-nb hover:-translate-x-px hover:-translate-y-px"
          >
            <Plus size={16} /> New event
          </Link>
        </div>
      </div>

      <section className="mb-6 grid grid-cols-2 gap-3.5 sm:grid-cols-4">
        <Stat label="Active Events" value={String(events.length)} />
        <Stat label="Planned Budget" value={money(planned, events[0]?.currency || "EGP")} compact />
        <div className="relative overflow-hidden rounded-lg border-2 border-black bg-neo-cyan/20 p-3.5 shadow-neo">
          <p className="mb-1 font-display text-[11px] font-bold uppercase tracking-wider text-black/70">Planning Progress</p>
          <p className="font-display text-3xl font-extrabold sm:text-4xl">{pct}%</p>
          <div className="mt-2 h-2 overflow-hidden rounded-sm border border-black bg-white">
            <div className="h-full border-r border-black bg-neo-cyan" style={{ width: `${pct}%` }} />
          </div>
        </div>
        <Stat label="Open Risks" value={String(high)} accent={high > 0} />
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="rounded-xl border-2 border-black bg-white p-5 shadow-neo-lg lg:col-span-7">
          {featured ? (
            <>
              <div className="mb-4 flex items-start justify-between">
                <div>
                  <h2 className="font-display text-2xl font-extrabold leading-snug tracking-tight">{featured.name}</h2>
                  <p className="mt-0.5 flex items-center gap-1 font-sans text-xs font-bold uppercase text-black/75">
                    <MapPin size={14} /> {featuredBrief?.location || featured.location || "TBD"}
                  </p>
                </div>
                <Badge tone={featured.status === "approved" ? "ok" : featured.status === "planning" ? "info" : "neutral"}>
                  {featured.status}
                </Badge>
              </div>
              <div className="mb-5 grid grid-cols-3 gap-2.5">
                <MiniStat label="Attendees" value={featuredBrief?.attendees != null ? String(featuredBrief.attendees) : "TBD"} />
                <MiniStat label="Duration" value={featuredBrief?.days != null ? `${featuredBrief.days} days` : "TBD"} />
                <MiniStat label="Budget" value={featuredBrief?.budget != null ? money(featuredBrief.budget, featured.currency) : "TBD"} />
              </div>
              <div className="mb-5 rounded-lg border-2 border-black bg-white p-3 shadow-neo-sm">
                <div className="mb-1.5 flex items-center justify-between font-display text-xs font-bold uppercase">
                  <span>Overall Progress</span>
                  <span className="rounded border border-black bg-neo-yellow px-1.5 py-0.5 font-mono text-[11px]">{pct}%</span>
                </div>
                <div className="h-3 overflow-hidden rounded-full border-2 border-black bg-[#e5e5e5] p-px">
                  <div className="h-full rounded-full border-r-2 border-black bg-neo-yellow" style={{ width: `${pct}%` }} />
                </div>
              </div>
              {featuredRisks > 0 && (
                <div className="mb-5 flex items-center justify-between rounded-lg border-2 border-black bg-[#ffebee] p-3.5 shadow-neo-sm">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded border-2 border-black bg-neo-pink">
                      <ShieldAlert size={14} className="text-white" />
                    </div>
                    <span className="font-display text-xs font-bold uppercase sm:text-sm">
                      {featuredRisks} High Priority Risk{featuredRisks === 1 ? "" : "s"} Detected
                    </span>
                  </div>
                  <Link
                    to={`/events/${featured.id}/risks`}
                    className="rounded border-2 border-black bg-white px-2.5 py-1 font-display text-xs font-extrabold uppercase shadow-neo-sm hover:bg-neo-pink hover:text-white"
                  >
                    View
                  </Link>
                </div>
              )}
              <Link
                to={`/events/${featured.id}`}
                className="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-black bg-neo-yellow py-3.5 font-display text-sm font-extrabold uppercase tracking-wider shadow-neo transition-all hover:-translate-x-px hover:-translate-y-px hover:shadow-neo-lg active:translate-x-1 active:translate-y-1 active:shadow-none"
              >
                Open Event <ArrowRight size={16} />
              </Link>
            </>
          ) : (
            <>
              <EmptyState title="No events" hint="Start a blank event and tell the planner the brief." />
              <Link
                to="/events/new"
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border-2 border-black bg-nb-magenta py-3.5 font-display text-sm font-extrabold uppercase text-white shadow-neo"
              >
                <Plus size={16} /> New event
              </Link>
            </>
          )}
        </div>

        <div className="relative rounded-xl border-2 border-black bg-white p-5 shadow-neo-lg lg:col-span-5">
          <div className="mb-5 flex items-center justify-between border-b-2 border-black pb-3">
            <h2 className="flex items-center gap-2 font-display text-xl font-extrabold uppercase tracking-tight">
              <span className="flex h-7 w-7 items-center justify-center rounded border-2 border-black bg-neo-cyan shadow-neo-sm">
                <Bot size={14} />
              </span>
              AI Planning Team
            </h2>
            <span className="rounded-full border-2 border-black bg-neo-green px-2 py-0.5 font-display text-[11px] font-extrabold uppercase shadow-neo-sm">
              {running.length ? "Active" : "Idle"}
            </span>
          </div>
          <div className="space-y-3.5">
            {pipeline.map((name) => {
              const r = latest.get(name);
              const runningNow = r?.status === "running";
              const done = r?.status === "completed";
              const failed = r?.status === "failed";
              return (
                <div
                  key={name}
                  className={`flex items-start gap-3 rounded-lg border-2 p-2 ${
                    runningNow
                      ? "relative overflow-hidden border-black bg-neo-cyan/20 p-3 shadow-neo"
                      : failed
                        ? "border-black bg-[#ffebee]"
                        : done
                          ? "border-black bg-[#f9f7f4]"
                          : "border-black/40 bg-white"
                  }`}
                >
                  <div
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-black shadow-neo-sm ${
                      runningNow ? "bg-neo-cyan pulse-neo" : done ? "bg-neo-green" : failed ? "bg-neo-pink text-white" : "bg-[#e8e8e8]"
                    }`}
                  >
                    {done ? <Check size={14} /> : <Bot size={14} />}
                  </div>
                  <div className="flex-1">
                    <p className={`font-display text-sm font-bold ${runningNow ? "font-extrabold uppercase" : ""}`}>
                      {name} Agent
                    </p>
                    <p className="font-sans text-xs font-semibold text-black/70">
                      {r?.output_summary || r?.task || (r ? r.status : "Waiting for a planning run.")}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-5 border-t-2 border-black pt-3 text-center">
            <Link
              to={`/events/${featured?.id || DEMO_EVENT_ID}/agents`}
              className="inline-flex items-center justify-center gap-1 rounded border-2 border-black px-3 py-1.5 font-display text-xs font-extrabold uppercase shadow-neo-sm hover:bg-neo-yellow"
            >
              View Agent Activity <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <div className="mb-3 flex items-end justify-between gap-3">
          <h2 className="font-display text-sm font-extrabold uppercase tracking-wider">All events</h2>
          <Link to="/events" className="font-display text-xs font-extrabold uppercase underline">
            Browse details
          </Link>
        </div>
        {events.length === 0 ? (
          <EmptyState title="No events" hint="Start a blank event and tell the planner the brief." />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {events.map((ev) => (
              <EventCard key={ev.id} ev={ev} onDeleted={(id) => setEvents((rows) => (rows || []).filter((e) => e.id !== id))} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, compact, accent }: { label: string; value: string; compact?: boolean; accent?: boolean }) {
  return (
    <div
      className={`rounded-lg border-2 border-black p-3.5 shadow-neo transition-transform hover:-translate-x-px hover:-translate-y-px ${
        accent ? "bg-neo-pink/10" : "bg-white"
      }`}
    >
      <p className="mb-1 font-display text-[11px] font-bold uppercase tracking-wider text-black/70">{label}</p>
      <p className={`font-display font-extrabold ${compact ? "mt-1 text-2xl leading-tight sm:text-3xl" : "text-3xl sm:text-4xl"} ${accent ? "text-neo-pink" : ""}`}>
        {value}
      </p>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border-2 border-black bg-[#f5f2eb] p-2 text-center">
      <p className="font-display text-[10px] font-bold uppercase text-black/70">{label}</p>
      <p className="mt-0.5 font-mono text-base font-bold">{value}</p>
    </div>
  );
}
