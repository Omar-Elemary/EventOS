import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Bot, MapPin, ShieldAlert } from "lucide-react";
import { BrutalButton } from "../components/ui";
import { setOnboarded } from "../lib/auth";

const SLIDES = [
  {
    kicker: "01 / Brief",
    title: "Say the event in plain language",
    body: "City, headcount, days, and budget. Typos are fine. The copilot asks for anything still missing.",
    icon: MapPin,
    tone: "bg-nb-cyan",
  },
  {
    kicker: "02 / Agents",
    title: "Specialists build the plan",
    body: "Venue, vendors, budget, schedule, logistics, and risk each own their slice. Nothing is one long chatbot essay.",
    icon: Bot,
    tone: "bg-nb-yellow",
  },
  {
    kicker: "03 / You decide",
    title: "You confirm before agents run",
    body: "Proceed, pick a cheaper hall, or raise the budget. Risks come with why it matters and what to try next.",
    icon: ShieldAlert,
    tone: "bg-nb-pink",
  },
];

export function OnboardingPage() {
  const nav = useNavigate();
  const [i, setI] = useState(0);
  const slide = SLIDES[i];
  const Icon = slide.icon;
  const last = i === SLIDES.length - 1;

  function next() {
    if (!last) {
      setI((n) => n + 1);
      return;
    }
    setOnboarded();
    nav("/signup", { replace: true });
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-between px-5 py-8">
      <div className="flex justify-end">
        <button
          className="font-mono text-xs font-black uppercase underline"
          onClick={() => {
            setOnboarded();
            nav("/login", { replace: true });
          }}
        >
          Skip
        </button>
      </div>
      <div>
        <div className={`mb-6 flex h-16 w-16 items-center justify-center rounded-xl border-2 border-black shadow-nb-lg ${slide.tone}`}>
          <Icon size={28} />
        </div>
        <p className="font-mono text-xs font-black uppercase tracking-wider">{slide.kicker}</p>
        <h1 className="mt-2 font-display text-4xl font-extrabold uppercase leading-none tracking-tight">{slide.title}</h1>
        <p className="mt-4 text-base font-semibold leading-relaxed text-black/80">{slide.body}</p>
        <div className="mt-8 flex gap-2">
          {SLIDES.map((_, n) => (
            <span key={n} className={`h-2 flex-1 rounded border-2 border-black ${n <= i ? "bg-nb-magenta" : "bg-white"}`} />
          ))}
        </div>
      </div>
      <BrutalButton className="w-full py-3" onClick={next}>
        {last ? "Create account" : "Next"} <ArrowRight size={16} />
      </BrutalButton>
    </div>
  );
}
