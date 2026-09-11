import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { RequireAuth } from "./components/RequireAuth";
import { AgentsPage } from "./pages/AgentsPage";
import { BudgetPage } from "./pages/BudgetPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DecisionsPage } from "./pages/DecisionsPage";
import { EventsPage } from "./pages/EventsPage";
import { EventOverviewPage } from "./pages/EventOverviewPage";
import { LoginPage } from "./pages/LoginPage";
import { NewEventPage } from "./pages/NewEventPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { PlannerPage } from "./pages/PlannerPage";
import { RisksPage } from "./pages/RisksPage";
import { SignupPage } from "./pages/SignupPage";
import { SplashPage } from "./pages/SplashPage";
import { TimelinePage } from "./pages/TimelinePage";
import { VendorsPage } from "./pages/VendorsPage";
import { VenuesPage } from "./pages/VenuesPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/splash" element={<SplashPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route element={<RequireAuth />}>
          <Route element={<AppShell />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/events/new" element={<NewEventPage />} />
            <Route path="/events" element={<EventsPage />} />
            <Route path="/events/:eventId" element={<EventOverviewPage />} />
            <Route path="/events/:eventId/planner" element={<PlannerPage />} />
            <Route path="/events/:eventId/venues" element={<VenuesPage />} />
            <Route path="/events/:eventId/vendors" element={<VendorsPage />} />
            <Route path="/events/:eventId/budget" element={<BudgetPage />} />
            <Route path="/events/:eventId/timeline" element={<TimelinePage />} />
            <Route path="/events/:eventId/risks" element={<RisksPage />} />
            <Route path="/events/:eventId/decisions" element={<DecisionsPage />} />
            <Route path="/events/:eventId/agents" element={<AgentsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
