import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Badge, EmptyState, ErrorState, PageKicker, Skeleton } from "../components/ui";

type Item = {
  id: string;
  title: string;
  start_time: string;
  end_time: string;
  location?: string;
  depends_on: string[];
  conflicts: string[];
};

export function TimelinePage() {
  const { eventId } = useParams();
  const [data, setData] = useState<{ items: Item[]; conflicts: string[] } | null>(null);
  const [tasks, setTasks] = useState<{ title: string; phase: string; owner?: string | null; depends_on?: string[] }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!eventId) return;
    api<{ items: Item[]; conflicts: string[] }>(`/api/events/${eventId}/schedule`)
      .then(setData)
      .catch((e) => setError(String(e)));
    api<{ title: string; phase: string; owner?: string | null; depends_on?: string[] }[]>(`/api/events/${eventId}/tasks`)
      .then(setTasks)
      .catch(() => setTasks([]));
  }, [eventId]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Skeleton className="h-64" />;
  if (!data.items?.length) return <EmptyState title="No timeline" hint="Generate a plan first." />;

  return (
    <div>
      <PageKicker>Schedule Grid</PageKicker>
      <h1 className="mb-2 font-display text-3xl font-extrabold uppercase tracking-tight">Timeline</h1>
      {tasks.length > 0 && (
        <p className="mb-4 text-sm font-semibold">
          Tasks by phase: {["setup", "load_in", "event", "teardown"].map((p) => `${p} ${tasks.filter((t) => t.phase === p).length}`).join(" · ")}
        </p>
      )}
      {data.conflicts?.length > 0 && (
        <p className="mb-4 rounded-lg border-2 border-black bg-nb-pink px-4 py-2 text-sm font-bold shadow-nb-sm">
          Conflicts: {data.conflicts.join(" · ")}
        </p>
      )}
      <ol className="space-y-4">
        {data.items.map((it, i) => (
          <li key={it.id} className="relative flex gap-4">
            <div className="flex w-8 flex-col items-center">
              <span
                className={`z-10 flex h-8 w-8 items-center justify-center rounded-full border-2 border-black font-mono text-xs font-black shadow-nb-sm ${
                  it.conflicts?.length ? "bg-nb-yellow-bright" : "bg-nb-cyan"
                }`}
              >
                {i + 1}
              </span>
              {i < data.items.length - 1 && <span className="w-1 flex-1 bg-black" />}
            </div>
            <article className="mb-1 flex-1 rounded-lg border-2 border-black bg-white p-4 shadow-nb">
              <p className="font-display text-lg font-extrabold">{it.title}</p>
              <p className="font-mono text-xs font-bold text-black/70">
                {new Date(it.start_time).toLocaleString()} → {new Date(it.end_time).toLocaleTimeString()}
              </p>
              {it.location && <p className="mt-1 text-sm font-semibold">{it.location}</p>}
              {it.depends_on?.length > 0 && (
                <p className="mt-1 text-xs font-semibold text-black/70">Depends on {it.depends_on.join(", ")}</p>
              )}
              {it.conflicts?.length > 0 && (
                <div className="mt-2">
                  <Badge tone="warn">conflict</Badge>
                </div>
              )}
            </article>
          </li>
        ))}
      </ol>
    </div>
  );
}
