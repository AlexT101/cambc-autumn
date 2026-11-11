# Common brief for idea agents (ocean, 2026-11-05)

Read `research/ideas-2026-11-05/USER-IDEAS.md` (the user's ideas, verbatim: keep their nuance), AGENTS.md, cambc-rules.yaml and tools/README.md first.

## Rules
- Prefix every Bash command with `source /home/ubuntu/venv/bin/activate;`.
- Don't commit. Never edit bots/baselines.
- ssh big-arm is read-only and light: it has 2 cores and serves the live arena. Small rsyncs of replay files are fine; no batches there.
- Never run `tools/mapgen/mapgen.mjs suite` without `--out`. New suites go in `maps/suites/fresh/fresh-<seed>`. Symlink merge dirs go in `maps/suites/merged/<name>`, with links `../../fresh/fresh-<seed>/<file>`. Use only your own seed range. `tools/run_batched.py --output` must be inside the repo.
- Fast runner always: `CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native`.
- Both bots play their own drafts: `--no-test-draft`.
- The box is shared: run at most one ab.py at a time per agent. ab.py shares slots fairly.

## Base
- `bots/variants/oc-base1` is ocean (astraeus, the draft5 draft, and farm R1+F1 merged). It is ready when `bots/variants/oc-base1/READY` exists. Research and design while you wait.
- If `bots/variants/oc-base2` appears (base1 plus SPSA constants), confirm your final winner on it too.

## Method
1. **Think first.** Write `research/ideas-2026-11-05/<id>.md` before coding: evidence (rules, our replays, ladder archive or replays), the design, knobs, a fuel estimate, the subvariant grid, and the expected gain with the maps where it applies.
   - The ladder archive is local: `replays/ladder-archive/<day>/data/*.npy` plus `meta.json`, with per-game, per-side and per-unit summaries.
   - Full ladder replays come from big-arm capture.db: see the memory note `big-arm-capture.md` in ~/.claude-osteo/projects/-home-ubuntu-cambc-autumn/memory/. Pull small samples.
   - Our own replays: run games with ab.py and inspect them with tools/replay/.
   - Map view: `node tools/mapgen/mapgen.mjs show FILE`.
2. **Self-play flatters exploits.** Our mirror opponent shares our blind spots and habits. Any assumption about how enemies behave needs ladder evidence. A final winner must also not lose to the opponent panel in `research/ideas-2026-11-05/PANEL.md` (being chosen now; until it exists, use `bots/astraeus` and `bots/archives/proteus`), following its rule: no significant loss to any member, and a gain on average.
3. **Develop in a dev copy.** Use `./copybot variants/oc-base1 variants/oc-<id>-dev` and guard each idea with `params::<id>::` knobs. With every knob off, `tools/fuel/bench.py` replays at 100M fuel must be byte-identical to oc-base1's. Make subvariant copies with knob settings; constant sweeps are expected.
4. **No new fuel gates** (code that chooses worse when fuel is short). Develop at `ab.py --fuel 10000000` to see the ceiling if fuel muddies the signal, but decide at the real budget. If out-of-fuel turns rise materially, make the work cheaper. Report fuel with bench.py (mean, p99, OOF).
5. **Testing.**
   - Use `ab.py --sprt 0.50,0.51` (it pairs a map's two sides), or chunks of 5,120 games with early stop (min 2 chunks, max 6), on fresh ladder-mix suites from your seed range.
   - Map subsets (filter `index.json` metrics into a symlink dir) are for development only. Keep decisions are made on full ladder-mix suites.
   - Confirm the chosen setting on unused seeds, at ≥20k games, plus a `--mix varied` check.
   - Combine only confirmed winners, as a full factorial over ≤4 knobs.
6. **Record** every row, losers included, in research/EXPERIMENTS.md in one section per idea titled "<idea> (ocean, 2026-11-05)", and keep the design doc updated.
7. **Final report** (concise):
   - the confirmed winning knob settings;
   - win rate and CI against oc-base1 on the confirm seeds, the varied-mix result, and the panel results;
   - fuel;
   - the dev variant path and the files and functions touched;
   - what lost.

## Adapt the plan
The user says: "depending on what happens you may choose to dynamically change the plan ofc. like more subvariants if looking promising etc".
- Treat your grid as a starting point.
- When a direction looks promising, spend more: add subvariants, refine constants, try sub-ideas.
- When a direction reads level or losing, sweep its constants (thresholds, weights, margins) before cutting it. An idea at the wrong setting can look dead. The user: "when this happens maybe refine constants asw lol". Cut it only after a reasonable constant sweep stays level or losing.
- Record why you changed course.

## Resources
The box has 185G RAM and no swap; 192G disk is free.
- At most ~30k maps per mapgen command.
- One ab.py per agent.
- Run `free -g` before anything big, and keep at least 20G available.
- Delete scratch replays you don't need (replays/ab summaries are small).
