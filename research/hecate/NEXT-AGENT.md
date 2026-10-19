# Prompt for the next agent

Paste the block below into a new session.

```
You're continuing cleanup and fix work on the hecate bot (bots/hecate, C++), on the main branch of this repo.

Read first:
- AGENTS.md: repo rules, tools, testing.
- cambc-rules.yaml: the game rules; it overrides docs/.
- research/hecate/SIMPLIFY.md: the work list, in order, with how to test each kind of change. This is your task list.
- The newest entries at the end of research/EXPERIMENTS.md: what was just tried, with results.

Where things stand (2026-10-19):
- main has the dead-code cleanup, shared helpers, bug fixes 2.1-2.6, and the v17 farm port replaced by farm-native spell clears (`spell_clear`) and pickups (`pick_up`).
- That bot scored 54.4% against the previous main over 390 games. It isn't submitted to the ladder yet (research/SUBMISSIONS.md).
- Work-list item 1 (rare fuel gates) is half done: removing the step-guard gate added out-of-fuel turns. Start by re-testing the other four gates as SIMPLIFY.md item 1 describes.

How to work:
- For every change, copy bots/hecate to bots/variants/<name>/ (gitignored; leave out .cambc/) and change only the copy. Use another copy of the current hecate as the baseline. Never edit bots/baselines/.
- Changes that should play identically: bench before and after with `py tools/fuel/bench.py run <copy> --out X.json`; `bench.py compare` must report 16/16 identical replays.
- Behaviour changes: `py run_batched.py variants/<new> variants/<base> --threads 22`, run plain, then with --gen, then with --central (390 games; noise is ±2.5 points). Bundle fixes that are clearly correct into one run, to save time. Test judgement calls alone. Keep a fix if it wins; keep a removal if it's level.
- When fuel gates change, also run `bench.py run <copy> --fuel 0` and compare out-of-fuel turns against the baseline (8 at ed3b2ac).
- If a result is unclear: `node tools/replay/extract.mjs replays/<batches>`, then `py tools/replay/ab_compare.py <variant name> <batches>`.
- To keep a change, copy it into bots/hecate. Record the result in research/EXPERIMENTS.md, remove the item from SIMPLIFY.md, extend research/hecate/CHANGES.md item 14, and commit on main. Ask the user before pushing.

Pitfalls:
- The source files have CRLF line endings.
- Small helper functions can cost fuel in the WASM build (one cost ~80 fuel a turn), so bench even refactors.
- The bot code has very few comments: keep it that way (AGENTS.md).
- Another agent may be investigating the fuel-gate questions; the open one is at the end of SIMPLIFY.md.
```
