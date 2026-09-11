import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { StatusBar } from "expo-status-bar";
import { useEffect, useState } from "react";
import { ActivityIndicator, Text, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { DEMO_EVENT_ID, getApiBase, loadSavedApiBase, pingApi } from "./src/lib/api";
import { AgentsScreen, BudgetScreen, RisksScreen, TimelineScreen, VendorsScreen, VenuesScreen } from "./src/screens/CatalogScreens";
import { ConnectScreen } from "./src/screens/ConnectScreen";
import { DashboardScreen } from "./src/screens/DashboardScreen";
import { EventScreen } from "./src/screens/EventScreen";
import { MoreScreen } from "./src/screens/MoreScreen";
import { PlannerScreen } from "./src/screens/PlannerScreen";
import { colors } from "./src/ui";

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

function Tabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: "#fff", borderBottomWidth: 2, borderBottomColor: "#000" },
        headerTitleStyle: { fontWeight: "800" },
        tabBarStyle: { backgroundColor: "#fff", borderTopWidth: 2, borderTopColor: "#000", height: 64, paddingBottom: 8, paddingTop: 8 },
        tabBarActiveTintColor: colors.magenta,
        tabBarInactiveTintColor: "#111",
        tabBarLabelStyle: { fontWeight: "800", fontSize: 10, textTransform: "uppercase" },
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          tabBarIcon: ({ color }) => <Text style={{ color, fontWeight: "800" }}>▣</Text>,
        }}
      />
      <Tab.Screen
        name="Event"
        component={EventScreen}
        initialParams={{ eventId: DEMO_EVENT_ID }}
        options={{
          tabBarIcon: ({ color }) => <Text style={{ color, fontWeight: "800" }}>▢</Text>,
        }}
      />
      <Tab.Screen
        name="Planner"
        component={PlannerScreen}
        initialParams={{ eventId: DEMO_EVENT_ID }}
        options={{
          title: "AI Planner",
          tabBarIcon: ({ color }) => <Text style={{ color, fontWeight: "800" }}>✦</Text>,
        }}
      />
      <Tab.Screen
        name="More"
        component={MoreScreen}
        options={{
          tabBarIcon: ({ color }) => <Text style={{ color, fontWeight: "800" }}>☰</Text>,
        }}
      />
    </Tab.Navigator>
  );
}

export default function App() {
  const [booting, setBooting] = useState(true);
  const [connected, setConnected] = useState(false);

  async function check() {
    await loadSavedApiBase();
    const ok = await pingApi(getApiBase());
    setConnected(ok);
    setBooting(false);
  }

  useEffect(() => {
    check();
  }, []);

  if (booting) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.bg }}>
        <ActivityIndicator color="#000" />
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <NavigationContainer>
          <StatusBar style="dark" />
          <Stack.Navigator
            screenOptions={{
              headerStyle: { backgroundColor: "#fff" },
              headerTitleStyle: { fontWeight: "800" },
              contentStyle: { backgroundColor: colors.bg },
            }}
          >
            {!connected ? (
              <Stack.Screen name="Connect" options={{ headerShown: false }}>
                {() => <ConnectScreen onConnected={() => setConnected(true)} />}
              </Stack.Screen>
            ) : (
              <>
                <Stack.Screen name="Tabs" component={Tabs} options={{ headerShown: false }} />
                <Stack.Screen name="Venues" component={VenuesScreen} />
                <Stack.Screen name="Vendors" component={VendorsScreen} />
                <Stack.Screen name="Budget" component={BudgetScreen} />
                <Stack.Screen name="Timeline" component={TimelineScreen} />
                <Stack.Screen name="Risks" component={RisksScreen} />
                <Stack.Screen name="Agents" component={AgentsScreen} />
                <Stack.Screen name="ConnectModal" options={{ title: "API connection" }}>
                  {() => <ConnectScreen onConnected={() => setConnected(true)} />}
                </Stack.Screen>
              </>
            )}
          </Stack.Navigator>
        </NavigationContainer>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
