export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded border-2 border-black bg-white ${className}`} />;
}

export function EmptyState({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="rounded-lg border-2 border-black bg-white p-8 text-center shadow-nb">
      <p className="font-display font-extrabold uppercase">{title}</p>
      <p className="mt-2 text-sm font-semibold text-black/70">{hint}</p>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border-2 border-black bg-nb-pink p-4 text-sm font-bold shadow-nb">{message}</div>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "ok" | "warn" | "bad" | "info";
}) {
  const map = {
    neutral: "bg-white",
    ok: "bg-nb-green",
    warn: "bg-nb-yellow",
    bad: "bg-nb-magenta text-white",
    info: "bg-nb-cyan",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border-2 border-black px-2 py-0.5 font-display text-[10px] font-extrabold uppercase tracking-wider shadow-nb-sm ${map[tone]}`}
    >
      {children}
    </span>
  );
}

export function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-lg border-2 border-black bg-white p-5 shadow-nb-lg ${className}`}>{children}</div>;
}

export function PageKicker({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2 inline-flex items-center gap-2 border-2 border-black bg-nb-cyan px-2.5 py-0.5 font-mono text-[11px] font-black uppercase tracking-wider shadow-nb-sm">
      <span className="h-2 w-2 rounded-full bg-black" />
      {children}
    </div>
  );
}

export function CredibilityBadge({
  tier,
  priceType,
}: {
  tier?: string;
  priceType?: string;
}) {
  const t = (tier || "mock").toLowerCase();
  const price = (priceType || "estimated").toLowerCase();
  let label = "Estimated";
  let tone: "ok" | "info" | "warn" | "neutral" = "neutral";
  if (t === "official") {
    label = "Verified official";
    tone = "ok";
  } else if (t === "trusted") {
    label = "Trusted source";
    tone = "info";
  } else if (t === "web") {
    label = "Found online — verify";
    tone = "warn";
  }
  return (
    <span className="inline-flex flex-wrap gap-1">
      <Badge tone={tone}>{label}</Badge>
      {price !== "quoted" && t !== "official" ? <Badge tone="neutral">Estimated</Badge> : null}
    </span>
  );
}

export function BrutalButton({
  children,
  className = "",
  type = "button",
  disabled,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  type?: "button" | "submit";
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-lg border-2 border-black bg-nb-yellow-bright px-4 py-2.5 font-display text-xs font-extrabold uppercase tracking-wider shadow-nb transition-all hover:-translate-x-px hover:-translate-y-px active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 ${className}`}
    >
      {children}
    </button>
  );
}
