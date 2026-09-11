import { useNavigation } from "@react-navigation/native";
import { Pressable, ScrollView, StyleSheet, Text } from "react-native";
import { Kicker, colors } from "../ui";

const LINKS = [
  { to: "Venues", label: "Venues" },
  { to: "Vendors", label: "Vendors" },
  { to: "Budget", label: "Budget" },
  { to: "Timeline", label: "Timeline" },
  { to: "Risks", label: "Risks" },
  { to: "Agents", label: "Agents" },
  { to: "ConnectModal", label: "API connection" },
];

export function MoreScreen() {
  const nav = useNavigation<any>();
  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.content}>
      <Kicker>More</Kicker>
      <Text style={styles.h1}>Workspace</Text>
      {LINKS.map((l) => (
        <Pressable
          key={l.to}
          onPress={() => nav.navigate(l.to)}
          style={({ pressed }) => [styles.row, pressed && { transform: [{ translateX: 2 }, { translateY: 2 }] }]}
        >
          <Text style={styles.label}>{l.label}</Text>
          <Text style={styles.chev}>›</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16 },
  h1: { fontSize: 28, fontWeight: "800", textTransform: "uppercase", marginBottom: 16 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 8,
    padding: 14,
    marginBottom: 10,
  },
  label: { flex: 1, fontWeight: "800", fontSize: 16, textTransform: "uppercase" },
  chev: { fontWeight: "800", fontSize: 22 },
});
