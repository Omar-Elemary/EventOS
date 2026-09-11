import { useState } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";
import { getApiBase, guessApiBase, persistApiBase, pingApi } from "../lib/api";
import { BrutalButton, Kicker, colors } from "../ui";

export function ConnectScreen({ onConnected }: { onConnected?: () => void }) {
  const [url, setUrl] = useState(getApiBase() || guessApiBase());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  async function connect() {
    const next = url.trim().replace(/\/$/, "");
    const withProto = /^https?:\/\//i.test(next) ? next : `http://${next}`;
    setBusy(true);
    setError(null);
    setOk(false);
    const live = await pingApi(withProto);
    setBusy(false);
    if (!live) {
      setError(`Cannot reach ${withProto}/api/events. On the PC run uvicorn --host 0.0.0.0 --port 8000, same Wi-Fi, and allow port 8000 in Windows Firewall.`);
      return;
    }
    await persistApiBase(withProto);
    setUrl(withProto);
    setOk(true);
    onConnected?.();
  }

  return (
    <View style={styles.page}>
      <Kicker>Phone · Expo Go</Kicker>
      <Text style={styles.h1}>Connect API</Text>
      <Text style={styles.copy}>
        This is a native EventOS client. It talks to FastAPI on your PC — not the website WebView.
      </Text>
      <Text style={styles.label}>API BASE URL</Text>
      <TextInput
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        onChangeText={setUrl}
        onSubmitEditing={connect}
        style={styles.input}
        value={url}
      />
      {error ? <Text style={styles.err}>{error}</Text> : null}
      {ok ? <Text style={styles.ok}>Connected.</Text> : null}
      <BrutalButton disabled={busy} label={busy ? "Checking…" : "Connect"} onPress={connect} />
      <Text style={styles.help}>
        PC command:{"\n"}cd backend{"\n"}python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg, padding: 20, justifyContent: "center" },
  h1: { fontSize: 36, fontWeight: "800", textTransform: "uppercase", marginBottom: 12 },
  copy: { fontWeight: "600", fontSize: 15, lineHeight: 22, marginBottom: 20 },
  label: { fontSize: 11, fontWeight: "800", letterSpacing: 1.4, marginBottom: 8 },
  input: {
    borderWidth: 2,
    borderColor: "#000",
    backgroundColor: "#fff",
    borderRadius: 8,
    padding: 12,
    fontWeight: "700",
    marginBottom: 12,
  },
  err: { backgroundColor: colors.pink, borderWidth: 2, borderColor: "#000", padding: 10, fontWeight: "700", marginBottom: 12 },
  ok: { backgroundColor: colors.green, borderWidth: 2, borderColor: "#000", padding: 10, fontWeight: "800", marginBottom: 12 },
  help: { marginTop: 16, fontWeight: "600", lineHeight: 20, color: "#333" },
});
