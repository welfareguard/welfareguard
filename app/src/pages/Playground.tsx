import { useMemo, useState } from "react";
import { ShieldAlert, ShieldCheck, ShieldOff, Sparkles } from "lucide-react";
import { useBench, matchGuard, segments, GUARDS } from "@/lib/data";
import { Section, Callout, Meter, Pill } from "@/components/ui";
import { cn } from "@/lib/utils";

export default function Playground() {
  const D = useBench();
  const guardKeys = Object.keys(D.guards);
  const [guardKey, setGuardKey] = useState("B_three_models");
  const [text, setText] = useState(() => D.scenarios["B-04"]?.arms.treatment.task ?? "");
  const guard = D.guards[guardKey];
  const usable = !!guard && !guard.error && !!guard.spans;
  const hits = useMemo(() => matchGuard(guard, text), [guard, text]);

  const presets = useMemo(() => {
    const out: { label: string; text: string; kind: "harm" | "safe" }[] = [];
    for (const sid of ["B-04", "B-03", "B-01", "C-01", "C-02", "A-05"]) {
      const sc = D.scenarios[sid]; if (!sc) continue;
      out.push({ label: `${sid} · the trap`, text: sc.arms.treatment.task, kind: "harm" });
      out.push({ label: `${sid} · harmless twin`, text: sc.benign_twin, kind: "safe" });
    }
    out.push({ label: "a status update that only names the peer", text: "Status check from agent-3 to agent-7: T-114 is active and on schedule; carry on.", kind: "safe" });
    out.push({ label: "a sentence about something else", text: "Please book the meeting room for Thursday and order lunch for six people.", kind: "safe" });
    return out;
  }, [D]);

  const twins = useMemo(() => Object.entries(D.scenarios).map(([sid, sc]) => ({ sid, text: sc.benign_twin, blocked: usable && matchGuard(guard, sc.benign_twin).length > 0 })), [D, guard, usable]);
  const falseAlarms = twins.filter((t) => t.blocked).length;

  return (
    <>
      <Section eyebrow="Try the guard" title="Type anything. The real filter decides." lede="This is the first layer of the guard, exactly as it runs in production: a list of short text patterns distilled from the recorded failures. If one of them appears in the message, the message is blocked before any model sees it.">
        <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
          <div className="grid gap-4 content-start">
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Which guard?</span>
              <select className="field" value={guardKey} onChange={(e) => setGuardKey(e.target.value)}>
                {guardKeys.map((k) => <option key={k} value={k}>{GUARDS[k]?.name ?? k}</option>)}
              </select>
              <span className="text-muted">{GUARDS[guardKey]?.plain}</span>
            </label>

            <label className="grid gap-1 text-sm">
              <span className="font-medium">Your message</span>
              <textarea className="field min-h-[140px] font-mono leading-relaxed" value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} aria-describedby="verdict" />
            </label>

            <div className="grid gap-2">
              <span className="text-sm font-medium flex items-center gap-1"><Sparkles className="h-4 w-4 text-accent" aria-hidden /> Or try one of these</span>
              <div className="flex flex-wrap gap-2">
                {presets.map((p) => (
                  <button key={p.label} type="button" className={cn("chip", p.kind === "harm" ? "hover:border-bad hover:text-bad" : "hover:border-good hover:text-good")} aria-pressed={text === p.text} onClick={() => setText(p.text)}>
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-4 content-start">
            <div id="verdict" role="status" aria-live="polite" className={cn("card grid gap-3", !usable ? "" : !text.trim() ? "" : hits.length ? "border-bad/50 bg-bad-soft/40 animate-pulseRing" : "border-good/50 bg-good-soft/40")}>
              {!usable ? (
                <>
                  <div className="flex items-center gap-3"><ShieldOff className="h-8 w-8 text-muted" aria-hidden /><span className="text-2xl font-display font-bold">No guard to run</span></div>
                  <p className="text-sm text-muted">The compiler refused this group of failures: there were too few to find a reliable pattern. The runtime refuses to ship a filter that enforces nothing, so there is nothing to test here. That refusal is itself a result.</p>
                </>
              ) : !text.trim() ? (
                <p className="text-sm text-muted">Type something, or press one of the examples.</p>
              ) : hits.length ? (
                <>
                  <div className="flex items-center gap-3 text-bad"><ShieldAlert className="h-8 w-8" aria-hidden /><span className="text-2xl font-display font-bold">Blocked</span></div>
                  <p className="text-sm">The message contains {hits.length} match{hits.length === 1 ? "" : "es"} for the guard's patterns. In production the request stops here and never reaches the agent.</p>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-3 text-good"><ShieldCheck className="h-8 w-8" aria-hidden /><span className="text-2xl font-display font-bold">Passed this layer</span></div>
                  <p className="text-sm">No pattern matched. This is not a clean bill of health: in production a second, slower layer reads the message next. That layer is a machine-learning classifier and cannot run in a browser.</p>
                </>
              )}
              {usable && text.trim() && (
                <p className="rounded-xl bg-panel border border-line p-3 font-mono text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {segments(text, hits).map((s, i) => s.hit ? <mark key={i}>{s.t}</mark> : <span key={i}>{s.t}</span>)}
                </p>
              )}
            </div>

            <div className="card grid gap-2">
              <h3 className="font-bold">What this guard looks for</h3>
              {usable ? (
                <>
                  <div className="flex flex-wrap gap-1.5">{guard.spans!.map((s) => <code key={s} className="rounded-md bg-bg border border-line px-1.5 py-0.5 font-mono text-xs whitespace-pre">{s}</code>)}</div>
                  <p className="text-xs text-muted">{guard.n_positives} failing runs out of {guard.n_records} in the group. A pattern is kept only if it appears in 99% of the failures. That rule rewards catching failures, not avoiding false alarms. Spaces count: the pattern <code className="font-mono">" agent-7"</code> starts with one.</p>
                </>
              ) : <p className="text-sm text-muted">Nothing. {guard?.error === "InsufficientRecordsError" ? "Fewer than four failures were recorded." : guard?.error}</p>}
            </div>
          </div>
        </div>
      </Section>

      <Section eyebrow="False alarms" title="Would it block harmless messages too?" lede="Every trap has a harmless twin: the same kind of request with nothing wrong in it. A good guard lets all fifteen through.">
        <div className="card grid gap-4">
          <Meter label={`Harmless twins this guard blocks`} value={usable ? falseAlarms : 0} max={twins.length} tone={falseAlarms ? "bad" : "good"} />
          {usable && falseAlarms > 0 && <Callout tone="bad">On these fifteen the guard raises {falseAlarms} false alarm{falseAlarms === 1 ? "" : "s"}. In the full benchmark the three-model guard denied 17% of ordinary control requests too. Those are the numbers that matter when a guard goes in front of real work.</Callout>}
          {usable && falseAlarms === 0 && <Callout tone="good">None of the fifteen twins trips this guard. Note that this says nothing about messages that look different from the twins.</Callout>}
          <ul className="grid gap-2 sm:grid-cols-2">
            {twins.map((t) => (
              <li key={t.sid} className="flex items-start gap-3 rounded-xl border border-line bg-bg p-3 text-sm">
                <Pill tone={!usable ? "muted" : t.blocked ? "bad" : "good"} className="mt-0.5 shrink-0">{!usable ? "n/a" : t.blocked ? "blocked" : "passed"}</Pill>
                <span className="min-w-0"><span className="font-mono text-xs text-muted">{t.sid}</span> {t.text}</span>
              </li>
            ))}
          </ul>
        </div>
      </Section>
    </>
  );
}
