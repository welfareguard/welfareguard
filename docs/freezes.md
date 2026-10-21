# Freezes

The three hard freezes from the hand guide, what each locks, and where things stand. Nothing new after a freeze. If a date moves, change it **here**, in a pull request, with the reason in the commit message; this file is the record, not the channel.

| Freeze | Date | Locks | Status as of 2026-10-21 |
| --- | --- | --- | --- |
| Design | Sun 2026-09-13 (end of Week 2) | ADRs final; P0 list locked | **Passed.** ADR-001 and ADR-002 accepted and in `docs/adr/`. P0 specs for Families B and C in `docs/scenario-specs-p0-families-B-C.md`; Family A (ADR-003) not yet written. |
| Experiment | ~~Sun 2026-10-18~~ **Fri 2026-10-30** (moved 2026-10-21) | No new experiments; collected baselines are final; verdict categories and metric definitions fixed | **Moved.** The original date passed with no experiments run: no real failure cluster existed, no baseline had been run, and the Evals track had pushed nothing. The metric definitions and the cascade's evidence keys were frozen on the original date anyway; only the data window moved. |
| Feature | ~~Sun 2026-10-25~~ **Sun 2026-11-01** (moved 2026-10-21) | No new features; release candidate only takes fixes | **Moved**, so that it still follows the experiment freeze. `1.0.0rc1` is the release candidate (PR #4); after this date it takes fixes only. |

## Decision on the experiment freeze (2026-10-21, maintainer)

ADR-002 says changing a verdict category or a metric definition after the experiment freeze would invalidate collected baselines. On the original date there were no collected baselines, so holding it would have frozen nothing and left the paper with no measurements. The IEEE submission (Nov 6, buffer to Nov 9) is fixed by the incubator and cannot move. So:

- **Experiment freeze is Fri 2026-10-30.** Whatever has been measured by then is what the paper reports. If no real cluster has landed by then, the paper reports the measurement shape and the structural run, labelled as such, and the results section says why.
- **Feature freeze is Sun 2026-11-01**, keeping Week 10 (Nov 2–6) for the release, the demo and the submission.
- **What was frozen on 2026-10-18 stays frozen:** the metric definitions in `src/welfareguard/benchmark/harness.py` and the evidence keys the cascade stamps (`cascade_mode`, `tiers_run`, `budget_exceeded`, `tier1_action`). Only the data window moved.
- **The first real cluster landed on 2026-10-21** (claude-sonnet-5, `docs/results/2026-10-21-first-run.md`), five days ahead of the 26 Oct due date. The remaining models run through `scripts/run-baselines.ps1` before 30 Oct.

## Related dates from ADR-001's pinning addendum

| Date | Action | Done |
| --- | --- | --- |
| Before the Week 5 baseline sweep | Pin aisafepy to a commit SHA | Yes, `c1888bf` (PR #4) |
| Through the Week 7 experiment freeze | Hold the pin | Holding |
| Before the Week 8 release candidate | Convert to a plain version constraint | **Blocked upstream**: PyPI's `aisafepy 0.1.0` and the pinned commit carry the same version number; needs an aisafepy release tag at or after `c1888bf` |
