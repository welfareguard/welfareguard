import { useEffect, useState, type ReactNode } from "react";
import { NavLink, Link } from "react-router-dom";
import { Shield, Sun, Moon, Menu, X, Github } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Start here", end: true },
  { to: "/try", label: "Try the guard" },
  { to: "/replay", label: "Watch the agents" },
  { to: "/results", label: "Results" },
  { to: "/scenarios", label: "Scenarios" },
  { to: "/learn", label: "Learn" },
];
export const REPO = "https://github.com/welfareguard/welfareguard";

function useTheme() {
  const [dark, setDark] = useState<boolean>(() => {
    try { const s = localStorage.getItem("wg-theme"); if (s) return s === "dark"; } catch { /* private window */ }
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("wg-theme", dark ? "dark" : "light"); } catch { /* ignore */ }
  }, [dark]);
  return [dark, setDark] as const;
}

export default function Layout({ children, loading, error }: { children: ReactNode; loading: boolean; error: string | null }) {
  const [dark, setDark] = useTheme();
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-20 border-b border-line bg-bg/85 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 h-14 flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2 font-display font-bold text-lg" onClick={() => setOpen(false)}>
            <Shield className="h-5 w-5 text-accent" aria-hidden /> WelfareGuard
          </Link>
          <nav aria-label="Main" className="hidden md:flex items-center gap-1 ml-6">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => cn("rounded-full px-3 py-1.5 text-sm transition-colors", isActive ? "bg-accent-soft text-accent font-medium" : "text-muted hover:text-ink")}>
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            <a href={REPO} target="_blank" rel="noopener" className="btn-ghost !px-2.5 hidden sm:inline-flex" aria-label="Source on GitHub"><Github className="h-4 w-4" /></a>
            <button type="button" className="btn-ghost !px-2.5" onClick={() => setDark(!dark)} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}>
              {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <button type="button" className="btn-ghost !px-2.5 md:hidden" onClick={() => setOpen(!open)} aria-expanded={open} aria-label="Menu">
              {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>
        {open && (
          <nav aria-label="Main" className="md:hidden border-t border-line bg-bg px-4 py-2 grid gap-1">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} onClick={() => setOpen(false)} className={({ isActive }) => cn("rounded-xl px-3 py-2 text-sm", isActive ? "bg-accent-soft text-accent font-medium" : "text-muted")}>
                {n.label}
              </NavLink>
            ))}
          </nav>
        )}
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 py-8 flex-1 min-w-0">
        {error ? (
          <div role="alert" className="card border-bad/40 bg-bad-soft text-ink max-w-xl mx-auto">
            <h1 className="text-xl mb-2">The data did not load</h1>
            <p className="text-sm">{error}</p>
            <p className="text-sm mt-2 text-muted">The app reads <code className="font-mono">data.json</code> from its own folder. If you run it locally, use <code className="font-mono">npm run dev</code> rather than opening the file directly. If this is the hosted copy, reload once; if it persists, the data file is missing from the deployment.</p>
          </div>
        ) : loading ? (
          <div role="status" aria-live="polite" className="card max-w-xl mx-auto">
            <p className="text-sm text-muted">Loading 768 agent transcripts and the compiled guards…</p>
            <div className="mt-3 grid gap-2"><div className="h-3 w-3/5 rounded bg-accent-soft animate-pulse" /><div className="h-3 w-2/5 rounded bg-accent-soft animate-pulse" /></div>
          </div>
        ) : children}
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto max-w-6xl px-4 py-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted">
          <span>WelfareGuard · Sentient Futures Project Incubator 2026 · Apache-2.0</span>
          <a className="hover:text-accent" href={REPO} target="_blank" rel="noopener">Source code</a>
          <a className="hover:text-accent" href={`${REPO}/blob/main/docs/results/2026-10-22-three-models.md`} target="_blank" rel="noopener">Full results note</a>
          <Link className="hover:text-accent" to="/learn">What the words mean</Link>
        </div>
      </footer>
    </div>
  );
}
