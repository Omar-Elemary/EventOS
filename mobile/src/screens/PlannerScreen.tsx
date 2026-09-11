import { useRoute } from "@react-navigation/native";
import { useEffect, useRef, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { api, DEMO_EVENT_ID, type AgentRun, type ChatAction, type ChatOut, type EventRecord, agentsForLatestRun } from "../lib/api";
import { Badge, Card, Kicker, colors } from "../ui";

type Msg = { role: "user" | "assistant"; text: string; actions?: ChatAction[] };

export function PlannerScreen() {
  const route = useRoute<any>();
  const eventId: string = route.params?.eventId || DEMO_EVENT_ID;
  const scrollRef = useRef<ScrollView>(null);
  const copilotFetched = useRef(false);
  const copilotStateRef = useRef<EventRecord["copilot_state"] | null>(null);
  const [event, setEvent] = useState<EventRecord | null>(null);
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      text: "Describe the event to plan (type, city, size, days, budget). I will run the agent graph.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [agents, setAgents] = useState<AgentRun[]>([]);
  const [phase, setPhase] = useState("intake");
  const [actions, setActions] = useState<ChatAction[]>([]);

  async function refresh() {
    const [ev, rows] = await Promise.all([
      api<EventRecord>(`/api/events/${eventId}`),
      api<{ role: string; content: string; actions?: ChatAction[] | null; phase?: string | null }[]>(
        `/api/events/${eventId}/chat`,
      ),
    ]);
    setEvent(ev);
    if (ev.copilot_state) copilotStateRef.current = ev.copilot_state;
    if (ev.copilot_state?.phase) setPhase(ev.copilot_state.phase);
    if (ev.copilot_state?.available_actions?.length) setActions(ev.copilot_state.available_actions);
    if (rows.length) {
      setMessages(rows.map((r) => ({ role: r.role as Msg["role"], text: r.content, actions: r.actions || undefined })));
      const last = [...rows].reverse().find((r) => r.role === "assistant");
      if (last?.actions?.length) setActions(last.actions);
      if (last?.phase) setPhase(last.phase);
    }
  }

  useEffect(() => {
    refresh().catch(() => setEvent(null));
  }, [eventId]);

  useEffect(() => {
    const load = () =>
      api<AgentRun[]>(`/api/events/${eventId}/agents`)
        .then((rows) => {
          setAgents(rows);
          const latest = new Map<string, AgentRun>();
          for (const r of agentsForLatestRun(rows)) latest.set(r.agent, r);
          const running = [...latest.values()].some((a) => a.status === "running");
          const finished = [...latest.values()].some((a) => a.agent === "finalize" || a.agent === "human_review");
          if (running) copilotFetched.current = false;
          if (!running && finished && !copilotFetched.current) {
            copilotFetched.current = true;
            refresh().catch(() => {});
          }
        })
        .catch(() => {});
    load();
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [eventId]);

  async function send(text: string, actionId?: string) {
    const trimmed = text.trim();
    if (!trimmed && !actionId) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: trimmed || actionId || "" }]);
    setBusy(true);
    try {
      const res = await api<ChatOut>("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          message: trimmed,
          event_id: eventId,
          action_id: actionId,
          copilot_state: copilotStateRef.current,
        }),
      });
      setMessages((m) => [...m, { role: "assistant", text: res.reply, actions: res.actions }]);
      setActions(res.actions || []);
      if (res.phase) setPhase(res.phase);
      if (res.copilot_state) copilotStateRef.current = res.copilot_state;
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: `Request failed: ${err}` }]);
    } finally {
      setBusy(false);
    }
  }

  const latest = new Map<string, AgentRun>();
  for (const r of agentsForLatestRun(agents)) latest.set(r.agent, r);
  const running = [...latest.values()].find((a) => a.status === "running");

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView
        ref={scrollRef}
        style={styles.page}
        contentContainerStyle={styles.content}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
      >
        <Kicker>{phase.toUpperCase()} · Active mission</Kicker>
        <Card style={{ backgroundColor: colors.yellowSoft }}>
          <Text style={styles.mission}>
            {event?.user_request ||
              (event
                ? `${event.duration_days}-day ${event.name} in ${event.location || "TBD"} for ${event.attendees} people.`
                : "Loading brief…")}
          </Text>
        </Card>
        {running ? (
          <Card style={{ backgroundColor: "#b8f9ff" }}>
            <Text style={styles.live}>LIVE · {running.agent}</Text>
            <Text style={styles.meta}>{running.task || running.output_summary || running.status}</Text>
          </Card>
        ) : null}
        <View style={styles.pills}>
          {["requirements", "venue", "vendor", "budget", "schedule", "logistics", "risk", "critic"].map((name) => {
            const r = latest.get(name);
            const tone = r?.status === "completed" ? "ok" : r?.status === "running" ? "info" : r?.status === "failed" ? "bad" : "neutral";
            return (
              <Badge key={name} tone={tone}>
                {name}
              </Badge>
            );
          })}
        </View>
        {messages.map((m, i) => (
          <View key={i} style={[styles.bubble, m.role === "user" ? styles.user : styles.bot]}>
            <Text style={[styles.bubbleText, m.role === "user" && { color: "#fff" }]}>{m.text}</Text>
          </View>
        ))}
      </ScrollView>
      <View style={styles.composer}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 8 }}>
          {actions.map((chip) => (
            <Pressable key={chip.id} onPress={() => send(chip.label, chip.id)} style={styles.chip}>
              <Text style={styles.chipText}>{chip.label}</Text>
            </Pressable>
          ))}
        </ScrollView>
        <View style={styles.row}>
          <TextInput
            value={input}
            onChangeText={setInput}
            onSubmitEditing={() => send(input)}
            placeholder="Instruct the agent…"
            placeholderTextColor="#666"
            style={styles.input}
          />
          <Pressable disabled={busy} onPress={() => send(input)} style={[styles.send, busy && { opacity: 0.5 }]}>
            <Text style={styles.sendText}>{busy ? "…" : "GO"}</Text>
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  page: { flex: 1 },
  content: { padding: 16, paddingBottom: 24 },
  mission: { fontWeight: "800", fontSize: 16, lineHeight: 22 },
  live: { fontWeight: "800", letterSpacing: 1, marginBottom: 4 },
  meta: { fontWeight: "600" },
  pills: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 12 },
  bubble: { borderWidth: 2, borderColor: "#000", borderRadius: 8, padding: 12, marginBottom: 8, maxWidth: "92%" },
  bot: { backgroundColor: "#fff", alignSelf: "flex-start" },
  user: { backgroundColor: colors.magenta, alignSelf: "flex-end" },
  bubbleText: { fontWeight: "600", lineHeight: 20 },
  composer: {
    borderTopWidth: 2,
    borderColor: "#000",
    backgroundColor: "#fff",
    padding: 10,
  },
  chip: {
    backgroundColor: colors.yellow,
    borderWidth: 2,
    borderColor: "#000",
    paddingHorizontal: 10,
    paddingVertical: 6,
    marginRight: 8,
    borderRadius: 6,
  },
  chipText: { fontWeight: "800", fontSize: 12 },
  row: { flexDirection: "row", gap: 8, alignItems: "center" },
  input: {
    flex: 1,
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontWeight: "700",
    backgroundColor: colors.bg,
  },
  send: {
    backgroundColor: colors.magenta,
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  sendText: { color: "#fff", fontWeight: "800" },
});
