# Common rules for DELPHI (macro-o4) implementation subagents

- Work ONLY in the git worktree /home/ubuntu/wt/macro-o4 (branch macro-o4-20261111). Never read, edit or build in
  /home/ubuntu/cambc-autumn or any other /home/ubuntu/wt/* checkout (you may *execute* the fast runner binary
  /home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner, nothing else there). Never touch git (no commits,
  no branch changes): the lead commits.
- Read /home/ubuntu/wt/macro-o4/AGENTS.md first and follow it (C++ only; comment only counterintuitive behaviour,
  concisely; `unity.cpp` includes every `.cc`, add any new one there). Game rules: /home/ubuntu/wt/macro-o4/cambc-rules.yaml
  (engine-verified; read it). API: docs/api/cpp.md, sdk/cpp/cambc.h.
- Never edit bots/variants/charybdis-ref or bots/charybdis. Edit only your own candidate directory under
  bots/variants/ (named in your brief; the lead may already have created it, else create it with
  `cd /home/ubuntu/wt/macro-o4 && ./copybot SRC variants/NAME`). Keep `params::test_draft` false. Do not touch the draft
  (`src/draft/`, draft model, champion picks) or emblem/shard selection (which emblem or shard family is bought);
  everything else in play is open.
- Do NOT run A/Bs, ab.py, solo.py, fgate.py, run_batched.py or batches of games: the lead does all testing.
  Build and smoke-test with single games:
  `cd /home/ubuntu/wt/macro-o4 && source /home/ubuntu/venv/bin/activate && TMPDIR=/home/ubuntu/wt/macro-o4/replays/tmp cambc build bots/variants/NAME` (/tmp is near its quota: always set that TMPDIR and keep game output under replays/delphi-smoke/)
  then e.g. `cambc run bots/variants/NAME bots/variants/charybdis-ref --map 00interlock` (stock cambc, debug build;
  see `cambc run --help` for fuel/output flags; use 200000 fuel if there is a flag). Use two or three maps including a
  generated one from /home/ubuntu/wt/macro-o4/maps/macro-dev/ (pass the .map26a path). Check games finish without bot
  errors/crashes. Look at the stdout (debug_block traces) to confirm your new behaviour fires and does what you meant.
- Fuel: tests run at 2x fuel (200000 a turn), so do not optimise fuel; just avoid pathological cost (no unbounded
  loops or per-tile fields over all groups every turn; bound with crow-distance pre-checks; cache per round).
- Debug traces: wrap any printf in `debug_block({ ... });` (compiled out in release).
- Do not write to any Claude memory directory.
- When the code is done and builds, spawn ONE read-only auditor subagent (subagent_type "Plan" or "Explore") giving it
  your brief (the file path) and your diff (`cd /home/ubuntu/wt/macro-o4 && diff -ru bots/variants/charybdis-ref/src
  bots/variants/NAME/src`), asking it to check the diff against the brief and hunt for bugs, unintended behaviour
  changes elsewhere, broken prune bounds/memo invalidation, and missed cases. Fix what it finds that is real, rebuild,
  re-run a game.
- Stop condition: the candidate builds, two or three local games finish without crashing, your traces show the
  behaviour firing, the audit is addressed. Then report back (final message): the design as built, files and
  functions changed, constants introduced and their derivation, how often the new behaviour fired in your test
  games, known limitations, and what the lead should measure. Stay within your brief's scope.
