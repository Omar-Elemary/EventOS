import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Badge, CredibilityBadge, EmptyState, ErrorState, PageKicker, Skeleton } from "../components/ui";

type Vendor = {
  id: string;
  name: string;
  category: string;
  location: string;
  estimated_cost: number;
  rating: number;
  source_type?: string;
  source_tier?: string;
  price_type?: string;
  requires_quote?: boolean;
  status?: string;
};

const CATS = [
  "catering",
  "photography",
  "videography",
  "security",
  "transportation",
  "decoration",
  "av",
  "lighting",
  "entertainment",
  "staffing",
];

export function VendorsPage() {
  const { eventId } = useParams();
  const [cat, setCat] = useState<string>("");
  const [rows, setRows] = useState<Vendor[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const path = eventId ? `/api/events/${eventId}/vendors` : "/api/vendors";
    api<Vendor[]>(path)
      .then((data) => setRows(cat ? data.filter((v) => v.category === cat) : data))
      .catch((e) => setError(String(e)));
  }, [cat, eventId]);

  if (error) return <ErrorState message={error} />;
  if (!rows) return <Skeleton className="h-64" />;

  return (
    <div>
      <PageKicker>Vendor Marketplace</PageKicker>
      <h1 className="mb-6 font-display text-3xl font-extrabold uppercase tracking-tight">Vendor Marketplace</h1>
      <div className="mb-6 flex flex-wrap gap-2">
        <Chip active={!cat} onClick={() => setCat("")}>
          All
        </Chip>
        {CATS.map((c) => (
          <Chip key={c} active={cat === c} onClick={() => setCat(c)}>
            {c}
          </Chip>
        ))}
      </div>
      {rows.length === 0 ? (
        <EmptyState title="No vendors" hint="Seed data loads with the API." />
      ) : (
        <div className="overflow-x-auto rounded-lg border-2 border-black bg-white shadow-nb-lg">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-black bg-nb-yellow text-left font-display text-xs uppercase tracking-wider">
                <th className="px-4 py-3">Vendor</th>
                <th>Category</th>
                <th>Location</th>
                <th>Est. cost</th>
                <th>Rating</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((v) => (
                <tr key={v.id} className="border-t-2 border-black/15">
                  <td className="px-4 py-3 font-display font-bold">{v.name}</td>
                  <td>
                    <Badge>{v.category}</Badge>
                  </td>
                  <td className="font-semibold">{v.location}</td>
                  <td className="font-mono font-bold">${v.estimated_cost.toLocaleString()}</td>
                  <td className="font-mono">{Number(v.rating || 0).toFixed(1)}</td>
                  <td>
                    <CredibilityBadge tier={v.source_tier || v.source_type} priceType={v.price_type} />
                    {v.requires_quote ? <p className="font-mono text-[10px] font-black uppercase">Quote required</p> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full border-2 border-black px-3 py-1 font-display text-xs font-extrabold uppercase shadow-nb-sm ${
        active ? "bg-nb-magenta text-white" : "bg-white hover:bg-nb-yellow"
      }`}
    >
      {children}
    </button>
  );
}
