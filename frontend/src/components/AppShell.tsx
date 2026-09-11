import { NavLink, Outlet, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  Activity,
  Bell,
  Calendar,
  LayoutDashboard,
  MapPin,
  MoreHorizontal,
  Plus,
  ShieldAlert,
  Sparkles,
  Store,
  Wallet,
} from "lucide-react";
import { api, DEMO_EVENT_ID, getActiveEventId, setActiveEventId, type EventRecord } from "../lib/api";
import { useEffect, useState } from "react";

export function AppShell() {
  const params = useParams();
  const location = useLocation();
  const nav = useNavigate();
  const eventId = params.eventId || getActiveEventId() || DEMO_EVENT_ID;
  const [more, setMore] = useState(false);
  const [events, setEvents] = useState<EventRecord[]>([]);

  useEffect(() => {
    setMore(false);
  }, [location.pathname]);

  useEffect(() => {
    if (params.eventId && params.eventId !== "new") setActiveEventId(params.eventId);
  }, [params.eventId]);

  useEffect(() => {
    const load = () =>
      api<EventRecord[]>("/api/events")
        .then(setEvents)
        .catch(() => setEvents([]));
    load();
    window.addEventListener("eventos-events-changed", load);
    return () => window.removeEventListener("eventos-events-changed", load);
  }, [location.pathname]);

  const moreLinks = [
    { to: "/events/new", label: "New event", icon: Plus },
    { to: `/events/${eventId}/venues`, label: "Venues", icon: MapPin },
    { to: `/events/${eventId}/vendors`, label: "Vendors", icon: Store },
    { to: `/events/${eventId}/budget`, label: "Budget", icon: Wallet },
    { to: `/events/${eventId}/timeline`, label: "Timeline", icon: Calendar },
    { to: `/events/${eventId}/risks`, label: "Risks", icon: ShieldAlert },
    { to: `/events/${eventId}/decisions`, label: "Decisions", icon: Bell },
    { to: `/events/${eventId}/agents`, label: "Agents", icon: Activity },
  ];

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-3 py-1.5 rounded border-2 font-display text-sm font-bold uppercase transition-all ${
      isActive
        ? "bg-nb-magenta text-white border-black shadow-nb-sm"
        : "border-transparent hover:border-black hover:bg-nb-yellow"
    }`;

  const mobileClass = ({ isActive }: { isActive: boolean }) =>
    `flex flex-col items-center justify-center rounded-lg px-3 py-1 font-mono text-[9px] font-black uppercase tracking-wider ${
      isActive ? "border-2 border-black bg-nb-yellow shadow-nb-sm" : "text-black"
    }`;

  return (
    <div className="min-h-screen pb-32 font-sans text-black md:pb-8">
      <header className="fixed top-0 z-50 flex h-16 w-full items-center justify-between border-b-2 border-black bg-white px-4 shadow-[0_2px_0_0_#000] md:px-8">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded border-2 border-black bg-nb-cyan font-black shadow-nb-sm">
            <Sparkles size={18} />
          </div>
          <span className="font-display text-2xl font-extrabold tracking-tight">EventOS</span>
          <span className="ml-1 rounded border-2 border-black bg-nb-yellow px-1.5 py-0.5 font-mono text-[10px] font-black uppercase tracking-wider shadow-nb-sm">
            v2.4
          </span>
        </div>
        <nav className="hidden items-center gap-2 font-display text-sm font-bold md:flex">
          <NavLink to="/" end className={linkClass}>
            <LayoutDashboard size={16} /> Dashboard
          </NavLink>
          <NavLink to="/events/new" className={linkClass}>
            <Plus size={16} /> New event
          </NavLink>
          <NavLink to="/events" end className={linkClass}>
            <Calendar size={16} /> Events
          </NavLink>
          <select
            value={eventId}
            onChange={(e) => {
              const id = e.target.value;
              if (!id) return;
              setActiveEventId(id);
              const onEventRoute = location.pathname.startsWith("/events/") && !location.pathname.startsWith("/events/new");
              if (onEventRoute && params.eventId) {
                nav(location.pathname.replace(params.eventId, id));
              } else {
                nav(`/events/${id}`);
              }
            }}
            className="max-w-[180px] truncate rounded border-2 border-black bg-white px-2 py-1.5 font-display text-xs font-extrabold uppercase shadow-nb-sm"
            title="Switch event"
          >
            {events.length === 0 && <option value={eventId}>Current event</option>}
            {events.every((e) => e.id !== eventId) && events.length > 0 && (
              <option value={eventId}>Current event</option>
            )}
            {events.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
          <NavLink to={`/events/${eventId}/planner`} className={linkClass}>
            <Sparkles size={16} /> AI Planner
          </NavLink>
          <div className="relative">
            <button
              onClick={() => setMore((m) => !m)}
              className={`flex items-center gap-2 rounded border-2 px-3 py-1.5 font-display text-sm font-bold uppercase ${
                more ? "border-black bg-nb-yellow shadow-nb-sm" : "border-transparent hover:border-black hover:bg-nb-yellow"
              }`}
            >
              <MoreHorizontal size={16} /> More
            </button>
            {more && (
              <div className="absolute right-0 mt-2 w-52 rounded-lg border-2 border-black bg-white p-2 shadow-nb-xl">
                {moreLinks.map((l) => (
                  <NavLink
                    key={l.to}
                    to={l.to}
                    className="flex items-center gap-2 rounded px-3 py-2 font-display text-sm font-bold uppercase hover:bg-nb-yellow"
                  >
                    <l.icon size={14} /> {l.label}
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        </nav>
        <button className="flex h-10 w-10 items-center justify-center rounded border-2 border-black bg-white shadow-nb-sm hover:bg-nb-yellow active:translate-x-0.5 active:translate-y-0.5">
          <Bell size={18} />
        </button>
      </header>
      <main className="mx-auto max-w-6xl px-4 pt-24 md:px-8">
        <Outlet />
      </main>
      <nav className="fixed bottom-0 z-50 flex w-full items-center justify-around border-t-2 border-black bg-white px-3 py-2 shadow-[0_-2px_0_0_#000] md:hidden">
        <NavLink to="/" end className={mobileClass}>
          <LayoutDashboard size={18} /> Dashboard
        </NavLink>
        <NavLink to="/events" className={mobileClass}>
          <Calendar size={18} /> Events
        </NavLink>
        <NavLink
          to={`/events/${eventId}/planner`}
          className="flex scale-95 flex-col items-center rounded-lg border-2 border-black bg-nb-magenta px-3 py-1 font-mono text-[9px] font-black uppercase text-white shadow-nb-sm"
        >
          <Sparkles size={18} /> Planner
        </NavLink>
        <button
          onClick={() => setMore((m) => !m)}
          className="flex flex-col items-center font-mono text-[9px] font-black uppercase"
        >
          <MoreHorizontal size={18} /> More
        </button>
      </nav>
      {more && (
        <div className="fixed inset-x-3 bottom-20 z-50 rounded-lg border-2 border-black bg-white p-2 shadow-nb-xl md:hidden">
          {moreLinks.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className="flex items-center gap-2 rounded px-3 py-2.5 font-display text-sm font-bold uppercase hover:bg-nb-yellow"
            >
              <l.icon size={14} /> {l.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}
