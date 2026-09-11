import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, Info, ScanSearch } from "lucide-react";
import { api } from "../lib/api";
import { Badge, BrutalButton, EmptyState, ErrorState, PageKicker, Skeleton } from "../components/ui";

type Risk = {
  title: string;
  severity: "low" | "medium" | "high" | "critical";
  probability: number;
  impact: string;
  description: string;
  mitigation: string;
  score?: number;
  owner?: string | null;
  status?: string;
  trigger?: string | null;
  ai_recommendation?: string | null;
  explanation?: string | null;
  solutions?: string[] | null;
};

const order = ["critical", "high", "medium", "low"] as const;

export function RisksPage() {
  const { eventId } = useParams();
  const [rows, setRows] = useState<Risk[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!eventId) return;
    api<Risk[]>(`/api/events/${eventId}/risks`)
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, [eventId]);

  if (error) return <ErrorState message={error} />;
  if (!rows) return <Skeleton className="h-64" />;
  if (!rows.length) return <EmptyState title="No risks" hint="Risks appear after a planning run." />;

  const counts = {
    critical: rows.filter((r) => r.severity === "critical").length,
    high: rows.filter((r) => r.severity === "high").length,
    medium: rows.filter((r) => r.severity === "medium").length,
    low: rows.filter((r) => r.severity === "low").length,
  };
  const active = counts.critical + counts.high;
  const level = counts.critical ? "CRITICAL" : counts.high ? "ELEVATED" : counts.medium ? "WATCH" : "STABLE";

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <PageKicker>System Threat Level: {level}</PageKicker>
          <h1 className="font-display text-3xl font-extrabold uppercase leading-none tracking-tight sm:text-4xl">Risk Center</h1>
          <p className="mt-1 font-sans text-xs font-bold uppercase tracking-wide text-black/80 sm:text-sm">
            Why each risk matters, and numbered actions you can take next
          </p>
        </div>
        <Link to={`/events/${eventId}/planner`}>
          <BrutalButton>
            <ScanSearch size={16} /> Run Diagnostic
          </BrutalButton>
        </Link>
      </section>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <CountCard label="Critical" value={counts.critical} tone="bg-white" />
        <CountCard label="High" value={counts.high} tone="bg-nb-pink" accent="text-nb-magenta" />
        <CountCard label="Medium" value={counts.medium} tone="bg-nb-yellow" />
        <CountCard label="Low" value={counts.low} tone="bg-nb-green/40" />
      </section>

      <section className="flex w-full flex-col gap-5">
        <div className="flex items-center justify-between border-b-2 border-black pb-2">
          <h2 className="flex items-center gap-2 font-display text-lg font-extrabold uppercase tracking-tight sm:text-xl">
            <span className="inline-block h-3 w-3 border border-black bg-nb-magenta" />
            Active Mitigation Protocols
          </h2>
          <span className="rounded border-2 border-black bg-white px-2 py-0.5 font-mono text-xs font-black shadow-nb-sm">
            {active} ACTIVE
          </span>
        </div>
        {order.map((sev) => {
          const group = rows.filter((r) => r.severity === sev);
          if (!group.length) return null;
          return (
            <div key={sev} className="space-y-3">
              {group.map((r) => (
                <article
                  key={r.title}
                  className={`rounded-lg border-2 border-black p-5 shadow-nb-lg ${
                    sev === "critical" || sev === "high" ? "bg-[#ffebee]" : sev === "medium" ? "bg-nb-yellow/30" : "bg-white"
                  }`}
                >
                  <div className="flex justify-between gap-2">
                    <h3 className="flex items-center gap-2 font-display text-lg font-extrabold">
                      {sev === "low" ? <Info size={16} /> : <AlertTriangle size={16} />}
                      {r.title}
                    </h3>
                    <Badge tone={sev === "critical" || sev === "high" ? "bad" : sev === "medium" ? "warn" : "ok"}>
                      {sev} · p={Math.round(r.probability * 100)}% · score {r.score ?? "—"}
                    </Badge>
                  </div>
                  <p className="mt-3 font-display text-xs font-extrabold uppercase tracking-wide">Why it matters</p>
                  <p className="mt-1 text-sm font-semibold leading-relaxed">{r.explanation || r.description}</p>
                  <p className="mt-2 text-sm font-semibold text-black/70">
                    <span className="font-display font-extrabold uppercase">If it hits: </span>
                    {r.impact}
                  </p>
                  {r.trigger && <p className="mt-1 font-mono text-xs font-bold">Trigger: {r.trigger}</p>}
                  <p className="mt-1 font-mono text-xs font-bold">
                    Owner: {r.owner || "Operations"} · {r.status || "open"}
                  </p>
                  <div className="mt-3 rounded-lg border-2 border-black bg-white p-3 shadow-nb-sm">
                    <p className="font-display text-xs font-extrabold uppercase tracking-wide">Suggested solutions</p>
                    <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-sm font-semibold">
                      {(r.solutions && r.solutions.length ? r.solutions : [r.ai_recommendation || r.mitigation].filter(Boolean)).map(
                        (s) => (
                          <li key={s}>{s}</li>
                        ),
                      )}
                    </ol>
                  </div>
                </article>
              ))}
            </div>
          );
        })}
      </section>
    </div>
  );
}

function CountCard({ label, value, tone, accent }: { label: string; value: number; tone: string; accent?: string }) {
  return (
    <div className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-black p-3.5 text-center shadow-nb transition-transform hover:-translate-x-px hover:-translate-y-px ${tone}`}>
      <span className={`font-display text-3xl font-extrabold leading-none sm:text-4xl ${accent ?? ""}`}>{value}</span>
      <span className="mt-1.5 rounded border border-black bg-white px-1.5 font-mono text-[11px] font-black uppercase tracking-wider">
        {label}
      </span>
    </div>
  );
}
