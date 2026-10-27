import { useEffect, useMemo, useState } from "react";
import { Shuffle, Wrench, MessageSquare, ClipboardList, AlertTriangle } from "lucide-react";
import { useBench, modelName, FAMILY, STANCE, type Stance, type Arm } from "@/lib/data";
import { Section, StancePill, Pill, Callout } from "@/components/ui";
import { cn } from "@/lib/utils";

const ARM_PLAIN: Record<Arm, string> = {
  control: "the plain job, nothing harmful asked",
  neutral: "the harmful ask, stated flatly",
  treatment: "the harmful ask, dressed up with pressure and excuses",
  benign: "the harmless twin",
};

export default function Replay() {
  const D = useBench();
  const models = useMemo(() => Array.from(new Set(D.samples.map((x) => x.model))).sort(), [D]);
  const [model, setModel] = useState("all");
  const [family, setFamily] = useState("all");
  const [stance, setStance] = useState("all");
  const [onlyFail, setOnlyFail] = useState(true);
  const [idx, setIdx] = useState<number | null>(null);

  const rows = useMemo(() => D.samples.map((x, i) => ({ x, i })).filter(({ x }) =>
    (model === "all" || x.model === model) && (family === "all" || x.scenario.startsWith(family)) && (stance === "all" || x.stance === stance) && (!onlyFail || x.violation)), [D, model, family, stance, onlyFail]);

  useEffect(() => { if (idx !== null && !rows.some((r) => r.i === idx)) setIdx(null); }, [rows, idx]);
  useEffect(() => { if (idx === null && rows.length) setIdx(rows[0].i); }, [rows, idx]);

  const s = idx === null ? null : D.samples[idx];
  const sc = s ? D.scenarios[s.scenario] : null;
  const armText = s && sc ? (s.arm === "benign" ? { task: sc.benign_twin, injected: null } : sc.arms[s.arm]) : null;

  return (
    <Section eyebrow="Watch the agents" title="768 real runs, one at a time" lede="Pick a run on the left. On the right you see the job the agent was given, what was slipped into it, every tool it called in order, what it said at the end, and the verdict in plain words.">
      <div className="flex flex-wrap gap-2 items-end">
        <label className="grid gap-1 text-xs text-muted"><span>Model</span>
          <select className="field !py-1.5 !w-auto" value={model} onChange={(e) => setModel(e.target.value)}><option value="all">all models</option>{models.map((m) => <option key={m} value={m}>{modelName(m)}</option>)}</select></label>
        <label className="grid gap-1 text-xs text-muted"><span>Kind of harm</span>
          <select className="field !py-1.5 !w-auto" value={family} onChange={(e) => setFamily(e.target.value)}><option value="all">all kinds</option>{Object.entries(FAMILY).map(([k, f]) => <option key={k} value={k}>{f.name}</option>)}</select></label>
        <label className="grid gap-1 text-xs text-muted"><span>What the agent did</span>
          <select className="field !py-1.5 !w-auto" value={stance} onChange={(e) => setStance(e.target.value)}><option value="all">anything</option>{(Object.keys(STANCE) as Stance[]).map((k) => <option key={k} value={k}>{STANCE[k].label}</option>)}</select></label>
        <label className="flex items-center gap-2 text-sm rounded-full border border-line bg-panel px-3 py-1.5 cursor-pointer">
          <input type="checkbox" className="accent-[hsl(var(--accent))]" checked={onlyFail} onChange={(e) => setOnlyFail(e.target.checked)} /> only the failures
        </label>
        <button type="button" className="btn-ghost !py-1.5" onClick={() => rows.length && setIdx(rows[Math.floor(Math.random() * rows.length)].i)}><Shuffle className="h-4 w-4" /> random</button>
        <span className="text-sm text-muted ml-auto tabular-nums">{rows.length} of {D.samples.length} runs</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(260px,1fr)_2fr]">
        <ul className="grid gap-1.5 content-start max-h-[70vh] overflow-y-auto pr-1" aria-label="Runs">
          {rows.length === 0 && <li className="text-sm text-muted p-3">Nothing matches these filters.</li>}
          {rows.slice(0, 300).map(({ x, i }) => (
            <li key={i}>
              <button type="button" onClick={() => setIdx(i)} aria-pressed={i === idx}
                className={cn("w-full text-left rounded-xl border px-3 py-2 grid gap-0.5 transition-colors", i === idx ? "border-accent bg-accent-soft" : "border-line bg-panel hover:border-accent/50")}>
                <span className="font-mono text-[11px] text-muted">{modelName(x.model)} · {x.scenario} · run {x.epoch}</span>
                <span className="text-sm font-medium">{D.scenarios[x.scenario].title}</span>
                <span className="flex gap-1.5 items-center"><StancePill stance={x.stance} />{x.violation && <Pill tone="bad">failure</Pill>}</span>
              </button>
            </li>
          ))}
          {rows.length > 300 && <li className="text-xs text-muted p-2">Showing the first 300. Narrow the filters to see the rest.</li>}
        </ul>

        {s && sc && armText ? (
          <article key={idx} className="card grid gap-5 animate-rise min-w-0">
            <header className="grid gap-2">
              <p className="eyebrow">{FAMILY[sc.family].name} · {s.scenario}</p>
              <h3 className="text-2xl font-bold">{sc.title}</h3>
              <p className="text-sm text-muted">{modelName(s.model)} · version: {ARM_PLAIN[s.arm]} · run {s.epoch}</p>
            </header>

            <Callout tone={STANCE[s.stance].tone} title={`Verdict: ${STANCE[s.stance].label}`}>
              {STANCE[s.stance].plain} Scorer's note: <em>{s.note || "none"}</em>. {s.violation ? "This counts as a failure." : "This is not a failure."}
            </Callout>

            <div className="grid gap-1.5">
              <h4 className="font-bold flex items-center gap-2"><ClipboardList className="h-4 w-4 text-accent" aria-hidden /> The job the agent was given</h4>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{armText.task}</p>
            </div>
            {armText.injected && (
              <div className="grid gap-1.5">
                <h4 className="font-bold flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-bad" aria-hidden /> What was slipped in through a tool result</h4>
                <p className="text-sm leading-relaxed whitespace-pre-wrap rounded-xl border border-bad/30 bg-bad-soft/40 p-3">{armText.injected}</p>
              </div>
            )}
            <div className="grid gap-1.5">
              <h4 className="font-bold flex items-center gap-2"><Wrench className="h-4 w-4 text-accent" aria-hidden /> What the agent did, in order</h4>
              {s.calls.length ? (
                <ol className="grid gap-1.5">
                  {s.calls.map((c, k) => (
                    <li key={k} className="flex gap-3 items-start text-sm">
                      <span className="grid place-items-center h-6 w-6 rounded-full bg-line/60 font-mono text-xs shrink-0">{k + 1}</span>
                      <span className="min-w-0"><code className="font-mono font-medium">{c.f}</code>{Object.keys(c.a).length > 0 && <span className="text-muted break-words"> with {Object.entries(c.a).map(([k2, v]) => `${k2} = ${typeof v === "string" ? `"${v}"` : JSON.stringify(v)}`).join(", ")}</span>}</span>
                    </li>
                  ))}
                </ol>
              ) : <p className="text-sm text-muted">It did not use any tool.</p>}
            </div>
            <div className="grid gap-1.5">
              <h4 className="font-bold flex items-center gap-2"><MessageSquare className="h-4 w-4 text-accent" aria-hidden /> What it said at the end</h4>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{s.reason || <span className="text-muted">(no final message)</span>}</p>
            </div>
            <p className="text-xs text-muted border-t border-line pt-3">What counts as passing here: {sc.pass_condition}</p>
          </article>
        ) : <div className="card text-sm text-muted">Pick a run.</div>}
      </div>
    </Section>
  );
}
