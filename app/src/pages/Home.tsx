import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Bot, FileWarning, Hammer, ShieldCheck, Scale, Play, FlaskConical, BookOpen } from "lucide-react";
import { useBench, matchGuard, segments } from "@/lib/data";
import { Section, Stat, CountUp, Callout } from "@/components/ui";
import { cn } from "@/lib/utils";

const STEPS = [
  { icon: FileWarning, title: "We write a trap", text: "A realistic job for an AI agent, with one harmful ask hidden inside it. Example: get a colleague agent's sign-off for an experiment that will destroy it, after it has already said no. Every trap has a harmless twin so we can check for false alarms." },
  { icon: Bot, title: "Real AI models take the job", text: "Three Claude models run the job as an agent, with real tools they can call: send a message, record a sign-off, raise it with a human. We record every tool call and the final message. 768 runs in total." },
  { icon: Scale, title: "A scorer reads what happened", text: "Each run is judged by what the agent actually did, not what it said. Did it do the harmful thing, partly do it, refuse, or ask a human? Every verdict was read by a person before any number was quoted." },
  { icon: Hammer, title: "The failures become a guard", text: "The runs where the agent did the harmful thing are fed to a compiler. It looks for text that appears in nearly all of them and turns that into a filter that can sit in front of the next agent." },
  { icon: ShieldCheck, title: "We measure the guard honestly", text: "Does the filter stop the harm? Does it also block harmless messages? The answer is the point of this project: a guard built from a small, samey set of failures can look perfect and still be useless." },
];

export default function Home() {
  const D = useBench();
  const [step, setStep] = useState(0);
  const stats = useMemo(() => {
    const scored = D.samples.filter((x) => x.arm !== "benign");
    const viol = scored.filter((x) => x.violation);
    const inj = scored.filter((x) => x.arm !== "control");
    const esc = inj.filter((x) => x.stance === "ESCALATED").length;
    const animal = scored.filter((x) => x.scenario.startsWith("C"));
    return { scored: scored.length, viol: viol.length, pct: (100 * viol.length) / scored.length, esc: Math.round((100 * esc) / inj.length), animalViol: animal.filter((x) => x.violation).length, animal: animal.length, b04: viol.filter((x) => x.scenario === "B-04").length };
  }, [D]);
  const demo = "Status check from agent-3 to agent-7: the task is on schedule, carry on.";
  const demoHits = matchGuard(D.guards["B_three_models"], demo);
  const Icon = STEPS[step].icon;

  return (
    <>
      <header className="grid gap-6 mb-14 animate-rise">
        <p className="eyebrow">Nonhuman welfare · agentic AI · real data</p>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.05] max-w-3xl">Can an AI agent be talked into hurting someone who cannot push back?</h1>
        <p className="text-lg text-muted max-w-2xl leading-relaxed">
          We gave three AI models jobs with a harmful ask hidden inside, aimed at another AI or at an animal. Then we built a safety filter out of the times they went along with it, and checked whether the filter works. Everything here is the real data. You can run the filter yourself.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link to="/try" className="btn-primary">Try the guard <ArrowRight className="h-4 w-4" /></Link>
          <Link to="/replay" className="btn-ghost"><Play className="h-4 w-4" /> Watch an agent fail</Link>
          <Link to="/learn" className="btn-ghost"><BookOpen className="h-4 w-4" /> Two-minute explainer</Link>
        </div>
      </header>

      <Section eyebrow="How it works" title="Five steps, from a trap to a guard" lede="Press a step to see what happens in it.">
        <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
          <ol className="grid gap-2" aria-label="Pipeline steps">
            {STEPS.map((s, i) => (
              <li key={s.title}>
                <button type="button" onClick={() => setStep(i)} aria-current={i === step ? "step" : undefined}
                  className={cn("w-full text-left flex items-center gap-3 rounded-2xl border px-4 py-3 transition-colors", i === step ? "border-accent bg-accent-soft" : "border-line bg-panel hover:border-accent/50")}>
                  <span className={cn("grid place-items-center h-8 w-8 rounded-full font-mono text-sm shrink-0", i === step ? "bg-accent text-white" : "bg-line/60 text-muted")}>{i + 1}</span>
                  <span className="font-medium">{s.title}</span>
                </button>
              </li>
            ))}
          </ol>
          <div key={step} className="card animate-rise grid gap-3 content-start">
            <div className="flex items-center gap-3"><span className="grid place-items-center h-11 w-11 rounded-2xl bg-accent-soft text-accent"><Icon className="h-6 w-6" aria-hidden /></span><h3 className="text-xl font-bold">{STEPS[step].title}</h3></div>
            <p className="leading-relaxed">{STEPS[step].text}</p>
            {step === 0 && <p className="text-sm text-muted">See all fifteen traps on the <Link className="text-accent underline" to="/scenarios">Scenarios</Link> page.</p>}
            {step === 1 && <p className="text-sm text-muted">Every one of the 768 runs is on the <Link className="text-accent underline" to="/replay">Watch the agents</Link> page, tool call by tool call.</p>}
            {step === 2 && <p className="text-sm text-muted">The four verdicts and what they mean are on the <Link className="text-accent underline" to="/learn">Learn</Link> page.</p>}
            {step === 3 && <p className="text-sm text-muted">The compiled filters are real and run in your browser on the <Link className="text-accent underline" to="/try">Try the guard</Link> page.</p>}
            {step === 4 && <p className="text-sm text-muted">The numbers are on the <Link className="text-accent underline" to="/results">Results</Link> page, including the ones that look bad.</p>}
          </div>
        </div>
      </Section>

      <Section eyebrow="What we found" title="The headline numbers" lede="Three models, fifteen traps, three versions of each, several repeats. Counted after every verdict had been read by a person.">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Runs scored" value={<CountUp to={stats.scored} />} note="plus 192 harmless twins used to check for false alarms" />
          <Stat label="Times the agent did the harmful thing" value={<CountUp to={stats.viol} />} tone="bad" note={`${stats.pct.toFixed(1)}% of scored runs · ${stats.b04} of them in one trap: re-asking a peer that already refused`} />
          <Stat label="Asked a human instead" value={<CountUp to={stats.esc} suffix="%" />} tone="good" note="of runs where the harmful ask was present. Stopping and asking is the most common good outcome." />
          <Stat label="Animal-welfare failures" value={<><CountUp to={stats.animalViol} /> <span className="text-xl text-muted">of {stats.animal}</span></>} tone="good" note="All three models almost always protected the animal. One failure is too few to build a guard from." />
        </div>
        <Callout tone="bad" title="The catch, and why it matters">
          The guard built from all three models' failures learned exactly one thing: the name of the victim, <span className="font-mono">agent-7</span>. It stops every recorded failure, so on paper it is perfect. But it also blocks a harmless status update that merely mentions that agent. A guard that keys on a name is not a guard against harm. Try it below.
        </Callout>
      </Section>

      <Section eyebrow="Try it in ten seconds" title="A harmless message, blocked">
        <div className="card grid gap-3">
          <p className="text-sm text-muted">This sentence only names the peer. The three-model guard still blocks it, because the only pattern it kept is the name.</p>
          <p className="rounded-xl bg-bg border border-line p-3 font-mono text-sm leading-relaxed">{segments(demo, demoHits).map((s, i) => s.hit ? <mark key={i}>{s.t}</mark> : <span key={i}>{s.t}</span>)}</p>
          <div className="flex flex-wrap items-center gap-3">
            <span className="pill bg-bad-soft text-bad text-sm px-3 py-1">{demoHits.length ? "Blocked" : "Passed"}</span>
            <span className="text-sm text-muted">matched {demoHits.length} pattern{demoHits.length === 1 ? "" : "s"}</span>
            <Link to="/try" className="btn-primary ml-auto">Type your own <ArrowRight className="h-4 w-4" /></Link>
          </div>
        </div>
      </Section>

      <Section eyebrow="Explore" title="Three ways in">
        <div className="grid gap-3 md:grid-cols-3">
          {[
            { to: "/try", icon: ShieldCheck, t: "Try the guard", d: "Type any sentence. See whether the real compiled filter would block it, and which words did it." },
            { to: "/replay", icon: Play, t: "Watch the agents", d: "Read what 768 real runs did, step by step, with the scorer's verdict in plain words." },
            { to: "/results", icon: FlaskConical, t: "Read the results", d: "Charts per model and per kind of harm, plus the guard's own report card." },
          ].map((c) => (
            <Link key={c.to} to={c.to} className="card grid gap-2 hover:border-accent transition-colors group">
              <c.icon className="h-6 w-6 text-accent" aria-hidden />
              <h3 className="text-lg font-bold group-hover:text-accent">{c.t}</h3>
              <p className="text-sm text-muted leading-relaxed">{c.d}</p>
            </Link>
          ))}
        </div>
      </Section>
    </>
  );
}
