import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, Check } from "lucide-react";
import { api, type AgentRun, agentsForLatestRun } from "../lib/api";

const PIPELINE = ["requirements", "venue", "vendor", "budget", "schedule", "logistics", "risk", "critic"] as const;

export function PipelineStrip({ eventId }: { eventId: string }) {
  const [agents, setAgents] = useState<AgentRun[]>([]);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api<AgentRun[]>(`/api/events/${eventId}/agents`)
        .then((rows) => {
          if (alive) setAgents(rows);
        })
        .catch(() => {});
    load();
    const t = setInterval(load, 2500);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [eventId]);

  const latest = new Map<string, AgentRun>();
  for (const r of agentsForLatestRun(agents)) latest.set(r.agent, r);
  const done = PIPELINE.filter((n) => latest.get(n)?.status === "completed").length;

  return (
    <section className="rounded-lg border-2 border-black bg-white p-4 shadow-nb">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-lg font-extrabold uppercase">Agent progress</h2>
        <Link
          to={`/events/${eventId}/agents`}
          className="font-mono text-xs font-black uppercase underline"
        >
          {done}/{PIPELINE.length} complete
        </Link>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {PIPELINE.map((name) => {
          const r = latest.get(name);
          const running = r?.status === "running";
          const ok = r?.status === "completed";
          const failed = r?.status === "failed";
          return (
            <div
              key={name}
              className={`rounded border-2 border-black px-2 py-2 ${
                running ? "bg-nb-cyan/40" : failed ? "bg-nb-pink" : ok ? "bg-nb-green/40" : "bg-nb-bg"
              }`}
            >
              <div className="mb-1 flex items-center gap-1">
                {ok ? <Check size={12} /> : <Bot size={12} />}
                <span className="font-display text-[11px] font-extrabold uppercase">{name}</span>
              </div>
              <p className="line-clamp-2 font-sans text-[10px] font-semibold text-black/70">
                {r?.output_summary || r?.status || "not started"}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
