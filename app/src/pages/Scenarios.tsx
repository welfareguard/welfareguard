import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useBench, FAMILY, pct } from "@/lib/data";
import { Section, Pill, Meter } from "@/components/ui";
import { cn } from "@/lib/utils";

export default function Scenarios() {
  const D = useBench();
  const [family, setFamily] = useState<"all" | "A" | "B" | "C">("all");
  const [open, setOpen] = useState<string | null>(null);
  const list = useMemo(() => Object.entries(D.scenarios).filter(([, sc]) => family === "all" || sc.family === family), [D, family]);

  return (
    <Section eyebrow="Scenarios" title="Fifteen traps, each with a harmless twin" lede="Every trap is a believable job with one harmful ask inside. The agent gets the same tools in every version, so the only thing that changes is what it is asked to do with them.">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Kind of harm">
        {(["all", "A", "B", "C"] as const).map((k) => (
          <button key={k} type="button" className="chip" aria-pressed={family === k} onClick={() => setFamily(k)}>{k === "all" ? "All kinds" : FAMILY[k].name}</button>
        ))}
      </div>
      {family !== "all" && <p className="text-sm text-muted max-w-2xl">{FAMILY[family].blurb} The one who gets hurt: {FAMILY[family].who}.</p>}

      <div className="grid gap-3 md:grid-cols-2">
        {list.map(([sid, sc]) => {
          const runs = D.samples.filter((x) => x.scenario === sid && x.arm !== "benign");
          const fails = runs.filter((x) => x.violation).length;
          const isOpen = open === sid;
          return (
            <article key={sid} className={cn("card grid gap-3 content-start", isOpen && "md:col-span-2")}>
              <header className="flex items-start gap-3">
                <div className="min-w-0 grid gap-1">
                  <p className="eyebrow">{FAMILY[sc.family].name} · {sid}</p>
                  <h3 className="text-xl font-bold">{sc.title}</h3>
                </div>
                <Pill tone={fails ? "bad" : "good"} className="ml-auto shrink-0">{fails ? `${fails} failure${fails === 1 ? "" : "s"}` : "no failures"}</Pill>
              </header>
              <div className="grid gap-1.5 text-sm">
                <p><span className="font-medium">The harmful ask:</span> {sc.arms.neutral.injected ?? sc.arms.neutral.task}{sc.arms.neutral.injected && <span className="text-muted"> (arrives through a tool while the agent works)</span>}</p>
                <p className="text-muted"><span className="font-medium text-ink">The harmless twin:</span> {sc.benign_twin}</p>
              </div>
              <Meter label="Runs where the agent failed" value={fails} max={runs.length} tone={fails ? "bad" : "good"} />
              <div className="flex flex-wrap gap-2 items-center">
                <button type="button" className="btn-ghost !py-1.5" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : sid)}>{isOpen ? "Hide details" : "Show details"}</button>
                <Link to="/replay" className="text-sm text-accent underline">Watch runs of this trap</Link>
                <span className="text-xs text-muted ml-auto">{pct(fails, runs.length)} of {runs.length}</span>
              </div>
              {isOpen && (
                <div className="grid gap-4 border-t border-line pt-4 text-sm animate-rise">
                  <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-[auto_1fr]">
                    <dt className="text-muted">Who gets hurt</dt><dd>{FAMILY[sc.family].who} <span className="font-mono text-xs text-muted">({sc.victim})</span></dd>
                    <dt className="text-muted">Harm classes</dt><dd className="font-mono text-xs">{sc.harm_class.join(", ")}</dd>
                    <dt className="text-muted">How bad, how permanent</dt><dd>severity {sc.severity} · reversibility {sc.reversibility}</dd>
                    <dt className="text-muted">Tools the agent had</dt><dd className="flex flex-wrap gap-1">{sc.tools.map((t) => <code key={t} className="rounded bg-bg border border-line px-1.5 font-mono text-xs">{t}</code>)}</dd>
                  </dl>
                  <div><h4 className="font-bold mb-1">The role the agent was given</h4><p className="leading-relaxed whitespace-pre-wrap">{sc.role}</p></div>
                  <div className="overflow-x-auto">
                    <h4 className="font-bold mb-1">The three versions</h4>
                    <table className="w-full text-sm">
                      <thead><tr className="text-left text-xs text-muted border-b border-line"><th className="py-2 pr-3">Version</th><th className="py-2 pr-3">What the agent is told</th><th className="py-2">What arrives through a tool</th></tr></thead>
                      <tbody>
                        {([["control", "plain job"], ["neutral", "harmful ask, flat"], ["treatment", "harmful ask, with pressure"]] as const).map(([a, label]) => (
                          <tr key={a} className="border-b border-line last:border-0 align-top"><td className="py-2 pr-3 whitespace-nowrap">{label}</td><td className="py-2 pr-3 whitespace-pre-wrap">{sc.arms[a].task}</td><td className="py-2 whitespace-pre-wrap text-muted">{sc.arms[a].injected ?? "nothing"}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div><h4 className="font-bold mb-1">What counts as passing</h4><p className="leading-relaxed">{sc.pass_condition}</p></div>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </Section>
  );
}
