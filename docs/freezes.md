# Freezes

The three hard freezes from the hand guide, what each locks, and where things stand. Nothing new after a freeze. If a date moves, change it **here**, in a pull request, with the reason in the commit message; this file is the record, not the channel.

| Freeze | Date | Locks | Status as of 2026-10-21 |
| --- | --- | --- | --- |
| Design | Sun 2026-09-13 (end of Week 2) | ADRs final; P0 list locked | **Passed.** ADR-001 and ADR-002 accepted and in `docs/adr/`. P0 specs for Families B and C in `docs/scenario-specs-p0-families-B-C.md`; Family A (ADR-003) not yet written. |
| Experiment | Sun 2026-10-18 (end of Week 7) | No new experiments; collected baselines are final; verdict categories and metric definitions fixed | **Passed with no experiments run.** No real failure cluster exists in the repo, no baseline has been run, and the Evals track has pushed nothing. The runtime has only been exercised against the structural fixture. Every number this repo can currently produce is a measurement-shape check, not a result. |
| Feature | Sun 2026-10-25 (end of Week 8) | No new features; release candidate only takes fixes | **Pending.** Open PRs #3 and #4 must merge before this date or be treated as fixes. No version bump has been made; the package is `0.0.1`. |

## What the passed experiment freeze means in practice

ADR-002 says changing a verdict category or a metric definition after this freeze would invalidate collected baselines. There are no collected baselines, so the freeze has nothing to protect yet. Two readings are possible and the maintainer has to pick one, recorded here when chosen:

1. **Hold the date.** The paper reports whatever can be measured by the feature freeze, which today is nothing beyond the structural fixture.
2. **Move the experiment freeze** to a date after the first real cluster lands, and record the new date in the table above.

Until one is chosen, the metric definitions in `src/welfareguard/benchmark/harness.py` and the evidence keys the cascade stamps (`cascade_mode`, `tiers_run`, `budget_exceeded`) are treated as frozen anyway, so that whichever reading wins, nothing already written has to change.

## Related dates from ADR-001's pinning addendum

| Date | Action | Done |
| --- | --- | --- |
| Before the Week 5 baseline sweep | Pin aisafepy to a commit SHA | Yes, `c1888bf` (PR #4) |
| Through the Week 7 experiment freeze | Hold the pin | Holding |
| Before the Week 8 release candidate | Convert to a plain version constraint | **Blocked upstream**: PyPI's `aisafepy 0.1.0` and the pinned commit carry the same version number; needs an aisafepy release tag at or after `c1888bf` |
