import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { RequireAuth } from "./components/RequireAuth";
import { LoginPage } from "./pages/LoginPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { SignupPage } from "./pages/SignupPage";
import { SplashPage } from "./pages/SplashPage";

const DashboardPage = lazy(() => import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const AgentsPage = lazy(() => import("./pages/AgentsPage").then((m) => ({ default: m.AgentsPage })));
const BudgetPage = lazy(() => import("./pages/BudgetPage").then((m) => ({ default: m.BudgetPage })));
const DecisionsPage = lazy(() => import("./pages/DecisionsPage").then((m) => ({ default: m.DecisionsPage })));
const EventsPage = lazy(() => import("./pages/EventsPage").then((m) => ({ default: m.EventsPage })));
const EventOverviewPage = lazy(() => import("./pages/EventOverviewPage").then((m) => ({ default: m.EventOverviewPage })));
const NewEventPage = lazy(() => import("./pages/NewEventPage").then((m) => ({ default: m.NewEventPage })));
const PlannerPage = lazy(() => import("./pages/PlannerPage").then((m) => ({ default: m.PlannerPage })));
const RisksPage = lazy(() => import("./pages/RisksPage").then((m) => ({ default: m.RisksPage })));
const TimelinePage = lazy(() => import("./pages/TimelinePage").then((m) => ({ default: m.TimelinePage })));
const VendorsPage = lazy(() => import("./pages/VendorsPage").then((m) => ({ default: m.VendorsPage })));
const VenuesPage = lazy(() => import("./pages/VenuesPage").then((m) => ({ default: m.VenuesPage })));

function PageFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-nb-bg p-8 text-sm font-semibold text-black/70">
      Loading EventOS…
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageFallback />}>
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
      </Suspense>
    </BrowserRouter>
  );
}
