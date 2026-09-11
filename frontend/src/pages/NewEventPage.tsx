import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Sparkles } from "lucide-react";
import { createBlankEvent } from "../lib/api";
import { BrutalButton, PageKicker } from "../components/ui";

export function NewEventPage() {
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const title = name.trim();
    if (!title) {
      setError("Give the event a name.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const ev = await createBlankEvent(title, note);
      nav(`/events/${ev.id}/planner`, { replace: true });
    } catch (err) {
      setError(String(err));
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <PageKicker>Start from scratch</PageKicker>
      <h1 className="mb-2 font-display text-3xl font-extrabold uppercase tracking-tight md:text-4xl">New event</h1>
      <p className="mb-6 font-sans text-sm font-semibold text-black/75">
        Create a blank draft. The planner will ask for city, headcount, days, and budget in EGP — it will not copy the demo summit.
      </p>
      <form onSubmit={onSubmit} className="rounded-xl border-2 border-black bg-white p-5 shadow-nb-lg">
        <label className="mb-1 block font-mono text-[11px] font-black uppercase text-black/60">Event name</label>
        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Alexandria music weekend"
          className="mb-4 w-full rounded-lg border-2 border-black bg-nb-bg px-3 py-2.5 font-display text-sm font-bold shadow-nb-sm placeholder:text-black/40 focus:outline-none focus:ring-2 focus:ring-nb-magenta"
        />
        <label className="mb-1 block font-mono text-[11px] font-black uppercase text-black/60">Optional note</label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          placeholder="Anything you already know — or leave blank and tell the planner in chat."
          className="mb-4 w-full rounded-lg border-2 border-black bg-nb-bg px-3 py-2.5 font-sans text-sm font-semibold shadow-nb-sm placeholder:text-black/40 focus:outline-none focus:ring-2 focus:ring-nb-magenta"
        />
        {error && (
          <p className="mb-3 rounded border-2 border-black bg-nb-pink px-3 py-2 text-sm font-bold">{error}</p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <BrutalButton type="submit" disabled={busy}>
            <Sparkles size={14} /> {busy ? "Creating…" : "Create and open planner"}
          </BrutalButton>
          <Link
            to="/"
            className="inline-flex items-center gap-1 rounded-lg border-2 border-black bg-white px-4 py-2.5 font-display text-xs font-extrabold uppercase shadow-nb-sm"
          >
            <ArrowLeft size={14} /> Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
