import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Badge, BrutalButton, EmptyState, ErrorState, PageKicker, Skeleton } from "../components/ui";

type Decision = {
  id: string;
  problem: string;
  options: { id: string; label: string }[];
  consequences: string[];
  recommendation: string;
  status: string;
  chosen_option: string | null;
};

export function DecisionsPage() {
  const { eventId } = useParams();
  const [rows, setRows] = useState<Decision[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!eventId) return;
    const data = await api<Decision[]>(`/api/events/${eventId}/decisions`);
    setRows(data);
  }

  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, [eventId]);

  async function choose(id: string, optionId: string) {
    await api(`/api/events/${eventId}/decisions/${id}`, {
      method: "POST",
      body: JSON.stringify({ option_id: optionId }),
    });
    await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ event_id: eventId, action_id: optionId, message: "" }),
    });
    await load();
  }

  if (error) return <ErrorState message={error} />;
  if (!rows) return <Skeleton className="h-64" />;
  const open = rows.filter((r) => r.status === "open");

  return (
    <div>
      <PageKicker>Human choice required</PageKicker>
      <h1 className="mb-2 font-display text-3xl font-extrabold uppercase tracking-tight">Decision Center</h1>
      <p className="mb-6 font-semibold text-black/70">
        {open.length} decision{open.length === 1 ? "" : "s"} require your attention. Problem → Options → Consequences →
        Recommendation.
      </p>
      {rows.length === 0 ? (
        <EmptyState title="No open decisions" hint="The critic posts decisions here when the plan cannot approve." />
      ) : (
        <ul className="space-y-4">
          {rows.map((d) => (
            <li key={d.id} className="rounded-lg border-2 border-black bg-white p-5 shadow-nb-lg">
              <div className="mb-2 flex justify-between gap-2">
                <h2 className="font-display text-lg font-extrabold">{d.problem}</h2>
                <Badge tone={d.status === "open" ? "warn" : "ok"}>{d.status}</Badge>
              </div>
              <p className="mb-3 rounded border-2 border-black bg-nb-yellow/40 p-3 text-sm font-semibold">
                <span className="font-display font-extrabold uppercase">Recommendation: </span>
                {d.recommendation}
              </p>
              {d.consequences?.length > 0 && (
                <ul className="mb-3 list-disc pl-5 text-sm font-semibold">
                  {d.consequences.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              )}
              {d.status === "open" && (
                <div className="flex flex-wrap gap-2">
                  {(d.options || []).map((o) => (
                    <BrutalButton key={o.id} onClick={() => choose(d.id, o.id)}>
                      {o.label}
                    </BrutalButton>
                  ))}
                </div>
              )}
              {d.chosen_option && (
                <p className="mt-2 font-mono text-xs font-bold">Chosen: {d.chosen_option}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
