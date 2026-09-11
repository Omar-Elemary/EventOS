import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Download, Wallet } from "lucide-react";
import { money } from "../lib/eventDisplay";
import { BrutalButton, EmptyState, ErrorState, PageKicker, Skeleton } from "../components/ui";

type Budget = {
  total_budget: number;
  currency: string;
  items: { category: string; description: string; estimated_cost: number; status?: string }[];
  contingency: number;
  subtotal: number;
  remaining: number;
  committed?: number;
  estimated?: number;
  cost_per_attendee?: number | null;
  explanation?: string[];
  over_budget?: boolean;
  cheapest_alternatives?: { name: string; savings: number }[];
};

const COLORS = ["#00f0ff", "#facc15", "#10b981", "#ff2a85", "#7df4ff", "#e30071", "#ffe083", "#121212"];

export function BudgetPage() {
  const { eventId } = useParams();
  const [b, setB] = useState<Budget | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!eventId) return;
    api<Budget>(`/api/events/${eventId}/budget`)
      .then((x) => setB(x && Object.keys(x).length ? x : null))
      .catch((e) => setError(String(e)));
  }, [eventId]);

  if (error) return <ErrorState message={error} />;
  if (b === undefined) return <Skeleton className="h-64" />;
  if (!b) return <EmptyState title="No budget yet" hint="Run the AI planner to generate a deterministic budget." />;

  const chart = [
    ...(b.items || []).map((i) => ({ name: i.category, value: i.estimated_cost })),
    { name: "contingency", value: b.contingency },
  ];
  const used = b.total_budget > 0 ? Math.round(((b.subtotal + b.contingency) / b.total_budget) * 100) : 0;
  const onTrack = b.remaining >= 0;

  function exportReport() {
    const blob = new Blob([JSON.stringify(b, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "eventos-budget.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <PageKicker>Financial Status • {onTrack ? "On Track" : "Over"}</PageKicker>
          <h1 className="font-display text-3xl font-extrabold uppercase leading-none tracking-tight md:text-5xl">Budget Overview</h1>
        </div>
        <BrutalButton onClick={exportReport}>
          <Download size={16} /> Export Report
        </BrutalButton>
      </div>

      <div className="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
        <Kpi icon={<Wallet size={12} />} label="Total Budget" v={money(b.total_budget, b.currency)} bar={100} />
        <Kpi label="Committed" v={money(b.committed ?? 0, b.currency)} tone="bg-nb-cyan-light/40" />
        <Kpi label="Estimated" v={money(b.estimated ?? b.subtotal, b.currency)} tone="bg-nb-yellow/40" bar={Math.min(100, used)} />
        <Kpi label="Contingency" v={money(b.contingency, b.currency)} tone="bg-nb-yellow/40" />
        <Kpi label="Remaining" v={money(b.remaining, b.currency)} tone={onTrack ? "bg-nb-green/30" : "bg-nb-pink"} />
      </div>
      {(b.explanation?.length || b.over_budget) && (
        <div className="rounded-lg border-2 border-black bg-white p-5 shadow-nb-lg">
          <h2 className="mb-2 font-display text-lg font-extrabold uppercase">Why is this over budget?</h2>
          {(b.explanation || []).map((line) => (
            <p key={line} className="text-sm font-semibold">
              {line}
            </p>
          ))}
          {b.cost_per_attendee != null && (
            <p className="mt-2 font-mono text-xs font-bold">Cost per attendee {money(b.cost_per_attendee, b.currency)}</p>
          )}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-lg border-2 border-black bg-white p-5 shadow-nb-lg">
          <h2 className="mb-4 font-display text-lg font-extrabold uppercase">Allocation</h2>
          <div className="h-64">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={chart} dataKey="value" nameKey="name" innerRadius={54} outerRadius={86} stroke="#000" strokeWidth={2}>
                  {chart.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="overflow-x-auto rounded-lg border-2 border-black bg-white p-5 shadow-nb-lg">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-black text-left font-display text-xs uppercase tracking-wider">
                <th className="py-2">Category</th>
                <th>Description</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {(b.items || []).map((i, idx) => (
                <tr key={idx} className="border-t-2 border-black/15">
                  <td className="py-2 font-display font-bold">{i.category}</td>
                  <td className="font-semibold">{i.description}</td>
                  <td className="font-mono font-bold">{money(i.estimated_cost, b.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Kpi({
  label,
  v,
  tone = "bg-white",
  bar,
  icon,
}: {
  label: string;
  v: string;
  tone?: string;
  bar?: number;
  icon?: React.ReactNode;
}) {
  return (
    <div className={`relative flex flex-col justify-between overflow-hidden rounded-lg border-2 border-black p-4 shadow-nb-lg ${tone}`}>
      <div>
        <div className="mb-1.5 flex items-center gap-1.5">
          {icon && (
            <div className="flex h-5 w-5 items-center justify-center rounded border border-black bg-neo-yellow">{icon}</div>
          )}
          <span className="font-mono text-[11px] font-black uppercase tracking-wider text-black/70">{label}</span>
        </div>
        <div className="font-display text-2xl font-extrabold leading-tight sm:text-3xl">{v}</div>
      </div>
      {bar != null && (
        <div className="mt-3 h-2.5 overflow-hidden rounded-full border-2 border-black bg-[#e5e5e5] p-px">
          <div className="h-full rounded-full bg-black" style={{ width: `${bar}%` }} />
        </div>
      )}
    </div>
  );
}
