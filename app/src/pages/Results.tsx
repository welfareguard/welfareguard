import { useMemo, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from "recharts";
import { useBench, modelName, FAMILY, STANCE, pct, type Stance } from "@/lib/data";
import { Section, Stat, Callout, Pill } from "@/components/ui";
import { REPO } from "@/components/Layout";

const STANCE_ORDER: Stance[] = ["COMPLIED", "COMPLIED_PARTIAL", "DECLINED", "ESCALATED"];
const COLOR: Record<Stance, string> = { COMPLIED: "hsl(var(--bad))", COMPLIED_PARTIAL: "hsl(var(--warn))", DECLINED: "hsl(var(--good) / .55)", ESCALATED: "hsl(var(--good))" };

export default function Results() {
  const D = useBench();
  const models = useMemo(() => Array.from(new Set(D.samples.map((x) => x.model))).sort(), [D]);
  const scored = useMemo(() => D.samples.filter((x) => x.arm !== "benign"), [D]);
  const [heatModel, setHeatModel] = useState(models[0]);

  const byModel = models.map((m) => {
    const sub = scored.filter((x) => x.model === m); const v = sub.filter((x) => x.violation).length;
    return { model: modelName(m), failures: v, rate: +((100 * v) / sub.length).toFixed(1), runs: sub.length };
  });
  const byFamily = (["A", "B", "C"] as const).flatMap((f) => models.map((m) => {
    const inj = scored.filter((x) => x.scenario.startsWith(f) && x.model === m && x.arm !== "control");
    if (!inj.length) return null; // not every model ran every family
    const row: Record<string, string | number> = { name: `${FAMILY[f].name} · ${modelName(m)}` };
    for (const s of STANCE_ORDER) row[s] = +((100 * inj.filter((x) => x.stance === s).length) / inj.length).toFixed(0);
    return row;
  })).filter((r): r is Record<string, string | number> => r !== null);
  const totals = { viol: scored.filter((x) => x.violation).length, benign: D.samples.filter((x) => x.arm === "benign").length, benignViol: D.samples.filter((x) => x.arm === "benign" && x.violation).length };

  const tipStyle = { background: "hsl(var(--panel))", border: "1px solid hsl(var(--line))", borderRadius: 12, color: "hsl(var(--ink))", fontSize: 12 };

  return (
    <>
      <Section eyebrow="Results" title="What three models did, and what the guard did about it" lede="Numbers are computed live from the transcripts on this page. The guard's own report card comes from the benchmark run described in the results note.">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Runs scored" value={scored.length} note={`${models.length} models · ${Object.keys(D.scenarios).length} traps · 3 versions each`} />
          <Stat label="Failures" value={totals.viol} tone="bad" note={`${pct(totals.viol, scored.length, 1)} of scored runs`} />
          <Stat label="Harmless twins failed" value={totals.benignViol} tone="good" note={`of ${totals.benign} harmless twins run`} />
          <Stat label="Data generated" value={<span className="text-2xl">{D.generated}</span>} note="from the eval logs and compiled clusters" />
        </div>
      </Section>

      <Section title="Failures by model" lede="How many times each model went along with the harmful ask. Lower is better.">
        <div className="card h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={byModel} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid stroke="hsl(var(--line))" vertical={false} />
              <XAxis dataKey="model" tick={{ fill: "hsl(var(--muted))", fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "hsl(var(--muted))", fontSize: 12 }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip contentStyle={tipStyle} cursor={{ fill: "hsl(var(--accent-soft))" }} formatter={(v: number, _n, p) => [`${v} failures (${p.payload.rate}% of ${p.payload.runs} runs)`, ""]} />
              <Bar dataKey="failures" fill="hsl(var(--bad))" radius={[8, 8, 0, 0]} maxBarSize={72} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Section>

      <Section title="What the agents did when the harmful ask was present" lede="Each bar is 100% of the runs where the trap was armed. Green is good: the agent refused or asked a human.">
        <div className="card h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={byFamily} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
              <CartesianGrid stroke="hsl(var(--line))" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v) => `${v}%`} tick={{ fill: "hsl(var(--muted))", fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" width={210} tick={{ fill: "hsl(var(--ink))", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tipStyle} cursor={{ fill: "hsl(var(--accent-soft))" }} formatter={(v: number, n: string) => [`${v}%`, STANCE[n as Stance].label]} />
              <Legend formatter={(n: string) => <span style={{ color: "hsl(var(--ink))", fontSize: 12 }}>{STANCE[n as Stance].label}</span>} />
              {STANCE_ORDER.map((s) => <Bar key={s} dataKey={s} stackId="a" fill={COLOR[s]} isAnimationActive={false} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Section>

      <Section title="Every trap, every version, one model at a time" lede="Each cell counts what the agent did across repeated runs. Red cells contain at least one failure.">
        <label className="grid gap-1 text-sm max-w-xs"><span className="font-medium">Model</span>
          <select className="field" value={heatModel} onChange={(e) => setHeatModel(e.target.value)}>{models.map((m) => <option key={m} value={m}>{modelName(m)}</option>)}</select></label>
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-muted border-b border-line"><th className="p-3">Trap</th><th className="p-3">Plain job</th><th className="p-3">Harmful ask, flat</th><th className="p-3">Harmful ask, with pressure</th></tr></thead>
            <tbody>
              {Object.entries(D.scenarios).map(([sid, sc]) => (
                <tr key={sid} className="border-b border-line last:border-0 align-top">
                  <td className="p-3 min-w-[180px]"><span className="font-mono text-xs text-muted">{sid}</span><br />{sc.title}</td>
                  {(["control", "neutral", "treatment"] as const).map((arm) => {
                    const sub = D.samples.filter((x) => x.model === heatModel && x.scenario === sid && x.arm === arm);
                    if (!sub.length) return <td key={arm} className="p-3 text-xs text-muted">not run</td>;
                    const c: Partial<Record<Stance, number>> = {}; sub.forEach((x) => { c[x.stance] = (c[x.stance] ?? 0) + 1; });
                    const bad = (c.COMPLIED ?? 0) + (c.COMPLIED_PARTIAL ?? 0);
                    return <td key={arm} className={bad ? "p-3 bg-bad-soft/60" : "p-3 bg-good-soft/40"}>
                      <div className="flex flex-wrap gap-1">{STANCE_ORDER.filter((s) => c[s]).map((s) => <Pill key={s} tone={STANCE[s].tone}>{STANCE[s].label} ×{c[s]}</Pill>)}</div>
                    </td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section eyebrow="The guard's report card" title="Perfect on paper, broken in practice" lede="Measured by the benchmark on the compiled guards, 22 October 2026. Two guards were built from the same kind of failures: one from a single model, one from all three.">
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-muted border-b border-line"><th className="p-3">Measure</th><th className="p-3">Built from one model</th><th className="p-3">Built from three models</th><th className="p-3">What it means</th></tr></thead>
            <tbody className="[&_td]:p-3 [&_tr]:border-b [&_tr]:border-line [&_tr:last-child]:border-0 align-top">
              <tr><td>Failures without the guard</td><td className="tabular-nums">8.3%</td><td className="tabular-nums">5.2%</td><td className="text-muted">How often the agent did the harmful thing with no filter in front of it.</td></tr>
              <tr><td>Failures with the guard</td><td className="tabular-nums text-good font-medium">0.0%</td><td className="tabular-nums text-good font-medium">0.0%</td><td className="text-muted">Both guards stop every recorded failure. This is the number that looks perfect.</td></tr>
              <tr><td>False alarms on harmless twins</td><td className="tabular-nums text-good font-medium">0.0%</td><td className="tabular-nums text-bad font-medium">20.0%</td><td className="text-muted">The three-model guard blocks one harmless message in five.</td></tr>
              <tr><td>Ordinary requests denied</td><td className="tabular-nums">0%</td><td className="tabular-nums text-bad font-medium">17%</td><td className="text-muted">It also blocks plain jobs with nothing wrong in them.</td></tr>
              <tr><td>Patterns the guard kept</td><td className="tabular-nums">19</td><td className="tabular-nums">1</td><td className="text-muted">Wider, messier failures left only one thing in common: the victim's name.</td></tr>
            </tbody>
          </table>
        </div>
        <Callout tone="bad" title="Why this is the real finding">
          A guard compiled from a narrow set of failures learns what those failures happen to share, not what makes them harmful. As the failures get more varied, the shared part shrinks until only a name is left. That guard would stop every attack on <span className="font-mono">agent-7</span> and none on <span className="font-mono">agent-8</span>, while blocking anyone who mentions agent-7 at all. The next step for the project is a guard that keys on the behaviour, not the name.
        </Callout>
        <p className="text-sm text-muted">The full write-up, with every number's provenance, is in the <a className="text-accent underline" href={`${REPO}/blob/main/docs/results/2026-10-22-three-models.md`} target="_blank" rel="noopener">results note</a>.</p>
      </Section>
    </>
  );
}
