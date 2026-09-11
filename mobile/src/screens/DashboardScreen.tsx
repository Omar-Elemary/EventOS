import { useFocusEffect, useNavigation } from "@react-navigation/native";
import { useCallback, useState } from "react";
import { Alert, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { api, DEMO_EVENT_ID, createBlankEvent, deleteEvent, type AgentRun, type EventRecord } from "../lib/api";
import { filledBrief, money, progressFor } from "../lib/eventDisplay";
import { Badge, BrutalButton, Card, Empty, Kicker, colors } from "../ui";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export function DashboardScreen() {
  const nav = useNavigation<any>();
  const [events, setEvents] = useState<EventRecord[] | null>(null);
  const [agents, setAgents] = useState<AgentRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const rows = await api<EventRecord[]>("/api/events");
      setEvents(rows);
      const featured = rows.find((e) => e.id === DEMO_EVENT_ID) || rows[0];
      const runs = featured
        ? await api<AgentRun[]>(`/api/events/${featured.id}/agents`).catch(() => [] as AgentRun[])
        : [];
      setAgents(runs);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  function confirmDelete(e: EventRecord) {
    Alert.alert("Delete event", `Delete “${e.name}”? This cannot be undone.`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await deleteEvent(e.id);
            await load();
          } catch (err) {
            setError(String(err));
          }
        },
      },
    ]);
  }

  const featured = events?.find((e) => e.id === DEMO_EVENT_ID) || events?.[0];
  const planned = events?.reduce((s, e) => s + (e.budget || 0), 0) ?? 0;
  const risks = events?.flatMap((e) => ((e.plan_snapshot?.risks as { severity?: string }[]) || [])) ?? [];
  const high = risks.filter((r) => r.severity === "high" || r.severity === "critical").length;
  const running = agents.filter((a) => a.status === "running").length;

  return (
    <ScrollView
      style={styles.page}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={!events && !error} onRefresh={load} />}
    >
      <Kicker>
        System Live • {events?.length ?? 0} event{(events?.length ?? 0) === 1 ? "" : "s"}
      </Kicker>
      <Text style={styles.h1}>
        {greeting()},{"\n"}Omar
      </Text>
      {error ? <Text style={styles.err}>{error}</Text> : null}
      <View style={styles.grid}>
        <Stat label="Events" value={String(events?.length ?? "—")} />
        <Stat label="Budget" value={money(planned, events?.[0]?.currency || "EGP")} />
        <Stat label="Agents" value={running ? `${running} live` : "Idle"} />
        <Stat label="Risks" value={String(high)} hot={high > 0} />
      </View>
      {featured ? (
        <Card>
          <View style={styles.row}>
            <Text style={styles.h2}>{featured.name}</Text>
            <Badge tone={featured.status === "approved" ? "ok" : featured.status === "planning" ? "info" : "neutral"}>
              {featured.status}
            </Badge>
          </View>
          <Text style={styles.meta}>
            {filledBrief(featured).location || "Location TBD"} ·{" "}
            {filledBrief(featured).attendees != null ? `${filledBrief(featured).attendees} pax` : "Headcount TBD"} ·{" "}
            {featured.copilot_state?.phase || "intake"}
          </Text>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${progressFor(featured)}%` }]} />
          </View>
          <Text style={styles.progressLabel}>{progressFor(featured)}% progress</Text>
          <View style={{ height: 12 }} />
          <BrutalButton label="Open event" onPress={() => nav.navigate("Event", { eventId: featured.id })} />
        </Card>
      ) : events && !events.length ? (
        <Empty title="No events" hint="Start a blank event below and brief the planner in chat." />
      ) : null}

      <Card>
        <Text style={styles.h2}>New event</Text>
        <Text style={styles.meta}>Blank draft — the planner will ask for city, headcount, days, and budget.</Text>
        <TextInput
          value={name}
          onChangeText={setName}
          placeholder="Event name"
          placeholderTextColor="#666"
          style={styles.input}
        />
        <BrutalButton
          label={creating ? "Creating…" : "Create and open planner"}
          disabled={creating}
          onPress={async () => {
            const title = name.trim();
            if (!title) return;
            setCreating(true);
            try {
              const ev = await createBlankEvent(title);
              setName("");
              await load();
              nav.navigate("Planner", { eventId: ev.id });
            } catch (e) {
              setError(String(e));
            } finally {
              setCreating(false);
            }
          }}
        />
      </Card>

      {(events || []).map((e) => {
        const brief = filledBrief(e);
        const pct = progressFor(e);
        const phase = e.copilot_state?.phase || "intake";
        return (
          <Card key={e.id}>
            <Pressable onPress={() => nav.navigate("Event", { eventId: e.id })}>
              <View style={styles.row}>
                <Text style={styles.h2}>{e.name}</Text>
                <Badge tone={e.status === "approved" ? "ok" : e.status === "planning" ? "info" : "neutral"}>
                  {e.status}
                </Badge>
              </View>
              <Text style={styles.meta}>
                {brief.location || "Location TBD"} · {brief.attendees != null ? `${brief.attendees} pax` : "Headcount TBD"} · {phase}
              </Text>
              <View style={styles.progressTrack}>
                <View style={[styles.progressFill, { width: `${pct}%` }]} />
              </View>
              <Text style={styles.progressLabel}>{pct}% progress</Text>
            </Pressable>
            <View style={styles.actions}>
              <Pressable onPress={() => nav.navigate("Event", { eventId: e.id })} style={styles.actionBtn}>
                <Text style={styles.actionText}>Open</Text>
              </Pressable>
              <Pressable onPress={() => confirmDelete(e)} style={styles.actionBtn}>
                <Text style={[styles.actionText, { color: colors.magenta }]}>Delete</Text>
              </Pressable>
            </View>
          </Card>
        );
      })}
    </ScrollView>
  );
}

function Stat({ label, value, hot }: { label: string; value: string; hot?: boolean }) {
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
  h1: { fontSize: 34, fontWeight: "800", letterSpacing: -1, marginBottom: 16, textTransform: "uppercase" },
  h2: { fontSize: 20, fontWeight: "800", flex: 1, paddingRight: 8 },
  meta: { fontWeight: "700", marginTop: 6, color: "#333" },
  err: { backgroundColor: colors.pink, borderWidth: 2, borderColor: "#000", padding: 10, fontWeight: "700", marginBottom: 12 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 12 },
  stat: {
    width: "48%",
    backgroundColor: "#fff",
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 8,
    padding: 12,
  },
  statLabel: { fontSize: 10, fontWeight: "800", letterSpacing: 1, textTransform: "uppercase", color: "#555" },
  statValue: { fontSize: 22, fontWeight: "800", marginTop: 4 },
  row: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  progressTrack: {
    marginTop: 10,
    height: 10,
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 999,
    backgroundColor: "#e5e5e5",
    overflow: "hidden",
  },
  progressFill: { height: "100%", backgroundColor: colors.magenta },
  progressLabel: { marginTop: 6, fontSize: 11, fontWeight: "800", textTransform: "uppercase" },
  actions: { flexDirection: "row", gap: 8, marginTop: 12 },
  actionBtn: {
    flex: 1,
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
    backgroundColor: colors.bg,
  },
  actionText: { fontSize: 12, fontWeight: "800", textTransform: "uppercase" },
  input: {
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontWeight: "700",
    backgroundColor: colors.bg,
    marginTop: 10,
    marginBottom: 10,
  },
});
