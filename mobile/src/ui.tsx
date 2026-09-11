import { Pressable, StyleSheet, Text, View } from "react-native";

export const colors = {
  yellow: "#facc15",
  yellowSoft: "#ffe083",
  cyan: "#00eefc",
  magenta: "#e30071",
  pink: "#ffb1c5",
  green: "#10b981",
  bg: "#fbf8ef",
  ink: "#121212",
  white: "#ffffff",
};

export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "ok" | "warn" | "bad" | "info";
}) {
  const bg =
    tone === "ok"
      ? colors.green
      : tone === "warn"
        ? colors.yellow
        : tone === "bad"
          ? colors.magenta
          : tone === "info"
            ? colors.cyan
            : colors.white;
  return (
    <View style={[styles.badge, { backgroundColor: bg }]}>
      <Text style={[styles.badgeText, tone === "bad" && { color: "#fff" }]}>{children}</Text>
    </View>
  );
}

export function Card({ children, style }: { children: React.ReactNode; style?: object }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function BrutalButton({
  label,
  onPress,
  color = colors.yellow,
  disabled,
}: {
  label: string;
  onPress: () => void;
  color?: string;
  disabled?: boolean;
}) {
  return (
    <Pressable
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [styles.btn, { backgroundColor: color, opacity: disabled ? 0.5 : 1 }, pressed && styles.btnPressed]}
    >
      <Text style={styles.btnText}>{label}</Text>
    </Pressable>
  );
}

export function Kicker({ children }: { children: React.ReactNode }) {
  return (
    <View style={styles.kicker}>
      <View style={styles.dot} />
      <Text style={styles.kickerText}>{children}</Text>
    </View>
  );
}

export function Empty({ title, hint }: { title: string; hint: string }) {
  return (
    <Card>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyHint}>{hint}</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  badgeText: { fontSize: 10, fontWeight: "800", letterSpacing: 0.6, textTransform: "uppercase" },
  card: {
    backgroundColor: "#fff",
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
  },
  btn: {
    borderWidth: 2,
    borderColor: "#000",
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: "center",
  },
  btnPressed: { transform: [{ translateX: 2 }, { translateY: 2 }] },
  btnText: { fontWeight: "800", letterSpacing: 1, textTransform: "uppercase" },
  kicker: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.cyan,
    borderWidth: 2,
    borderColor: "#000",
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginBottom: 10,
  },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#000" },
  kickerText: { fontSize: 11, fontWeight: "800", letterSpacing: 1, textTransform: "uppercase" },
  emptyTitle: { fontWeight: "800", fontSize: 16, marginBottom: 6 },
  emptyHint: { fontWeight: "600", color: "#333" },
});
