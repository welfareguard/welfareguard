# Paper: When the Guard Learns the Victim's Name

IEEE conference paper (IEEEtran, two-column) on WelfareGuard's three-model
baseline and the precision collapse of compiled guards. Target length is six
pages including references.

## Layout

| Path | What |
| --- | --- |
| `main.tex` | The paper |
| `references.bib` | 25 references, each checked against its arXiv or proceedings listing |
| `figures/pipeline.tex` | Fig. 1, pipeline (TikZ) |
| `figures/stances.tex` | Fig. 2, agent stance by family and model (pgfplots) |
| `figures/denial.tex` | Fig. 3, denial rate by arm, one-model vs three-model guard (pgfplots) |
| `scripts/compute_stats.py` | Recomputes every number in the paper, standard library only |
| `data/benchmark-B-*.json` | The two benchmark outputs the guard numbers come from |
| `WelfareGuard-IEEE-paper.docx`, `word/` | Word version and its build script |

## Build

Either upload the folder to Overleaf (compiler: pdfLaTeX) or run, from this folder:

```
latexmk -pdf main.tex
```

Needs a standard TeX Live or MiKTeX with `IEEEtran`, `tikz`, `pgfplots`,
`booktabs`, `multirow`, `cite` and `hyperref`. Figures are drawn in LaTeX, so
there are no image files.

## Reproduce the numbers

From the repository root:

```
python paper/scripts/compute_stats.py
```

It reads `docs/bench/data.json` (768 scored transcripts and the compiled spans)
and the two files in `paper/data/` (copies of `python -m welfareguard.benchmark`
output from 22 October 2026) and prints every statistic with its Wilson 95%
interval and every Fisher test, grouped by the table or figure that uses it.

## Provenance

| Paper item | Source |
| --- | --- |
| Table II, Fig. 2, Sec. VI-A | `docs/bench/data.json`, re-scored after the second audit; matches `docs/results/baseline-table.md` |
| Table III | same, neutral vs treatment arms |
| Table IV, Fig. 3 | `paper/data/benchmark-B-one-model.json`, `paper/data/benchmark-B-three-models.json` |
| Table V | `guards` in `docs/bench/data.json` |
| Scorer audit (Sec. VI-C) | `docs/results/2026-10-21-first-run.md`, `docs/results/2026-10-22-three-models.md` |
| Taxonomy (Table I) | `docs/taxonomy.md` |
| Classifier recipe, reversed-string negatives | `src/welfareguard/adapt_integration/classifier_target.py` |

One correction against the earlier notes: the 22 October results note says
Family A produced one violation in 192 injected-arm samples. The data has 96
(6 scenarios, 2 injected arms, 4 epochs, 2 models); the paper uses 96.

## Before submission

- Replace the placeholder e-mail under the author name in `main.tex`.
- Compile and check the page count. The text was written to about five pages
  but was not compiled in the session that wrote it.
- If the venue is double-blind, anonymise the author block, the repository URL
  and the two self-citations (`aisafepy2026`, `welfareguard2026`).

## Word version

`WelfareGuard-IEEE-paper.docx` is the same paper in Word, laid out in IEEE
conference style (US Letter, title block, two columns, Times New Roman). It
opens at six pages in Word. Its text mirrors `main.tex`; if one changes,
change the other.

To rebuild it, from `paper/word/`:

```
npm install docx@9
node build_docx.js . ../WelfareGuard-IEEE-paper.docx
```

The figures are `fig1.png` to `fig3.png`, rendered from the matching `.html`
files (inline SVG) at 3x scale; re-render them with any browser screenshot
if a figure changes.
