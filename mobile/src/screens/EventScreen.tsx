import { useNavigation, useRoute } from "@react-navigation/native";
import { useEffect, useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";
import { api, DEMO_EVENT_ID, agentsForLatestRun, deleteEvent, type AgentRun, type EventRecord } from "../lib/api";
import { filledBrief, money, progressFor } from "../lib/eventDisplay";
import { Badge, BrutalButton, Card, Kicker, colors } from "../ui";

const PIPELINE = ["requirements", "venue", "vendor", "budget", "schedule", "logistics", "risk", "critic"];

export function EventScreen() {
  const nav = useNavigation<any>();
  const route = useRoute<any>();
  const eventId: string = route.params?.eventId || DEMO_EVENT_ID;
  const [ev, setEv] = useState<EventRecord | null>(null);
  const [agents, setAgents] = useState<AgentRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<EventRecord>(`/api/events/${eventId}`)
      .then(setEv)
      .catch((e) => setError(String(e)));
    api<AgentRun[]>(`/api/events/${eventId}/agents`)
      .then(setAgents)
      .catch(() => setAgents([]));
  }, [eventId]);

  const snap = ev?.plan_snapshot || {};
  const risks =
    (snap.risks as { title: string; severity: string; explanation?: string; solutions?: string[] }[]) || [];
  const budget = snap.budget as { remaining?: number; subtotal?: number } | undefined;
  const brief = filledBrief(ev);
  const pct = ev ? progressFor(ev) : 0;
  const phase = ev?.copilot_state?.phase || "intake";
  const latest = new Map<string, AgentRun>();
  for (const r of agentsForLatestRun(agents)) latest.set(r.agent, r);
  const done = PIPELINE.filter((n) => latest.get(n)?.status === "completed").length;

  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.content}>
      <Kicker>
        {ev?.status || "…"} · {phase}
      </Kicker>
      {error ? <Text style={styles.err}>{error}</Text> : null}
      <Text style={styles.h1}>{ev?.name || "Event"}</Text>
      <Text style={styles.meta}>
        {brief.location || "Location TBD"} · {brief.attendees != null ? `${brief.attendees} attendees` : "Headcount TBD"} ·{" "}
        {brief.days != null ? `${brief.days} days` : "Duration TBD"}
      </Text>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${pct}%` }]} />
      </View>
      <Text style={styles.progressLabel}>{pct}% overall progress</Text>
      <View style={{ height: 12 }} />
      <BrutalButton label="Ask AI planner" onPress={() => nav.navigate("Planner", { eventId })} />
      <View style={{ height: 12 }} />
      {ev ? (
        <BrutalButton
          label="Delete event"
          color={colors.pink}
          onPress={() => {
            Alert.alert("Delete event", `Delete “${ev.name}”? This cannot be undone.`, [
              { text: "Cancel", style: "cancel" },
              {
                text: "Delete",
                style: "destructive",
                onPress: async () => {
                  try {
                    await deleteEvent(ev.id);
                    nav.navigate("Dashboard");
                  } catch (e) {
                    setError(String(e));
                  }
                },
              },
            ]);
          }}
        />
      ) : null}
      <View style={{ height: 12 }} />
      <View style={styles.grid}>
        <Metric label="Budget" value={brief.budget != null && ev ? money(brief.budget, ev.currency) : "TBD"} />
        <Metric label="Planned" value={budget?.subtotal != null && ev ? money(budget.subtotal, ev.currency) : "—"} />
        <Metric label="Left" value={budget?.remaining != null && ev ? money(budget.remaining, ev.currency) : "—"} />
        <Metric label="Risks" value={String(risks.length)} hot={risks.length > 0} />
      </View>
      <Text style={styles.h2}>
        Agent progress · {done}/{PIPELINE.length}
      </Text>
      <View style={styles.pills}>
        {PIPELINE.map((name) => {
          const r = latest.get(name);
          const ok = r?.status === "completed";
          const running = r?.status === "running";
          const failed = r?.status === "failed";
          return (
            <View
              key={name}
              style={[
                styles.pill,
                ok && { backgroundColor: "#c8f7c5" },
                running && { backgroundColor: "#9ef0f0" },
                failed && { backgroundColor: colors.pink },
              ]}
            >
              <Text style={styles.pillText}>{name}</Text>
              <Text style={styles.pillStatus}>{r?.status || "idle"}</Text>
            </View>
          );
        })}
      </View>
      <Text style={styles.h2}>Key risks</Text>
      {risks.slice(0, 5).map((r) => (
        <Card key={r.title}>
          <View style={styles.row}>
            <Text style={styles.risk}>{r.title}</Text>
            <Badge tone={r.severity === "high" || r.severity === "critical" ? "bad" : r.severity === "medium" ? "warn" : "ok"}>
              {r.severity}
            </Badge>
          </View>
          {r.explanation ? <Text style={styles.meta}>{r.explanation}</Text> : null}
          {r.solutions?.[0] ? <Text style={styles.meta}>Try: {r.solutions[0]}</Text> : null}
        </Card>
      ))}
      {ev && risks.length === 0 ? <Text style={styles.meta}>No risks yet — run the planner.</Text> : null}
    </ScrollView>
  );
}

function Metric({ label, value, hot }: { label: string; value: string; hot?: boolean }) {
  return (
    <View style={[styles.stat, hot && { backgroundColor: "#ffebee" }]}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={[styles.statValue, hot && { color: colors.magenta }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16, paddingBottom: 32 },
  h1: { fontSize: 28, fontWeight: "800", textTransform: "uppercase", letterSpacing: -0.5 },
  h2: { fontSize: 18, fontWeight: "800", textTransform: "uppercase", marginBottom: 8, marginTop: 8 },
  meta: { fontWeight: "700", color: "#333", marginTop: 6 },
  err: { backgroundColor: colors.pink, borderWidth: 2, borderColor: "#000", padding: 10, fontWeight: "700", marginBottom: 12 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 12 },
  stat: { width: "48%", backgroundColor: "#fff", borderWidth: 2, borderColor: "#000", borderRadius: 8, padding: 12 },
  statLabel: { fontSize: 10, fontWeight: "800", letterSpacing: 1, textTransform: "uppercase", color: "#555" },
  statValue: { fontSize: 18, fontWeight: "800", marginTop: 4 },
  row: { flexDirection: "row", justifyContent: "space-between", gap: 8, alignItems: "center" },
  risk: { flex: 1, fontWeight: "800" },
  progressTrack: {
    marginTop: 12,
    height: 12,
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 999,
    backgroundColor: "#e5e5e5",
    overflow: "hidden",
  },
  progressFill: { height: "100%", backgroundColor: colors.magenta },
  progressLabel: { marginTop: 6, fontSize: 11, fontWeight: "800", textTransform: "uppercase" },
  pills: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 8 },
  pill: {
    width: "48%",
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 8,
    padding: 8,
    backgroundColor: "#fff",
  },
  pillText: { fontSize: 11, fontWeight: "800", textTransform: "uppercase" },
  pillStatus: { fontSize: 10, fontWeight: "700", color: "#555", marginTop: 2 },
});
