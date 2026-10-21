# Examples: the handoff format, runnable

Two files in the exact shapes `welfareguard.clusters.load_cluster` and
`welfareguard.benchmark.load_samples` accept, so the one-command run in
`docs/runbook-baseline.md` works on a fresh checkout:

```bash
python -m welfareguard.benchmark --cluster examples/cluster.structural.json --samples examples/samples.structural.json
```

**This is structural filler, not scenario data.** The cluster's records are the
scaffold's hand-written spans (`_FAKE_PATTERN_SPANS` in `regex_guard.py`) plus
a sequence marker, which is what the test suite already uses. The samples are
the shape tests' probes with arm labels attached. No welfare scenario was
authored here, in keeping with the rule that WelfareGuard is a consumer of
`FailureRecord` clusters, not an author of them.

What it demonstrates, and nothing more:

- the cluster file format, field by field;
- the samples file format and the four arms;
- that the pipeline compiles, initialises and reports end to end;
- degraded single-tier mode, because five records is below the classifier's
  eight-positive threshold.

The numbers it prints are not results. A real cluster from the Evals track
replaces `cluster.structural.json` and its failing samples replace
`samples.structural.json`; nothing else changes.
