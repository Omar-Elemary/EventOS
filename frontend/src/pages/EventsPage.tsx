import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { api, type EventRecord } from "../lib/api";
import { EventCard } from "../components/EventCard";
import { EmptyState, ErrorState, PageKicker, Skeleton } from "../components/ui";

export function EventsPage() {
  const [events, setEvents] = useState<EventRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<EventRecord[]>("/api/events")
      .then(setEvents)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!events) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-56" />
        <Skeleton className="h-56" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <PageKicker>{events.length} event{events.length === 1 ? "" : "s"}</PageKicker>
          <h1 className="font-display text-3xl font-extrabold uppercase tracking-tight md:text-4xl">Events</h1>
          <p className="mt-2 font-sans text-sm font-semibold text-black/75">
            Open any event to see its brief, budget, risks, and planning progress.
          </p>
        </div>
        <Link
          to="/events/new"
          className="inline-flex items-center justify-center gap-2 rounded-lg border-2 border-black bg-nb-magenta px-4 py-3 font-display text-sm font-extrabold uppercase text-white shadow-nb"
        >
          <Plus size={16} /> New event
        </Link>
      </div>
      {events.length === 0 ? (
        <EmptyState title="No events yet" hint="Create a blank event and brief the planner." />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {events.map((ev) => (
              <EventCard key={ev.id} ev={ev} onDeleted={(id) => setEvents((rows) => (rows || []).filter((e) => e.id !== id))} />
            ))}
        </div>
      )}
    </div>
  );
}
