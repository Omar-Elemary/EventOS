import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { getSession, hasOnboarded } from "../lib/auth";

export function SplashPage() {
  const nav = useNavigate();

  useEffect(() => {
    const t = window.setTimeout(() => {
      if (getSession() && hasOnboarded()) nav("/", { replace: true });
      else if (!hasOnboarded()) nav("/onboarding", { replace: true });
      else nav("/login", { replace: true });
    }, 1800);
    return () => window.clearTimeout(t);
  }, [nav]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-nb-magenta px-6 text-white">
      <div className="flex h-20 w-20 items-center justify-center rounded-2xl border-4 border-black bg-nb-cyan text-black shadow-nb-xl pulse-neo">
        <Sparkles size={36} />
      </div>
      <h1 className="mt-6 font-display text-5xl font-extrabold uppercase tracking-tight">EventOS</h1>
      <p className="mt-2 rounded border-2 border-black bg-nb-yellow px-2 py-0.5 font-mono text-xs font-black uppercase text-black shadow-nb-sm">
        v2.4 · AI event crew
      </p>
    </div>
  );
}
