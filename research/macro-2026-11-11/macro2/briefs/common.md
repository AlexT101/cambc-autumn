# Common rules for macro2 implementation subagents

- Work ONLY in the git worktree /home/ubuntu/wt/macro2 (branch macro2-20261111). Never read, edit or build on
  /home/ubuntu/cambc-autumn or other /home/ubuntu/wt/* checkouts. Never touch the main branch, never push.
- Read /home/ubuntu/wt/macro2/AGENTS.md first and follow it (C++ only; comment only counterintuitive behaviour,
  concisely; `unity.cpp` includes every `.cc`, add any new one there; leave out `.cambc/` when copying a bot).
  Rules of the game: /home/ubuntu/wt/macro2/cambc-rules.yaml (engine-verified). API: docs/api/cpp.md, sdk/cpp/cambc.h.
- Never edit bots/variants/ocean-ref-b7c87cf or bots/ocean. Create/edit only your own candidate directory
  (named in your brief) under bots/variants/. Create it with `./copybot SRC variants/macro2-NAME` from the repo root
  (`-f` replaces). Keep `params::test_draft` off. Do not touch the draft (`src/draft/`, draft model, champion picks)
  or emblem selection (which emblem/shard family is chosen); everything else in play is open.
- Do NOT run A/Bs, ab.py, solo.py, fgate.py, run_batched.py or any batch of games; the lead does all testing.
  You may build and play a couple of single local games to check for crashes:
  `cd /home/ubuntu/wt/macro2 && source /home/ubuntu/venv/bin/activate && cambc build bots/variants/macro2-NAME`
  then e.g. `cambc run bots/variants/macro2-NAME bots/variants/ocean-ref-b7c87cf --map 00interlock` (stock cambc,
  debug build; check `cambc run --help` for flags such as fuel). Use a couple of maps incl. one generated map from
  /home/ubuntu/wt/macro2-maps/s-200001/ (pass the .map26a path). Check the games finish without bot errors.
  Fuel: tests run at 2x fuel (200000), so do not spend effort on fuel optimisation; just avoid pathological cost
  (e.g. no unbounded loops; prefer O(groups x small K)).
- Do not write to any Claude memory directory. Do not commit to git (the lead commits).
- When the code is done and builds, spawn ONE read-only auditor subagent (subagent_type Explore or Plan) with your
  brief and your diff (`diff -ru bots/variants/ocean-ref-b7c87cf/src bots/variants/macro2-NAME/src`), asking it to
  check the diff against the brief and look for bugs, unintended behaviour changes elsewhere, and missed cases. Fix
  what it finds that is real, rebuild, re-run a game.
- Stop condition: the candidate builds, two or three local games run to completion without crashing, the audit is
  addressed. Then report back (your final message): a summary of the design as built, the diff's files and
  functions, any constants you introduced and why (derive them from rules or measured quantities where possible),
  known limitations, and anything the lead should measure. Keep scope bounded to your brief.
