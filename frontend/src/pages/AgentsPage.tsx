import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Activity, Check, Download, Pause } from "lucide-react";
import { api, type AgentRun, agentsForLatestRun } from "../lib/api";
import { Badge, BrutalButton, EmptyState, ErrorState, PageKicker, Skeleton } from "../components/ui";

const PIPELINE = ["requirements", "orchestrator", "venue", "vendor", "budget", "schedule", "logistics", "risk", "critic"];

export function AgentsPage() {
  const { eventId } = useParams();
  const [rows, setRows] = useState<AgentRun[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!eventId) return;
    const load = () =>
      api<AgentRun[]>(`/api/events/${eventId}/agents`)
        .then(setRows)
        .catch((e) => setError(String(e)));
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [eventId]);

  if (error) return <ErrorState message={error} />;
  if (!rows) return <Skeleton className="h-64" />;

  const latest = new Map<string, AgentRun>();
  for (const r of agentsForLatestRun(rows)) latest.set(r.agent, r);
  const doneCount = PIPELINE.filter((n) => latest.get(n)?.status === "completed").length;
  const running = rows.some((r) => r.status === "running");

  function exportLogs() {
    const blob = new Blob([JSON.stringify(rows, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "eventos-agent-logs.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col justify-between gap-4 rounded-xl border-2 border-black bg-white p-5 shadow-nb-lg md:flex-row md:items-center">
        <div>
          <PageKicker>
            Pipeline {running ? "Active" : "Idle"} • {rows.length} runs
          </PageKicker>
          <h1 className="font-display text-2xl font-extrabold leading-tight tracking-tight md:text-3xl lg:text-4xl">
            Agent Activity Workflow
          </h1>
          <p className="mt-0.5 font-sans text-sm font-semibold text-black/80 md:text-base">
            Summaries only — no hidden chain-of-thought.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <BrutalButton className="flex-1 md:flex-none" onClick={() => {}}>
            <Pause size={14} /> Pause Run
          </BrutalButton>
          <button
            onClick={exportLogs}
            className="flex flex-1 items-center justify-center gap-2 rounded-lg border-2 border-black bg-nb-cyan px-4 py-2.5 font-display text-xs font-black uppercase tracking-wider shadow-nb active:translate-x-0.5 active:translate-y-0.5 md:flex-none md:text-sm"
          >
            <Download size={14} /> Export Logs
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border-2 border-black bg-white p-5 shadow-nb-lg">
        <div className="mb-6 flex items-center justify-between border-b-2 border-black pb-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded border-2 border-black bg-nb-yellow shadow-nb-sm">
              <Activity size={14} />
            </div>
            <h2 className="font-display text-lg font-extrabold uppercase tracking-tight md:text-xl">Execution Flow</h2>
          </div>
          <span className="rounded border-2 border-black bg-black px-2.5 py-1 font-mono text-xs font-black uppercase tracking-wide text-white">
            Stage {doneCount} of {PIPELINE.length}
          </span>
        </div>
        <div className="no-scrollbar overflow-x-auto pb-2">
          <ol className="flex min-w-[720px] items-center gap-2">
            {PIPELINE.map((name, i) => {
              const r = latest.get(name);
              const done = r?.status === "completed";
              const run = r?.status === "running";
              const fail = r?.status === "failed";
              return (
                <li key={name} className="flex items-center gap-2">
                  <div
                    className={`flex min-w-[88px] flex-col items-center rounded-lg border-2 border-black px-2 py-2 shadow-nb-sm ${
                      run ? "bg-nb-cyan pulse-neo" : done ? "bg-nb-green" : fail ? "bg-nb-magenta text-white" : "bg-[#f4efe6]"
                    }`}
                  >
                    <span className="font-display text-[10px] font-extrabold uppercase">{name}</span>
                    <span className="font-mono text-[9px] font-bold">{r ? r.status : "idle"}</span>
                  </div>
                  {i < PIPELINE.length - 1 && <span className="h-1.5 w-4 bg-black" />}
                </li>
              );
            })}
          </ol>
        </div>
      </div>

      {rows.length === 0 ? (
        <EmptyState title="No agent runs" hint="Queue a plan from the AI Planner." />
      ) : (
        <ul className="space-y-2">
          {rows
            .slice()
            .reverse()
            .map((r) => (
              <li key={r.id} className="rounded-lg border-2 border-black bg-white shadow-nb">
                <button
                  className="flex w-full justify-between gap-3 px-4 py-3 text-left"
                  onClick={() => setOpen(open === r.id ? null : r.id)}
                >
                  <span className="flex items-center gap-2 font-mono text-sm font-bold">
                    {r.status === "completed" ? <Check size={14} /> : <Activity size={14} />} {r.agent} · iter {r.iteration}
                  </span>
                  <span className="font-mono text-xs font-bold">{r.duration_ms}ms</span>
                </button>
                {open === r.id && (
                  <div className="space-y-2 border-t-2 border-black px-4 py-4 text-sm">
                    <Badge tone={r.status === "completed" ? "ok" : r.status === "failed" ? "bad" : "info"}>{r.status}</Badge>
                    <p>
                      <span className="font-display font-extrabold uppercase">Task: </span>
                      {r.task}
                    </p>
                    <p>
                      <span className="font-display font-extrabold uppercase">In: </span>
                      {r.input_summary}
                    </p>
                    <p>
                      <span className="font-display font-extrabold uppercase">Out: </span>
                      {r.output_summary}
                    </p>
                      {r.errors?.length ? (
                        <p className="rounded border-2 border-black bg-nb-pink p-2 font-semibold">
                          Reason: {r.errors.join(" · ")}
                        </p>
                      ) : null}
                  </div>
                )}
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}
