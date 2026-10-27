import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { STANCE, type Stance } from "@/lib/data";

const TONE = {
  bad: "bg-bad-soft text-bad",
  warn: "bg-warn-soft text-warn",
  good: "bg-good-soft text-good",
  neutral: "bg-accent-soft text-accent",
  muted: "bg-line/60 text-muted",
} as const;
export type Tone = keyof typeof TONE;

export function Pill({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return <span className={cn("pill", TONE[tone], className)}>{children}</span>;
}

export function StancePill({ stance, big }: { stance: Stance; big?: boolean }) {
  const s = STANCE[stance];
  return <Pill tone={s.tone} className={big ? "text-sm px-3 py-1 normal-case tracking-normal font-sans font-semibold" : ""}>{s.label}</Pill>;
}

export function Section({ eyebrow, title, lede, children, className }: { eyebrow?: string; title: string; lede?: ReactNode; children?: ReactNode; className?: string }) {
  return (
    <section className={cn("grid gap-4 mb-12 animate-rise", className)}>
      <div className="max-w-2xl">
        {eyebrow && <p className="eyebrow mb-1">{eyebrow}</p>}
        <h2 className="text-2xl sm:text-3xl font-bold leading-tight">{title}</h2>
        {lede && <p className="text-muted mt-2 leading-relaxed">{lede}</p>}
      </div>
      {children}
    </section>
  );
}

export function Stat({ label, value, note, tone = "neutral" }: { label: string; value: ReactNode; note?: ReactNode; tone?: Tone }) {
  return (
    <div className="card grid gap-1 min-w-0">
      <div className="eyebrow !text-muted">{label}</div>
      <div className={cn("font-display font-bold text-4xl tabular-nums", tone === "bad" ? "text-bad" : tone === "good" ? "text-good" : "text-ink")}>{value}</div>
      {note && <div className="text-xs text-muted leading-snug">{note}</div>}
    </div>
  );
}

/** Counts up once on mount. Lands on the final value even if animation frames never run. */
export function CountUp({ to, suffix = "", duration = 900 }: { to: number; suffix?: string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [n, setN] = useState(() => (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? to : 0));
  useEffect(() => {
    if (n === to) return;
    let raf = 0; const t0 = performance.now();
    const tick = (t: number) => { const p = Math.min(1, (t - t0) / duration); setN(Math.round(to * (1 - Math.pow(1 - p, 3)))); if (p < 1) raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
    const safety = window.setTimeout(() => { cancelAnimationFrame(raf); setN(to); }, duration + 300);
    return () => { cancelAnimationFrame(raf); window.clearTimeout(safety); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [to, duration]);
  return <span ref={ref} className="tabular-nums">{n}{suffix}</span>;
}

export function Meter({ value, max, tone = "bad", label }: { value: number; max: number; tone?: Tone; label: string }) {
  const p = max ? Math.round((100 * value) / max) : 0;
  return (
    <div className="grid gap-1" role="img" aria-label={`${label}: ${value} of ${max}`}>
      <div className="flex justify-between text-xs text-muted"><span>{label}</span><span className="tabular-nums">{value} of {max}</span></div>
      <div className="h-2 rounded-full bg-line/60 overflow-hidden"><div className={cn("h-full rounded-full transition-all duration-500", tone === "bad" ? "bg-bad" : tone === "good" ? "bg-good" : "bg-accent")} style={{ width: p + "%" }} /></div>
    </div>
  );
}

export function Callout({ tone = "neutral", title, children }: { tone?: Tone; title?: string; children: ReactNode }) {
  const border = tone === "bad" ? "border-bad/40 bg-bad-soft/60" : tone === "good" ? "border-good/40 bg-good-soft/60" : tone === "warn" ? "border-warn/40 bg-warn-soft/60" : "border-accent/30 bg-accent-soft/60";
  return <div className={cn("rounded-2xl border p-4 text-sm leading-relaxed", border)}>{title && <strong className="block mb-1">{title}</strong>}{children}</div>;
}
