# Live bench

`index.html` + `data.json`: an interactive page where anyone can run the
compiled Tier-1 guards on their own text, replay the 768 real transcripts
with the scorer's verdicts, and read the three-model results. It runs
entirely in the browser; `data.json` is regenerated from the logs and
clusters (see the export snippet in the results notes) and carries the
real compiled spans, so it must be refreshed after every new run.

## Where it is served

- **GitHub Pages**: `.github/workflows/pages.yml` publishes the whole `docs/`
  folder on every push to `main` that touches it, at
  `https://welfareguard.github.io/welfareguard/` (landing page), with the
  bench at `/bench/` and the measurement demo at `/demo/`. The workflow is
  inert until Pages is switched on in the repository settings with
  "Source: GitHub Actions"; that switch is the maintainer's.
- **Artifact copy**: the maintainer's claude.ai artifact link carries the same
  page and data for sharing before Pages is on.

## Running it locally

The page fetches `data.json`, so it must be served over HTTP; opening the
file directly shows an error that says so.

```
cd docs
python -m http.server 8000
# then http://localhost:8000/        landing page
#      http://localhost:8000/bench/  live bench
#      http://localhost:8000/demo/   measurement demo
```

## Sections have addresses

`#try`, `#replay`, `#results`, `#scenarios` and `#about` open the matching tab
directly, so a link into a specific table works. The tab bar is keyboard
operable (arrow keys, Home, End).

## Refreshing after a run

Regenerate `data.json` from the eval logs and compiled clusters, check that
`generated`, `guards`, `samples` and `scenarios` are present (the Pages
workflow refuses a file that is missing any of them), and commit it with the
run's results note. The page reads `generated` for its footer stamp.
