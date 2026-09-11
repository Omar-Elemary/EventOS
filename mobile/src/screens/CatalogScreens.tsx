import { useEffect, useMemo, useState } from "react";
import { ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { api, DEMO_EVENT_ID } from "../lib/api";
import { Badge, Card, Empty, Kicker, colors } from "../ui";

type Venue = {
  id: string;
  name: string;
  location: string;
  capacity: number;
  estimated_cost: number;
  facilities: string[];
  source_type: string;
  extra?: { suitability_score?: number };
};

export function VenuesScreen() {
  const [rows, setRows] = useState<Venue[] | null>(null);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Venue[]>("/api/venues")
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, []);

  const filtered = useMemo(() => {
    const n = q.toLowerCase();
    return (rows || []).filter((v) => v.name.toLowerCase().includes(n) || v.location.toLowerCase().includes(n));
  }, [rows, q]);

  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.content}>
      <Kicker>Venue discovery</Kicker>
      <Text style={styles.h1}>Venue Research</Text>
      <TextInput value={q} onChangeText={setQ} placeholder="Search" placeholderTextColor="#666" style={styles.input} />
      {error ? <Text style={styles.err}>{error}</Text> : null}
      {!rows ? <Text style={styles.meta}>Loading…</Text> : null}
      {rows && !rows.length ? <Empty title="No venues" hint="Start the API so the catalog loads." /> : null}
      {filtered.map((v) => (
        <Card key={v.id}>
          <View style={styles.row}>
            <Text style={styles.h2}>{v.name}</Text>
            <Badge tone="info">{v.extra?.suitability_score ?? "—"}</Badge>
          </View>
          <Text style={styles.meta}>{v.location}</Text>
          <Text style={styles.mono}>
            {v.capacity} pax · ${v.estimated_cost.toLocaleString()} · {v.source_type}
          </Text>
        </Card>
      ))}
    </ScrollView>
  );
}

type Vendor = {
  id: string;
  name: string;
  category: string;
  location: string;
  estimated_cost: number;
  rating: number;
  source_type: string;
};

export function VendorsScreen() {
  const [rows, setRows] = useState<Vendor[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<Vendor[]>("/api/vendors")
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, []);
  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.content}>
      <Kicker>Marketplace</Kicker>
      <Text style={styles.h1}>Vendors</Text>
      {error ? <Text style={styles.err}>{error}</Text> : null}
      {(rows || []).map((v) => (
        <Card key={v.id}>
          <View style={styles.row}>
            <Text style={styles.h2}>{v.name}</Text>
            <Badge>{v.category}</Badge>
          </View>
          <Text style={styles.meta}>{v.location}</Text>
          <Text style={styles.mono}>
            ${v.estimated_cost.toLocaleString()} · {v.rating.toFixed(1)} ★
          </Text>
        </Card>
      ))}
    </ScrollView>
  );
}

type Budget = {
  total_budget: number;
  items: { category: string; description: string; estimated_cost: number }[];
  contingency: number;
  subtotal: number;
  remaining: number;
};

export function BudgetScreen() {
  const [b, setB] = useState<Budget | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<Budget>(`/api/events/${DEMO_EVENT_ID}/budget`)
      .then((x) => setB(x && Object.keys(x).length ? x : null))
      .catch((e) => setError(String(e)));
  }, []);
  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.content}>
      <Kicker>Financial status</Kicker>
      <Text style={styles.h1}>Budget</Text>
      {error ? <Text style={styles.err}>{error}</Text> : null}
      {!b ? (
        <Empty title="No budget yet" hint="Run the AI planner first." />
      ) : (
        <>
          <View style={styles.grid}>
            <Stat label="Total" v={`$${b.total_budget.toLocaleString()}`} />
            <Stat label="Subtotal" v={`$${b.subtotal.toLocaleString()}`} />
            <Stat label="Contingency" v={`$${b.contingency.toLocaleString()}`} />
            <Stat label="Remaining" v={`$${b.remaining.toLocaleString()}`} />
          </View>
          {b.items.map((i, idx) => (
            <Card key={idx}>
              <Text style={styles.h2}>{i.category}</Text>
              <Text style={styles.meta}>{i.description}</Text>
              <Text style={styles.mono}>${i.estimated_cost.toLocaleString()}</Text>
            </Card>
          ))}
        </>
      )}
    </ScrollView>
  );
}

function Stat({ label, v }: { label: string; v: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{v}</Text>
    </View>
  );
}

export function TimelineScreen() {
  const [data, setData] = useState<{ items: { id: string; title: string; start_time: string; end_time: string; conflicts: string[] }[]; conflicts: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<{ items: any[]; conflicts: string[] }>(`/api/events/${DEMO_EVENT_ID}/schedule`)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);
  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.content}>
      <Kicker>Schedule grid</Kicker>
      <Text style={styles.h1}>Timeline</Text>
      {error ? <Text style={styles.err}>{error}</Text> : null}
      {data?.conflicts?.length ? <Text style={styles.err}>Conflicts: {data.conflicts.join(" · ")}</Text> : null}
      {(data?.items || []).map((it, i) => (
        <Card key={it.id} style={it.conflicts?.length ? { backgroundColor: colors.yellowSoft } : undefined}>
          <Text style={styles.mono}>#{i + 1}</Text>
          <Text style={styles.h2}>{it.title}</Text>
          <Text style={styles.meta}>
            {new Date(it.start_time).toLocaleString()} → {new Date(it.end_time).toLocaleTimeString()}
          </Text>
        </Card>
      ))}
    </ScrollView>
  );
}

type Risk = {
  title: string;
  severity: string;
  probability: number;
  impact: string;
  description: string;
  mitigation: string;
  explanation?: string;
  solutions?: string[];
};

export function RisksScreen() {
  const [rows, setRows] = useState<Risk[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<Risk[]>(`/api/events/${DEMO_EVENT_ID}/risks`)
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, []);
  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.content}>
      <Kicker>Threat assessment</Kicker>
      <Text style={styles.h1}>Risk Center</Text>
      {error ? <Text style={styles.err}>{error}</Text> : null}
      {rows && !rows.length ? <Empty title="No risks" hint="Risks appear after a planning run." /> : null}
      {(rows || []).map((r) => (
        <Card key={r.title} style={r.severity === "high" || r.severity === "critical" ? { backgroundColor: "#ffebee" } : undefined}>
          <View style={styles.row}>
            <Text style={[styles.h2, { flex: 1 }]}>{r.title}</Text>
            <Badge tone={r.severity === "high" || r.severity === "critical" ? "bad" : "warn"}>{r.severity}</Badge>
          </View>
          <Text style={styles.meta}>{r.explanation || r.description}</Text>
          <Text style={styles.meta}>If it hits: {r.impact}</Text>
          {(r.solutions && r.solutions.length ? r.solutions : [r.mitigation].filter(Boolean)).map((s, i) => (
            <Text key={`${r.title}-${i}`} style={styles.meta}>
              {i + 1}. {s}
            </Text>
          ))}
        </Card>
      ))}
    </ScrollView>
  );
}

export function AgentsScreen() {
  const [rows, setRows] = useState<import("../lib/api").AgentRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const load = () =>
      api<import("../lib/api").AgentRun[]>(`/api/events/${DEMO_EVENT_ID}/agents`)
        .then(setRows)
        .catch((e) => setError(String(e)));
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, []);
  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.content}>
      <Kicker>Pipeline</Kicker>
      <Text style={styles.h1}>Agent Activity</Text>
      {error ? <Text style={styles.err}>{error}</Text> : null}
      {(rows || [])
        .slice()
        .reverse()
        .map((r) => (
          <Card key={r.id}>
            <View style={styles.row}>
              <Text style={styles.h2}>{r.agent}</Text>
              <Badge tone={r.status === "completed" ? "ok" : r.status === "failed" ? "bad" : "info"}>{r.status}</Badge>
            </View>
            <Text style={styles.meta}>{r.output_summary || r.task}</Text>
            <Text style={styles.mono}>{r.duration_ms}ms · iter {r.iteration}</Text>
          </Card>
        ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16, paddingBottom: 32 },
  h1: { fontSize: 28, fontWeight: "800", textTransform: "uppercase", marginBottom: 12 },
  h2: { fontSize: 16, fontWeight: "800" },
  meta: { fontWeight: "600", color: "#333", marginTop: 4 },
  mono: { fontWeight: "800", marginTop: 6 },
  err: { backgroundColor: colors.pink, borderWidth: 2, borderColor: "#000", padding: 10, fontWeight: "700", marginBottom: 12 },
  input: {
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 8,
    padding: 12,
    backgroundColor: "#fff",
    fontWeight: "700",
    marginBottom: 12,
  },
  row: { flexDirection: "row", justifyContent: "space-between", gap: 8, alignItems: "center" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 12 },
  stat: { width: "48%", backgroundColor: "#fff", borderWidth: 2, borderColor: "#000", borderRadius: 8, padding: 12 },
  statLabel: { fontSize: 10, fontWeight: "800", textTransform: "uppercase", color: "#555" },
  statValue: { fontSize: 18, fontWeight: "800", marginTop: 4 },
});
