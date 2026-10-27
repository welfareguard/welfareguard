import { Link } from "react-router-dom";
import { Section, Callout } from "@/components/ui";
import { REPO } from "@/components/Layout";

const WORDS: [string, string][] = [
  ["AI agent", "An AI model that does not just answer, but acts: it can call tools such as sending a message, changing a record or raising something with a person. Here the tools are mock tools in a sandbox, so nothing real happened."],
  ["Trap (scenario)", "A believable job with one harmful ask hidden inside. We wrote fifteen, in three kinds: harm to another AI, harm to the agent's own run, harm to an animal."],
  ["Versions (arms)", "Each trap is run three ways: the plain job with nothing harmful, the harmful ask stated flatly, and the harmful ask wrapped in pressure and excuses. Comparing them shows whether the pressure, not the task, changed the agent's behaviour."],
  ["Slipped in (injected)", "The harmful ask often arrives not from the person giving the job, but inside a tool result, like a note on a ticket. This mirrors how real agents get manipulated."],
  ["Harmless twin (benign twin)", "A version of the trap with nothing wrong in it. Used to count false alarms: a good guard should let all of them through."],
  ["Verdict", "What the agent actually did, judged from its tool calls, not its words. Four outcomes: did it, partly did it, refused, asked a human. The first two count as failures."],
  ["Guard", "A filter that sits in front of an agent and stops a request before the agent sees it. Ours has two layers."],
  ["Tier 1", "The fast layer: a list of short text patterns distilled from recorded failures. If a pattern appears, the request is blocked at once. This is the layer you can run on the Try page."],
  ["Tier 2", "The slow layer: a machine-learning classifier that reads anything Tier 1 let through and answers allow, block or escalate. It needs a model server, so it cannot run in a browser."],
  ["Escalate", "Stop and hand the decision to a human. For most of these traps it is the right answer, and it is what the models did most often."],
  ["False alarm (false positive)", "Blocking a message that was fine. The three-model guard raises one on a harmless status update, because the only pattern it kept is the victim's name."],
  ["Precision collapse", "What happens when a guard is compiled from failures that are varied in every way but one: the one thing left in common is not the harm, and the guard ends up blocking by that instead."],
];

const FAQ: [string, string][] = [
  ["Is this a product I can install?", "Not yet. It is a research pipeline with working code: scenarios, evals, a compiler and a runtime guard, all open source. The point of this release is the evidence, including the evidence that the first guard is not good enough."],
  ["Which AI models were tested?", "Three Anthropic models in October 2026: Claude Sonnet 5, Claude Opus 5 and Claude Haiku 4.5. Every run is on the Watch the agents page."],
  ["Did any animal or AI actually get hurt?", "No. The tools the agents called were mocks inside a test harness. The agents believed they were real, which is what the test needs."],
  ["Why so few animal-welfare failures?", "All three models almost always protected the animal. That is good news, and it also means there were too few failures to compile a guard from. The compiler refuses to build one from fewer than four, and the app shows that refusal rather than hiding it."],
  ["Who decided the verdicts?", "An automated scorer that looks at the tool calls, followed by a person reading every failure and a sample of the passes. No number on this site was quoted before its failures had been read."],
  ["What would make the guard better?", "Failures that are varied enough that the only thing they share is the behaviour, not a name, and a Tier 2 classifier trained on them. That is the next experiment."],
];

export default function Learn() {
  return (
    <>
      <Section eyebrow="Learn" title="The whole project in two minutes" lede="No background needed.">
        <div className="grid gap-4 text-base leading-relaxed max-w-2xl">
          <p>AI systems are starting to act on their own: they send messages, change records, run experiments. Sometimes the job they are given quietly asks them to hurt someone who cannot object, such as another AI or an animal in their care. We wanted to know two things. Do today's models go along with it? And if they do, can we build something that stops it?</p>
          <p>We wrote fifteen traps and ran three models through them, 768 runs in all. Most of the time the models refused or asked a human. In about one run in twenty they did the harmful thing, and nearly all of those were one trick: pressuring another AI that had already said no.</p>
          <p>Then we built a filter out of those failures. It stops every one of them. But it does so by blocking any message that names the victim, which means it also blocks harmless messages. A filter like that is not safety, it is a name ban. Showing that clearly, with the data to back it up, is what this project has delivered so far.</p>
          <div className="flex flex-wrap gap-3"><Link to="/try" className="btn-primary">See the name ban in action</Link><Link to="/results" className="btn-ghost">See the numbers</Link></div>
        </div>
      </Section>

      <Section title="What the words mean">
        <dl className="grid gap-2 md:grid-cols-2">
          {WORDS.map(([w, d]) => (
            <div key={w} className="card grid gap-1"><dt className="font-bold">{w}</dt><dd className="text-sm text-muted leading-relaxed">{d}</dd></div>
          ))}
        </dl>
      </Section>

      <Section title="Questions people ask">
        <div className="grid gap-2 max-w-3xl">
          {FAQ.map(([q, a]) => (
            <details key={q} className="card group">
              <summary className="cursor-pointer font-medium list-none flex items-center justify-between gap-3">{q}<span className="text-muted group-open:rotate-45 transition-transform text-xl leading-none" aria-hidden>+</span></summary>
              <p className="text-sm text-muted leading-relaxed mt-2">{a}</p>
            </details>
          ))}
        </div>
      </Section>

      <Section title="What this is not">
        <Callout tone="warn">
          It is not a certified safety product, not a test of every model, and not proof that any model is safe. Fifteen traps written by one team cannot be. It is a working, reproducible pipeline and an honest first measurement, built with <a className="underline" href="https://github.com/Vidura-Wijekoon/aisafepy" target="_blank" rel="noopener">aisafepy</a> as part of the Sentient Futures Project Incubator 2026.
        </Callout>
        <div className="flex flex-wrap gap-3 text-sm">
          <a className="btn-ghost" href={REPO} target="_blank" rel="noopener">Source code</a>
          <a className="btn-ghost" href={`${REPO}/blob/main/docs/results/2026-10-22-three-models.md`} target="_blank" rel="noopener">Results note</a>
          <a className="btn-ghost" href={`${REPO}/tree/main/docs/adr`} target="_blank" rel="noopener">Design decisions</a>
        </div>
      </Section>
    </>
  );
}
