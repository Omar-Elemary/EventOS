import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { BrutalButton, PageKicker } from "../components/ui";
import { setOnboarded, signupAccount } from "../lib/auth";

export function SignupPage() {
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setOnboarded();
      await signupAccount(name, email, password);
      nav("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create account");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-10">
      <div className="mb-6 flex items-center gap-2">
        <div className="flex h-10 w-10 items-center justify-center rounded border-2 border-black bg-nb-yellow shadow-nb-sm">
          <Sparkles size={18} />
        </div>
        <span className="font-display text-2xl font-extrabold tracking-tight">EventOS</span>
      </div>
      <PageKicker>Get started</PageKicker>
      <h1 className="mt-2 font-display text-4xl font-extrabold uppercase leading-none">Sign up</h1>
      <p className="mt-2 text-sm font-semibold text-black/70">Your events stay on this account.</p>
      <form onSubmit={onSubmit} className="mt-6 space-y-3">
        <label className="block font-mono text-[11px] font-black uppercase">
          Name
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-lg border-2 border-black bg-white px-3 py-2.5 font-sans text-sm font-semibold shadow-nb-sm"
          />
        </label>
        <label className="block font-mono text-[11px] font-black uppercase">
          Email
          <input
            required
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border-2 border-black bg-white px-3 py-2.5 font-sans text-sm font-semibold shadow-nb-sm"
          />
        </label>
        <label className="block font-mono text-[11px] font-black uppercase">
          Password
          <input
            required
            type="password"
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border-2 border-black bg-white px-3 py-2.5 font-sans text-sm font-semibold shadow-nb-sm"
          />
        </label>
        {error && <p className="rounded-lg border-2 border-black bg-nb-pink px-3 py-2 text-sm font-bold">{error}</p>}
        <BrutalButton type="submit" disabled={busy} className="w-full py-3">
          {busy ? "Creating…" : "Create account"}
        </BrutalButton>
      </form>
      <p className="mt-4 text-sm font-semibold">
        Already have an account?{" "}
        <Link to="/login" className="font-display font-extrabold uppercase underline">
          Log in
        </Link>
      </p>
    </div>
  );
}
