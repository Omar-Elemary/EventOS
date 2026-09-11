import { useEffect, useMemo, useState } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Badge, BrutalButton, CredibilityBadge, EmptyState, ErrorState, PageKicker, Skeleton } from "../components/ui";

type Venue = {
  id: string;
  name: string;
  location: string;
  capacity: number;
  estimated_cost: number;
  facilities: string[];
  suitability_score?: number;
  source_type?: string;
  source_tier?: string;
  price_type?: string;
  requires_quote?: boolean;
  last_checked_at?: string | null;
  status?: string;
  extra?: { suitability_score?: number; pros?: string[]; cons?: string[] };
};

export function VenuesPage() {
  const { eventId } = useParams();
  const [rows, setRows] = useState<Venue[] | null>(null);
  const [q, setQ] = useState("");
  const [minCap, setMinCap] = useState(0);
  const [maxCost, setMaxCost] = useState(0);
  const [compare, setCompare] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const path = eventId ? `/api/events/${eventId}/venues` : "/api/venues";
    api<Venue[]>(path)
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, [eventId]);

  const filtered = useMemo(() => {
    return (rows || []).filter(
      (v) =>
        v.capacity >= minCap &&
        (maxCost === 0 || v.estimated_cost <= maxCost) &&
        (v.name.toLowerCase().includes(q.toLowerCase()) || v.location.toLowerCase().includes(q.toLowerCase())),
    );
  }, [rows, q, minCap, maxCost]);

  if (error) return <ErrorState message={error} />;
  if (!rows) return <Skeleton className="h-64" />;
  if (!rows.length) return <EmptyState title="No venues seeded" hint="Start the API so demo catalog loads." />;

  const compared = rows.filter((v) => compare.includes(v.id));

  return (
    <div>
      <div className="mb-5">
        <PageKicker>Venue Discovery</PageKicker>
        <h1 className="font-display text-3xl font-extrabold uppercase leading-tight tracking-tight sm:text-4xl">Venue Research</h1>
      </div>

      <div className="mb-5 rounded-xl border-2 border-black bg-white p-4 shadow-nb-lg sm:p-6">
        <div className="mb-4 flex items-center justify-between border-b-2 border-black pb-3">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded border-2 border-black bg-nb-yellow text-xs font-black shadow-nb-sm">
              <SlidersHorizontal size={12} />
            </span>
            <span className="font-display text-sm font-extrabold uppercase tracking-wider">Filter Controls</span>
          </div>
          <span className="rounded border border-black bg-nb-bg px-2 py-0.5 font-mono text-[10px] font-bold uppercase shadow-nb-sm">
            {filtered.length} matches
          </span>
        </div>
        <div className="grid grid-cols-1 items-end gap-3.5 md:grid-cols-12">
          <div className="md:col-span-6">
            <label className="mb-1.5 block font-mono text-xs font-extrabold uppercase tracking-wider">Search Focus</label>
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="e.g. Cairo tech conference venues..."
                className="w-full rounded-lg border-2 border-black bg-nb-bg py-2.5 pl-9 pr-3 font-sans text-sm font-bold shadow-nb-sm placeholder-black/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-black"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 md:col-span-4">
            <div>
              <label className="mb-1.5 block font-mono text-xs font-extrabold uppercase tracking-wider">Capacity</label>
              <select
                value={minCap}
                onChange={(e) => setMinCap(Number(e.target.value))}
                className="w-full appearance-none rounded-lg border-2 border-black bg-nb-bg px-3 py-2.5 font-mono text-xs font-bold shadow-nb-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-black"
              >
                <option value={0}>Any</option>
                <option value={100}>100+</option>
                <option value={300}>300+</option>
                <option value={600}>600+</option>
              </select>
            </div>
            <div>
              <label className="mb-1.5 block font-mono text-xs font-extrabold uppercase tracking-wider">Max Budget</label>
              <select
                value={maxCost}
                onChange={(e) => setMaxCost(Number(e.target.value))}
                className="w-full appearance-none rounded-lg border-2 border-black bg-nb-bg px-3 py-2.5 font-mono text-xs font-bold shadow-nb-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-black"
              >
                <option value={0}>Any</option>
                <option value={5000}>$5,000</option>
                <option value={10000}>$10,000</option>
                <option value={20000}>$20,000</option>
              </select>
            </div>
          </div>
          <div className="md:col-span-2">
            <BrutalButton className="w-full" onClick={() => {}}>
              Apply
            </BrutalButton>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {filtered.map((v) => (
          <article key={v.id} className="rounded-lg border-2 border-black bg-white p-5 shadow-nb-lg transition-transform hover:-translate-x-px hover:-translate-y-px">
            <div className="flex justify-between gap-2">
              <h2 className="font-display text-lg font-extrabold">{v.name}</h2>
              <Badge tone="info">{v.suitability_score ?? v.extra?.suitability_score ?? "—"}</Badge>
            </div>
            <p className="mt-1 text-sm font-semibold text-black/70">{v.location}</p>
            <p className="mt-3 font-mono text-sm font-bold">
              {v.capacity} pax · ${v.estimated_cost.toLocaleString()}
            </p>
            <div className="mt-2">
              <CredibilityBadge tier={v.source_tier || v.source_type} priceType={v.price_type} />
            </div>
            {v.requires_quote ? <p className="mt-1 font-mono text-[10px] font-bold uppercase">Requires quote: YES</p> : null}
            {v.last_checked_at ? (
              <p className="font-mono text-[10px] font-bold text-black/60">
                Last checked {new Date(v.last_checked_at).toLocaleString()}
              </p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-1">
              {Array.isArray(v.facilities) && v.facilities.map((f) => (
                <Badge key={f}>{f}</Badge>
              ))}
            </div>
            <div className="mt-4 flex gap-2">
            <button
              className="rounded border-2 border-black bg-nb-yellow px-3 py-1.5 font-display text-xs font-extrabold uppercase shadow-nb-sm"
              onClick={() => setCompare((c) => (c.includes(v.id) ? c.filter((x) => x !== v.id) : [...c, v.id].slice(0, 3)))}
            >
              {compare.includes(v.id) ? "Remove compare" : "Compare"}
            </button>
            {eventId && v.id && (
              <button
                className="rounded border-2 border-black bg-white px-3 py-1.5 font-display text-xs font-extrabold uppercase shadow-nb-sm"
                onClick={() =>
                  api(`/api/events/${eventId}/venues/${v.id}`, {
                    method: "POST",
                    body: JSON.stringify({ status: "selected" }),
                  }).then(() =>
                    api<Venue[]>(`/api/events/${eventId}/venues`).then(setRows),
                  )
                }
              >
                {v.status === "selected" ? "Selected" : "Select"}
              </button>
            )}
            </div>
          </article>
        ))}
      </div>

      {compared.length > 1 && (
        <div className="mt-8 overflow-x-auto rounded-lg border-2 border-black bg-white p-4 shadow-nb-lg">
          <h2 className="mb-3 font-display text-lg font-extrabold uppercase">Comparison</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-black text-left font-display text-xs uppercase tracking-wider">
                <th className="py-2">Venue</th>
                <th>Capacity</th>
                <th>Cost</th>
                <th>Score</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {compared.map((v) => (
                <tr key={v.id} className="border-t-2 border-black/20">
                  <td className="py-2 font-bold">{v.name}</td>
                  <td className="font-mono">{v.capacity}</td>
                  <td className="font-mono">${v.estimated_cost.toLocaleString()}</td>
                  <td>{v.suitability_score ?? v.extra?.suitability_score ?? "—"}</td>
                  <td className="text-xs font-bold">{v.source_tier || v.source_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
