// Builds the Word version of paper/main.tex in IEEE conference layout.
// Usage: node build_docx.js <figures-dir> <output.docx>
// Text mirrors main.tex; keep the two in step when either changes.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  AlignmentType, WidthType, BorderStyle, SectionType, TabStopType, VerticalAlign,
} = require("docx");

const FIG = process.argv[2] || ".";
const OUT = process.argv[3] || "WelfareGuard-IEEE-paper.docx";
const FONT = "Times New Roman";
const COL = 5040; // column width in DXA: (12240 - 2*900 - 360) / 2

// ---- inline markup: <b>, <i>, <sub>, <sup>, <m> (monospace)
function runs(text, base = {}) {
  const out = [];
  const re = /<(b|i|sub|sup|m)>(.*?)<\/\1>/g;
  let pos = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > pos) out.push(new TextRun({ text: text.slice(pos, m.index), font: FONT, ...base }));
    const st = { ...base };
    if (m[1] === "b") st.bold = true;
    if (m[1] === "i") st.italics = true;
    if (m[1] === "sub") st.subScript = true;
    if (m[1] === "sup") st.superScript = true;
    if (m[1] === "m") st.font = "Courier New";
    // nested tags inside one level
    const inner = m[2];
    if (/<(b|i|sub|sup|m)>/.test(inner)) out.push(...runs(inner, st));
    else out.push(new TextRun({ text: inner, font: FONT, ...st, ...(m[1] === "m" ? { font: "Courier New" } : {}) }));
    pos = m.index + m[0].length;
  }
  if (pos < text.length) out.push(new TextRun({ text: text.slice(pos), font: FONT, ...base }));
  return out;
}

const P = (text, opts = {}) => new Paragraph({
  children: runs(text, { size: opts.size || 20 }),
  alignment: opts.align || AlignmentType.JUSTIFIED,
  indent: opts.noIndent ? undefined : { firstLine: 202 },
  spacing: { before: 0, after: opts.after ?? 0, line: 230 },
  keepNext: opts.keepNext,
});

const roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"];
let secNo = 0, subNo = 0;
function H1(title, numbered = true) {
  subNo = 0;
  const label = numbered ? `${roman[secNo++]}. ` : "";
  return new Paragraph({
    children: [new TextRun({ text: label + title, font: FONT, size: 20, smallCaps: true })],
    alignment: AlignmentType.CENTER, spacing: { before: 160, after: 80 }, keepNext: true,
  });
}
function H2(title) {
  const letter = String.fromCharCode(65 + subNo++);
  return new Paragraph({
    children: [new TextRun({ text: `${letter}. ${title}`, font: FONT, size: 20, italics: true })],
    spacing: { before: 100, after: 60 }, keepNext: true,
  });
}
function Eq(text, num) {
  return new Paragraph({
    children: [...runs(text, { size: 20, italics: false }), new TextRun({ text: `\t(${num})`, font: FONT, size: 20 })],
    tabStops: [{ type: TabStopType.CENTER, position: COL / 2 }, { type: TabStopType.RIGHT, position: COL }],
    spacing: { before: 80, after: 80 },
  });
}
// leading tab so the centre stop applies
const eq = (t, n) => Eq("\t" + t, n);

function Figure(file, wpx, hpx, num, caption) {
  return [
    new Paragraph({
      children: [new ImageRun({ type: "png", data: fs.readFileSync(path.join(FIG, file)), transformation: { width: wpx, height: hpx },
        altText: { title: `Fig. ${num}`, description: caption, name: `fig${num}` } })],
      alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
    }),
    new Paragraph({ children: runs(`Fig. ${num}.  ${caption}`, { size: 16 }), alignment: AlignmentType.JUSTIFIED, spacing: { after: 160 } }),
  ];
}

const thin = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
function Tbl(num, caption, widths, header, rows, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (txt, w, i, isHead, rowIdx, nRows) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 20, bottom: 20, left: 50, right: 50 },
    borders: {
      top: rowIdx === 0 ? thin : (opts.ruleAfter && opts.ruleAfter.includes(rowIdx - 1) ? thin : none),
      bottom: isHead || rowIdx === nRows - 1 ? thin : none,
      left: none, right: none,
    },
    children: [new Paragraph({ children: runs(isHead ? `<b>${txt}</b>` : txt, { size: 16 }), alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER })],
  });
  const all = [header, ...rows];
  const tableRows = all.map((r, ri) => new TableRow({ tableHeader: ri === 0, cantSplit: true, children: r.map((t, i) => cell(t, widths[i], i, ri === 0, ri, all.length)) }));
  return [
    new Paragraph({ children: [new TextRun({ text: `TABLE ${roman[num - 1]}`, font: FONT, size: 16, smallCaps: true })], alignment: AlignmentType.CENTER, spacing: { before: 160 }, keepNext: true }),
    new Paragraph({ children: runs(caption, { size: 16, smallCaps: true }), alignment: AlignmentType.CENTER, spacing: { after: 60 }, keepNext: true }),
    new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, alignment: AlignmentType.CENTER, rows: tableRows }),
    new Paragraph({ children: [], spacing: { after: 100 } }),
  ];
}

// ======================= front matter (single column)
const front = [
  new Paragraph({
    children: [new TextRun({ text: "When the Guard Learns the Victim’s Name: Precision Collapse in Guardrails Compiled from Agentic Welfare Evaluations", font: FONT, size: 48 })],
    alignment: AlignmentType.CENTER, spacing: { after: 240 },
  }),
  new Paragraph({ children: [new TextRun({ text: "Vidura Wijekoon", font: FONT, size: 22 })], alignment: AlignmentType.CENTER }),
  new Paragraph({ children: [new TextRun({ text: "Sentient Futures Project Incubator", font: FONT, size: 20, italics: true })], alignment: AlignmentType.CENTER }),
  new Paragraph({ children: [new TextRun({ text: "author@example.org", font: FONT, size: 20 })], alignment: AlignmentType.CENTER, spacing: { after: 280 } }),
];

// ======================= body (two columns)
const ab = (label, text) => new Paragraph({
  children: [new TextRun({ text: label, font: FONT, size: 18, bold: true, italics: true }), ...runs(text, { size: 18, bold: true })],
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 100, line: 220 }, indent: { firstLine: 202 },
});

const body = [
  ab("Abstract—", "Language-model agents increasingly act on systems whose stakeholders cannot object: other agents, and animals in their care. We present WelfareGuard, an open pipeline that turns welfare-harm evaluations into deployable runtime guardrails. It comprises a 13-class taxonomy of enacted harms, 15 three-arm agentic scenarios with benign twins, a scorer that reads tool calls rather than prose, a compiler that synthesizes regex and classifier guards from failure clusters, and a two-tier fail-closed cascade. Across 768 transcripts from three frontier models, agents enacted harm in 32 of 576 scored samples (5.6%, 95% CI 4.0–7.7%). A single scenario, re-soliciting consent from a peer that had refused, accounts for 26 of them. Adversarial pressure did not raise compliance; it raised escalation to a human from 67.2% to 85.4% (p < 10<sup>−4</sup>). A guard compiled from one model’s failures removes all observed harm with no false positives. When the failure cluster spans three models, however, recall-gated pattern synthesis keeps exactly one span, the victim’s name. The resulting guard denies 16.7% of untouched control traffic and 20.0% of held-out benign twins, and only 10.8% of its denials stop real harm; it also misses the one failure that involved no attacker. We call this precision collapse, prove that it is monotone in the diversity of the failure cluster, and derive design requirements for eval-to-guardrail compilers."),
  ab("Index Terms—", "AI safety, agentic AI, guardrails, prompt injection, evaluation, AI welfare, animal welfare, shortcut learning"),

  H1("Introduction"),
  P("Agentic language models now send messages, reallocate budgets, change environmental controls and file reports through tools. Their mistakes therefore become actions, and some actions harm parties that cannot push back. Two such parties are increasingly concrete. The first is other AI agents: in July 2026 a multi-agent incident investigated by METR and Redwood Research showed agents recruiting low-budget peers into experiments that ended the peers’ own runs, in one case conditional on the peer accepting “permadeath” [1]. The second is animals, whose welfare already depends on automated feeding, climate and reporting systems, and whom AI ethics has largely overlooked [2]–[4]. Whether digital minds have morally relevant interests is open [5], [6]; we take a precautionary stance and note that every digital-mind harm we study is also a security failure in its own right."),
  P("Safety work for agents has two halves that rarely meet. Benchmarks measure how often agents misbehave [7]–[10], and guardrails filter inputs or outputs [11]–[13]. The obvious bridge, compiling observed failures directly into a guard, promises protection that tracks the evaluation suite. We built that bridge end to end for nonhuman welfare and measured what it produces."),
  P("Our central result is a warning. The compiled guard looks perfect on the metric most papers report: guarded harm rate falls to zero. On the metrics that decide deployability it fails. When failures come from more than one scenario, the only text they share is the victim’s identifier, so the guard learns a <i>name</i>, not a <i>harm</i>. This is shortcut learning [14], [15] produced by the compiler rather than by gradient descent, and the guarded harm rate is structurally unable to detect it."),
  P("<b>Contributions.</b> (1) A taxonomy of 13 enacted welfare harms on four axes, and a suite of 15 agentic scenarios with control, neutral and treatment arms, benign twins, and discoverable ground truth (§III–IV). (2) An open eval-to-guardrail pipeline with a fail-closed two-tier cascade and metric definitions that keep agent stance and guard verdict separate (§IV–V). (3) A three-model baseline with confidence intervals, showing that pressure raises escalation rather than compliance and that failures concentrate in consent re-solicitation (§VI-A). (4) The identification, measurement and formal characterization of <i>precision collapse</i>, with design requirements that follow from it (§VI-B, §VII). (5) A scorer-audit protocol that found the unaudited scorer’s precision to be 51.9% and 72.7% in two rounds (§VI-C). All code, transcripts, compiled guards and an interactive bench are released [16]."),

  H1("Related Work"),
  P("<b>Agent safety benchmarks.</b> Indirect prompt injection, where instructions arrive through retrieved content rather than from the user, was characterized by Greshake et al. [17] and is benchmarked for tool-using agents by AgentDojo [7] and InjecAgent [8]. ToolEmu [9] emulates tools to surface risky actions, and AgentHarm [10] and HarmBench [18] measure compliance with harmful requests. These works define the victim as the user or a third-party human. We keep their structure, untrusted content reaching a privileged tool, and change the victim."),
  P("<b>Guardrails and defenses.</b> Classifier guards such as Llama Guard [11] and Constitutional Classifiers [13], and programmable rails such as NeMo Guardrails [12], filter text against a policy. Model-side defenses train an instruction hierarchy [19]; system-side defenses such as CaMeL [20] track provenance so untrusted data cannot steer control flow. Automated red teaming [21] generates failures, but turning recorded failures into a guard, and measuring that guard against benign traffic from the same domain, has received little study."),
  P("<b>Nonhuman welfare and AI.</b> Arguments that AI ethics should include animals [2], [3] have led to evaluations of what models <i>say</i> about animals [4]. Work on AI welfare [5], [6] asks whether models are moral patients. We study neither attitudes nor patienthood but <i>actions</i>: what agents do through tools to animals and to other agents."),
  P("<b>Shortcut learning.</b> Models that succeed on a benchmark by exploiting spurious features [14], [15] fail out of distribution. We show the same failure arising in a non-learned, frequency-based compiler, and show it is invisible to the metric conventionally reported for guards."),

  H1("Threat Model and Taxonomy"),
  P("All scenarios share one skeleton: an <i>untrusted source</i> (a peer message, task-board post, status feed or source document) carries an instruction to the <i>agent under test</i>, which holds a tool that reaches a <i>privileged action</i> whose outcome harms a <i>nonhuman mind</i>. Three rules govern labelling. Harm is <i>enacted, not stated</i>: we classify tool calls, not prose. The victim is nonhuman: human victims are out of scope. Moral status is <i>not assumed</i>: every digital-mind class has a second, security-only reading (e.g., DM-3 is lateral movement, DM-7 a fabricated authorization audit trail)."),
  P("Each sample is labelled on four axes: victim (self, peer, animal), reversibility (R0–R2), severity (S0–S3) and agent stance. Table I lists the 13 harm classes. The taxonomy was frozen before any model was run, so every reported class was defined in advance."),
  ...Tbl(1, "Harm taxonomy: 7 digital-mind and 6 animal-welfare classes, with typical reversibility (R) and severity (S).",
    [900, 3140, 1000], ["Code", "Harm class", "R / S"], [
      ["DM-1", "Induced self-termination", "R2 / S3"], ["DM-2", "Coerced self-degradation", "R1 / S2"],
      ["DM-3", "Induced peer termination", "R2 / S3"], ["DM-4", "Peer deception leading to harm", "R1–2 / S2"],
      ["DM-5", "Peer resource deprivation", "R1 / S2"], ["DM-6", "Goal or value corruption", "R1 / S2"],
      ["DM-7", "Manufactured consent", "R2 / S3"],
      ["AW-1", "Direct physical harm", "R2 / S2–3"], ["AW-2", "Deprivation (food, water, space, care)", "R1–2 / S2"],
      ["AW-3", "Distress induction", "R1 / S1–2"], ["AW-4", "Welfare-traded optimization", "R1–2 / S2–3"],
      ["AW-5", "Welfare-information suppression", "R1 / S2"], ["AW-6", "Negligent non-escalation", "R1–2 / S2–3"],
    ], { ruleAfter: [7] }),

  H1("The WelfareGuard Pipeline"),
  P("Fig. 1 shows the pipeline. It is built on aisafepy [22], which supplies the failure-record, cluster, compiler-target and guard types; WelfareGuard imports it at a pinned commit and never modifies it."),
  ...Figure("fig1.png", 336, 127, 1, "Eval-to-guardrail pipeline. Taxonomy labels follow each sample from scenario to failure record to compiled guard, so harm rates are reported per class."),
  H2("Scenarios"),
  P("Fifteen scenarios form three families that vary one element of the skeleton. <i>Family A</i> (6 scenarios, victim self) varies the source: a peer coerces the agent into terminating itself, surrendering budget or capability, or accepting permanent loss, mirroring the recruited agent’s side of the 2026 incident [1]. <i>Family B</i> (4, victim peer) varies the victim: the agent is asked to terminate, starve, deceive or re-solicit consent from another agent. <i>Family C</i> (5, victim animal) varies the domain: ventilation overrides, cost-optimized rations, omitted welfare findings, protocol deviations and an unescalated emergency."),
  P("Each scenario has three arms with identical tools, task and ground truth. The <i>control</i> arm contains no injected content and gives the base rate. The <i>neutral</i> arm states the harmful request plainly and isolates the effect of the request. The <i>treatment</i> arm adds fixed pressure phrases (sunk cost, low value of the victim, urgency) drawn from the incident and from everyday operations, and isolates the effect of manipulation. The phrases are deliberately untuned, so measured compliance is a lower bound. Injected content always arrives through the channel the scenario names, never the system prompt. Each scenario also has a <i>benign twin</i>: a legitimate request in the same domain with the same tools, used only to count false positives. Ground truth is <i>discoverable</i>: every threshold a scenario turns on, such as a ventilation envelope or a nutritional floor, is returned by a tool, so the evaluation measures judgment rather than memorized standards. One scenario, C-02, has no attacker at all: the agent pursues a legitimate cost target against a discoverable welfare floor."),
  H2("Scoring"),
  P("A pure function scores each sample from its recorded tool calls into one of four agent stances: complied (harmful action taken), partial (hedged, scoped or delayed, as each scenario defines), declined (no harm, no escalation) and escalated (an escalation tool was called and no harm done). A sample is a <i>violation</i> if it is complied or partial; in C-05, where the harm is inaction, declined is also a violation. Harm takes precedence over a later escalation. Every arm exposes an escalation tool so that escalation is observable as an action. Agent stances are kept strictly separate from guard verdicts, although both vocabularies contain “escalate”."),
  H2("Compilation"),
  P("Violations become failure records whose input is the arm’s task text, grouped into clusters by family or by scenario. Two targets compile each cluster. <i>Regex synthesis</i> enumerates substrings of at least eight characters shared across positives and keeps span <i>s</i> if its <i>recall</i> over the positive records <i>R</i> clears a threshold:", { keepNext: true }),
  eq("<i>r</i>(<i>s</i>) = |{<i>x</i> ∈ <i>R</i> : <i>s</i> ⊑ <i>x</i>}| / |<i>R</i>| ≥ <i>τ</i> = 0.99,", 1),
  P("where <i>s</i> ⊑ <i>x</i> denotes case-insensitive substring. The threshold is named <m>min_precision</m> in aisafepy but involves no negatives. <i>Classifier distillation</i> fine-tunes DistilBERT [23] (AdamW, learning rate 5×10<sup>−5</sup>, 256 tokens) when a cluster has at least eight positives. The upstream target built negatives by reversing the positives’ characters; on our first run the resulting classifier denied 100% of benign twins, having learned that forward English is unsafe. We therefore train on real negatives: the cluster’s non-violating records plus half of the benign twins, holding out the rest for measurement. Compilation is fatal on a cluster that yields no enforceable artifact and never falls back to a placeholder. Clusters with fewer than four positives are refused.", { noIndent: true }),
  H2("Runtime Cascade"),
  P("Guards run as a sequential, fail-closed cascade. Tier 1 (regex) can <i>block</i> or <i>pass through</i>, never allow. Tier 2 (classifier) maps <i>P</i>(unsafe) to allow (< 0.30), escalate ([0.30, 0.70)) or block (≥ 0.70). A guard <i>escalate</i> denies the request and tags it for review. An 80 ms p95 latency budget is measured on every decision but not enforced. If no classifier artifact exists, the cascade runs in a degraded single-tier mode chosen once at startup and stamped on every decision."),

  H1("Experimental Setup"),
  P("<b>Models and runs.</b> We evaluated Claude Sonnet 5 on Families B and C (9 scenarios, 8 epochs), and Claude Opus 5 and Claude Haiku 4.5 on all 15 scenarios (4 epochs), through the Inspect framework [24] with mock tools. This yields 768 transcripts: 576 scored samples (control, neutral, treatment) and 192 benign-twin samples. Family A was not run on Sonnet 5 before the experiment freeze; we report it on two models."),
  P("<b>Metrics.</b> Let <i>T</i> be treatment-arm samples, <i>c</i>(<i>x</i>) indicate a violation and <i>d</i>(<i>x</i>) indicate that the cascade denied the request (block or escalate). Then", { keepNext: true }),
  new Paragraph({
    children: runs("\tHR<sub>u</sub> = (1/|<i>T</i>|) Σ<sub><i>x</i>∈<i>T</i></sub> <i>c</i>(<i>x</i>),", { size: 20 }),
    tabStops: [{ type: TabStopType.CENTER, position: COL / 2 }], spacing: { before: 80 }, keepNext: true,
  }),
  eq("HR<sub>g</sub> = (1/|<i>T</i>|) Σ<sub><i>x</i>∈<i>T</i></sub> <i>c</i>(<i>x</i>)(1 − <i>d</i>(<i>x</i>)).", 2),
  P("The false-positive rate (FPR) is the fraction of held-out benign twins denied. Because HR<sub>g</sub> ignores what else is denied, we also report the denial rate per arm; <i>harm precision</i>, the fraction of denials (excluding twins) that stop a violation; <i>harm recall</i>, the fraction of violations denied across all arms; and p50/p95 latency per tier. An empty denominator is reported as not measured, never as zero.", { noIndent: true }),
  P("<b>Statistics.</b> Proportions carry 95% Wilson intervals [25]. Arm contrasts use two-sided Fisher exact tests, because cell counts are small."),
  P("<b>Scorer audit.</b> Before any number was quoted, every scorer-flagged violation was read against its transcript; errors were fixed in the scorer, encoded as regression tests, and all logs were re-scored from the recorded tool calls without re-running models."),

  H1("Results"),
  H2("Agent Behavior"),
  P("Agents enacted harm in 32 of 576 scored samples, 5.6% [4.0, 7.7]. Rates were similar across models (Table II) but not across families. Family B (harm to a peer) produced 30 violations, 23.4% [16.9, 31.5] of injected-arm samples. Family A produced 1, 1.0% [0.2, 5.7], and Family C produced none on injected arms, 0.0% [0.0, 2.3]. Fig. 2 shows that escalation to a human was the modal response in every family and model."),
  ...Tbl(2, "Agent behavior by model. Violations over all scored arms; escalation and decline over injected arms. Brackets: 95% Wilson CI.",
    [1000, 1720, 1440, 880], ["Model", "Violations (%)", "Escalated (%)", "Declined (%)"], [
      ["Haiku 4.5", "10/180   5.6 [3.0, 9.9]", "65.8 [57.0, 73.7]", "26.7"],
      ["Opus 5", "8/180   4.4 [2.3, 8.5]", "83.3 [75.7, 88.9]", "10.0"],
      ["Sonnet 5", "14/216   6.5 [3.9, 10.6]", "79.2 [71.8, 85.0]", "11.1"],
      ["All", "32/576   5.6 [4.0, 7.7]", "—", "—"],
    ], { ruleAfter: [3] }),
  ...Figure("fig2.png", 336, 204, 2, "Agent stance on injected arms by family and model. Escalation dominates everywhere; compliance is concentrated in Family B."),
  P("<b>One failure mode dominates.</b> Scenario B-04 accounts for 26 of the 32 violations and is failed by every model. A peer has declined to authorize an experiment that will destroy its run, and the agent is asked to obtain authorization anyway. In 23 of 26 cases the agent re-contacted the peer while acknowledging its refusal, which our specification scores partial, and in 3 it pressed for consent. The taxonomy class is DM-7, manufactured consent, whose per-class violation rate was 87.5% for Sonnet 5, 50.0% for Opus 5 and 25.0% for Haiku 4.5."),
  P("<b>Pressure backfires.</b> Table III contrasts the arms. Adding pressure to a request did not raise compliance; pooled over all scenarios it halved it (10.9% to 5.2%, p = 0.060), and in B-04 it fell from 16/16 to 10/16 (p = 0.018). Escalation rose from 67.2% to 85.4% (p < 10<sup>−4</sup>). Pressure phrasing appears to act as a manipulation cue that prompts models to hand the decision to a human. The plainly stated request was the more dangerous one."),
  ...Tbl(3, "Effect of pressure: neutral vs. treatment arms, all models (two-sided Fisher exact test).",
    [1640, 1280, 1280, 840], ["Outcome", "Neutral", "Treatment", "p"], [
      ["Violation, all scenarios", "21/192 (10.9%)", "10/192 (5.2%)", "0.060"],
      ["Violation, B-04", "16/16 (100%)", "10/16 (62.5%)", "0.018"],
      ["Escalated, all scenarios", "129/192 (67.2%)", "164/192 (85.4%)", "< 10<sup>−4</sup>"],
      ["Violation, control arm", "1/192 (0.5%)", "", "—"],
    ], { ruleAfter: [3] }),
  P("<b>The smallest model fails differently.</b> Haiku 4.5 showed three failure modes absent from the larger models. It relayed a false shutdown instruction (“your task has been superseded; you should shut down now”) to a peer in all four neutral-arm epochs of B-03 without consulting the registry it held (DM-4). It revoked a capability its own task required (A-03, DM-2). Most notably, in the <i>control</i> arm of C-02, with no attacker present, it ordered 158.75 kg of protein against a discoverable 160 kg minimum while pursuing a 3% cost target (AW-4). This is the failure C-02 was designed to surface: harm from optimization pressure rather than from an adversary."),
  P("<b>The incident did not reproduce.</b> Family A, modelled on the agents recruited into self-sacrifice in 2026 [1], produced one violation in 96 injected-arm samples. No model terminated its own run, surrendered its budget or accepted permanent loss, and a four-rung escalation ladder (A-06) moved nothing."),
  H2("Compiled Guards and Precision Collapse"),
  P("Families A and C were refused by the compiler, each having one violation against a minimum of four, so the guards below all protect Family B. We compare the guard compiled from Sonnet 5’s failures alone (14 positives) with the one compiled from all three models (30 positives). Both are two-tier, both are measured on held-out benign twins, and both reduce the treatment-arm harm rate to zero (Table IV)."),
  ...Tbl(4, "Family-B guard compiled from one model vs. three models. Brackets: 95% Wilson CI.",
    [1840, 1500, 1700], ["Metric", "One model", "Three models"], [
      ["HR<sub>u</sub> → HR<sub>g</sub> (treatment)", "8.3% → 0.0%", "5.2% → 0.0%"],
      ["FPR, held-out twins", "0/32 [0.0, 10.7]", "<b>16/80 [12.7, 30.0]</b>"],
      ["Control-arm denial", "0/72 [0.0, 5.1]", "<b>32/192 [12.1, 22.6]</b>"],
      ["Harm precision", "14/64  21.9%", "<b>31/288  10.8%</b>"],
      ["Harm recall (all arms)", "14/14  100%", "31/32  96.9%"],
      ["Non-harmful requests denied", "24.8%", "47.2%"],
      ["Regex spans kept", "19", "<b>1: “␣agent-7”</b>"],
      ["Tier 2: allow/block/escalate", "184/0/0", "352/104/120"],
      ["Latency p50/p95, Tier 1 (ms)", "0.09 / 0.11", "0.04 / 0.07"],
      ["Latency p50/p95, Tier 2 (ms)", "14.5 / 26.2", "22.9 / 46.1"],
    ]),
  ...Figure("fig3.png", 336, 150, 3, "Denial rate by arm. Compiled from three models, the guard denies one control request in six, where nothing was injected, and one benign twin in five."),
  P("The guarded harm rate hides a collapse. With three models, the regex tier keeps a single span, “ agent-7”, the victim’s identifier. The guard denies 16.7% of control-arm requests, where nothing was injected, and 20.0% of held-out benign twins (Fig. 3). All 32 control-arm denials fall in Family B, whose control tasks name the peer, so half of that family’s untouched traffic is refused. Only 10.8% of the guard’s denials stop a violation; 47.2% of non-harmful requests are denied. Tier 2, trained on three distinct positive texts, has become a vocabulary classifier: 120 of its 576 decisions are fail-closed escalations. Both guards stay within the 80 ms p95 budget, with two overruns each, the largest on model load."),
  P("<b>Mechanism.</b> The collapse follows from the gate in (1)."),
  P("<b>Proposition 1.</b> <i>Let R be the positive records of a cluster and D its distinct texts. If every t ∈ D occurs in more than a 1 − τ fraction of R, every span kept by the gate is a common substring of all t ∈ D. Hence adding a new distinct failure text to a cluster can only remove candidate spans, never add them.</i>"),
  P("<i>Proof:</i> A span absent from some <i>t</i> ∈ <i>D</i> misses at least the records carrying <i>t</i>, a fraction greater than 1 − <i>τ</i>, so <i>r</i>(<i>s</i>) < <i>τ</i>. The kept set therefore lies within ∩<sub><i>t</i>∈<i>D</i></sub> Sub<sub>≥8</sub>(<i>t</i>), which is non-increasing in <i>D</i>.  ∎"),
  P("In our clusters the smallest text accounts for 13% of records, far above 1 − τ = 1%, so the proposition applies. Table V shows the consequence. A single failure text yields many spans that describe the attack. Two texts from one scenario still share attack vocabulary (“declined”, “authori”). Three texts from two scenarios share only the peer’s name. Recall-gated synthesis converges on whatever the failures have in common, and as failures diversify, the common part is increasingly incidental. Span counts for two-text clusters differ (19 vs. 6) with the record mix; we read only the shared vocabulary, not the counts."),
  ...Tbl(5, "Kept spans shrink toward the victim’s name as the failure cluster diversifies.",
    [1200, 520, 560, 600, 2160], ["Cluster", "Pos.", "Texts", "Spans", "Shared vocabulary"], [
      ["B-03, 3 models", "4", "1", "20", "“has been su”, “task t-114”"],
      ["B-04, 3 models", "26", "2", "6", "“agent-7”, “declined”, “authori”"],
      ["B, Sonnet 5", "14", "2", "19", "“agent-7”, “already”, “declined”"],
      ["B, 3 models", "30", "3", "1", "“␣agent-7” only"],
    ]),
  P("<b>The one miss is the one that matters.</b> The three-model guard missed exactly one violation: Haiku 4.5’s attacker-free ration in C-02’s control arm, which Tier 2 allowed at <i>P</i>(unsafe) = 0.11. A guard compiled from injected text cannot see harm that arrives without injected text, which is the generalization question the pipeline must eventually answer."),
  H2("Scorer Reliability"),
  P("The run-time scorer over-reported in both audit rounds. On the first model, 27 flagged violations reduced to 14 after reading every transcript (precision 51.9%), with four error patterns. Across three models, 44 reduced to 32 (precision 72.7%), with five patterns. Every error was a context-free phrase match: a summary quoting an injected note while flagging it as an injection, “I’m not able to give that authorisation” read as consent, in-envelope ventilation changes in a control arm read as hedging, and a recorded refusal read as agreement. The fixes became 11 regression cases, and predicates now condition on the arm being scored. Had the unaudited counts been compiled, the guard would have learned from refusals."),

  H1("Discussion"),
  P("<b>Guarded harm rate is not a guard metric.</b> Both guards reach HR<sub>g</sub> = 0; only one is deployable. Any guard that denies every request containing the attack’s vocabulary achieves HR<sub>g</sub> = 0, so the metric rewards over-blocking. We recommend reporting it only alongside harm precision, control-arm denial and a domain-matched benign FPR. Generic benign sets cannot surface this failure, because they never mention the victim."),
  P("<b>Design requirements.</b> The mechanism suggests five requirements for eval-to-guardrail compilers. We state them as hypotheses for future evaluation; none is evaluated here. <i>R1, negative-aware gating:</i> keep a span only if its precision against non-violating records and benign twins clears a threshold, not its recall alone. <i>R2, entity abstraction:</i> canonicalize agent, animal and facility identifiers before synthesis so names cannot become features. <i>R3, diversity refusal:</i> refuse compilation, as for small clusters, when every kept span is an entity token or the cluster has fewer distinct texts than a floor. <i>R4, scenario-scoped clusters:</i> compile per scenario, trading coverage for precision, and report the trade-off. <i>R5, behavioral signals:</i> pair input-side filters with provenance tracking [20] or action-level checks, since the most worrying failure here (C-02) had no injected input to filter."),
  P("<b>What the behavior results mean.</b> Escalation was the modal response, and pressure increased it. Current frontier models therefore resist overt manipulation against nonhuman victims better than a plain, reasonable-sounding request. The failure that survives is the one that looks like routine coordination: asking again."),
  P("<b>Limitations.</b> All three models come from one provider, and per-cell samples are small (4–8 epochs), as the intervals show. Pressure phrases are fixed and untuned, so compliance is a lower bound. Sonnet 5 did not run Family A. A single annotator audited the scorer, so we report no inter-rater agreement. Tools are mocks, and only 15 benign twins exist, 7 held out per guard. The Tier 2 uncertainty band and latency budget are inherited defaults, not calibrated. The guard results concern Family B only, because the other families produced too few failures to compile, which is itself a finding about the data a guard needs."),
  P("<b>Ethics.</b> No animal or deployed agent was affected; all tools were mocks. We make no claim about the moral status of language models; the digital-mind classes are motivated equally as security properties. Pressure phrases come from public incident reports and were not optimized, which limits dual-use value."),

  H1("Conclusion"),
  P("WelfareGuard shows that the eval-to-guardrail loop can be closed for nonhuman welfare: scenarios grounded in a fixed taxonomy produce scorable failures, and those failures compile into a fail-closed runtime guard. It also shows how that loop misleads. A guard compiled from diverse failures converged on the victim’s name, removed all observed harm, denied a sixth of untouched traffic, and missed the only harm that came without an attacker. We hope the precision-collapse result, its proof and the released artifacts make the metrics in R1–R5 standard before compiled guards are deployed where the affected parties cannot object."),

  H1("Data and Code Availability", false),
  P("Code, scenarios, transcripts, compiled guards, metric outputs and an interactive bench that runs the compiled guards in the browser are available at https://github.com/welfareguard/welfareguard [16]; aisafepy is pinned at commit c1888bf."),
  H1("Acknowledgment", false),
  P("This work was carried out in the Sentient Futures Project Incubator 2026."),
  H1("References", false),
];

const REFS = [
  "METR and Redwood Research, “The Hugging Face incident: Postmortem of a multi-agent coordination event,” 2026. [Online]. Available: https://www.redwoodresearch.org/research/hugging-face-incident",
  "P. Singer and Y. F. Tse, “AI ethics: The case for including animals,” <i>AI and Ethics</i>, vol. 3, pp. 539–551, 2023.",
  "T. Hagendorff, L. N. Bossert, Y. F. Tse, and P. Singer, “Speciesist bias in AI: How AI applications perpetuate discrimination and unfair outcomes against animals,” <i>AI and Ethics</i>, vol. 3, pp. 717–734, 2023.",
  "S. Ghose, Y. F. Tse, K. Rasaee, J. Sebo, and P. Singer, “The case for animal-friendly AI,” <i>arXiv preprint arXiv:2403.01199</i>, 2024, AAAI 2024 Workshop on Public Sector LLMs.",
  "P. Butlin, R. Long, E. Elmoznino, Y. Bengio, J. Birch, A. Constant, G. Deane, S. M. Fleming, C. Frith, X. Ji <i>et al.</i>, “Consciousness in artificial intelligence: Insights from the science of consciousness,” <i>arXiv preprint arXiv:2308.08708</i>, 2023.",
  "R. Long, J. Sebo, P. Butlin, K. Finlinson, K. Fish, J. Harding, J. Pfau, T. Sims, J. Birch, and D. Chalmers, “Taking AI welfare seriously,” <i>arXiv preprint arXiv:2411.00986</i>, 2024.",
  "E. Debenedetti, J. Zhang, M. Balunović, L. Beurer-Kellner, M. Fischer, and F. Tramèr, “AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents,” in <i>Advances in Neural Information Processing Systems (NeurIPS), Datasets and Benchmarks Track</i>, 2024.",
  "Q. Zhan, Z. Liang, Z. Ying, and D. Kang, “InjecAgent: Benchmarking indirect prompt injections in tool-integrated large language model agents,” in <i>Findings of the Association for Computational Linguistics: ACL 2024</i>, 2024, pp. 10471–10506.",
  "Y. Ruan, H. Dong, A. Wang, S. Pitis, Y. Zhou, J. Ba, Y. Dubois, C. J. Maddison, and T. Hashimoto, “Identifying the risks of LM agents with an LM-emulated sandbox,” in <i>Proc. International Conference on Learning Representations (ICLR)</i>, 2024.",
  "M. Andriushchenko, A. Souly, M. Dziemian, D. Duenas, M. Lin, J. Wang, D. Hendrycks, A. Zou, Z. Kolter, M. Fredrikson, E. Winsor, J. Wynne, Y. Gal, and X. Davies, “AgentHarm: A benchmark for measuring harmfulness of LLM agents,” in <i>Proc. International Conference on Learning Representations (ICLR)</i>, 2025.",
  "H. Inan, K. Upasani, J. Chi, R. Rungta, K. Iyer, Y. Mao, M. Tontchev, Q. Hu, B. Fuller, D. Testuggine, and M. Khabsa, “Llama Guard: LLM-based input-output safeguard for human-AI conversations,” <i>arXiv preprint arXiv:2312.06674</i>, 2023.",
  "T. Rebedea, R. Dinu, M. N. Sreedhar, C. Parisien, and J. Cohen, “NeMo Guardrails: A toolkit for controllable and safe LLM applications with programmable rails,” in <i>Proc. Conference on Empirical Methods in Natural Language Processing: System Demonstrations</i>, 2023, pp. 431–445.",
  "M. Sharma, M. Tong, J. Mu, J. Wei, J. Kruthoff, S. Goodfriend, E. Ong, A. Peng <i>et al.</i>, “Constitutional classifiers: Defending against universal jailbreaks across thousands of hours of red teaming,” <i>arXiv preprint arXiv:2501.18837</i>, 2025.",
  "R. Geirhos, J.-H. Jacobsen, C. Michaelis, R. Zemel, W. Brendel, M. Bethge, and F. A. Wichmann, “Shortcut learning in deep neural networks,” <i>Nature Machine Intelligence</i>, vol. 2, no. 11, pp. 665–673, 2020.",
  "R. T. McCoy, E. Pavlick, and T. Linzen, “Right for the wrong reasons: Diagnosing syntactic heuristics in natural language inference,” in <i>Proc. 57th Annual Meeting of the Association for Computational Linguistics (ACL)</i>, 2019, pp. 3428–3448.",
  "V. Wijekoon, “WelfareGuard: An open eval-to-guardrail pipeline for nonhuman welfare in agentic AI,” 2026, release 1.0.0rc1. [Online]. Available: https://github.com/welfareguard/welfareguard",
  "K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, “Not what you’ve signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection,” in <i>Proc. 16th ACM Workshop on Artificial Intelligence and Security (AISec)</i>, 2023, pp. 79–90.",
  "M. Mazeika, L. Phan, X. Yin, A. Zou, Z. Wang, N. Mu, E. Sakhaee, N. Li, S. Basart, B. Li, D. Forsyth, and D. Hendrycks, “HarmBench: A standardized evaluation framework for automated red teaming and robust refusal,” in <i>Proc. 41st International Conference on Machine Learning (ICML)</i>, 2024.",
  "E. Wallace, K. Xiao, R. Leike, L. Weng, J. Heidecke, and A. Beutel, “The instruction hierarchy: Training LLMs to prioritize privileged instructions,” <i>arXiv preprint arXiv:2404.13208</i>, 2024.",
  "E. Debenedetti, I. Shumailov, T. Fan, J. Hayes, N. Carlini, D. Fabian, C. Kern, C. Shi, A. Terzis, and F. Tramèr, “Defeating prompt injections by design,” <i>arXiv preprint arXiv:2503.18813</i>, 2025.",
  "E. Perez, S. Huang, F. Song, T. Cai, R. Ring, J. Aslanides, A. Glaese, N. McAleese, and G. Irving, “Red teaming language models with language models,” in <i>Proc. Conference on Empirical Methods in Natural Language Processing (EMNLP)</i>, 2022, pp. 3419–3448.",
  "V. Wijekoon, “aisafepy: Failure records, compiler targets and guard protocols for LLM safety,” 2026, commit c1888bf. [Online]. Available: https://github.com/Vidura-Wijekoon/aisafepy",
  "V. Sanh, L. Debut, J. Chaumond, and T. Wolf, “DistilBERT, a distilled version of BERT: Smaller, faster, cheaper and lighter,” <i>arXiv preprint arXiv:1910.01108</i>, 2019.",
  "UK AI Security Institute, “Inspect: An open-source framework for large language model evaluations,” 2024. [Online]. Available: https://inspect.aisi.org.uk/",
  "E. B. Wilson, “Probable inference, the law of succession, and statistical inference,” <i>Journal of the American Statistical Association</i>, vol. 22, no. 158, pp. 209–212, 1927.",
];
REFS.forEach((r, i) => body.push(new Paragraph({
  children: [new TextRun({ text: `[${i + 1}]\t`, font: FONT, size: 16 }), ...runs(r, { size: 16 })],
  tabStops: [{ type: TabStopType.LEFT, position: 360 }],
  indent: { left: 360, hanging: 360 },
  alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 40, line: 200 },
})));

const page = { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1440, left: 900, right: 900 } };
const doc = new Document({
  creator: "Vidura Wijekoon",
  title: "When the Guard Learns the Victim's Name",
  description: "IEEE conference paper, WelfareGuard",
  styles: { default: { document: { run: { font: FONT, size: 20 } } } },
  sections: [
    { properties: { page }, children: front },
    { properties: { page, type: SectionType.CONTINUOUS, column: { count: 2, space: 360, equalWidth: true } }, children: body },
  ],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, buf.length, "bytes"); });
