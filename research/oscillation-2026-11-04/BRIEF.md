# Oscillation / stuck / target-switching hunt (2026-11-04): phase 1 brief

Goal: astraeus (`bots/astraeus`, our main C++ bot) has champions that get stuck, oscillate between tiles or branches,
keep switching targets, or walk badly. Phase 1 collects and labels examples and finds their **mechanisms in our
code**. Phase 2 (later, separate agents) groups them and fixes them. Do not fix anything in phase 1.

Read first: `AGENTS.md` (repo guide), `cambc-rules.yaml` (game rules, authoritative), `bots/astraeus/src/bot.cc`
(the turn: `decide()` takes the first branch that applies).

## Data

- `bots/variants/astraeus-trace/`: astraeus plus trace hooks (diff it against `bots/astraeus/src` to see them; the
  logic is otherwise identical). It printed one `D` line per champion turn to its team's stdout.
- About 7,700 games against frozen baselines (`bots/baselines/v61,v65,v66,v67,v68,v69`), each map played from both
  sides, in `replays/batch-*-ab-osc-trace-<baseline>-<suite>/` (`results.json` gives each match's map path, side
  order and winner; file `NNN-<map>-12.repl26a` = astraeus-trace is team A, `-21` = team B).
- Detector: `tools/replay/osc_detect.py` → `replays/osc/all/` (`episodes.jsonl`, `summary.md`, `games.tsv`).
- **Your groups**: `replays/osc/all/groups/<GROUP>.md`: counts, signatures and ~20 examples each (8 longest on distinct
  maps, then random ones). `replays/osc/all/episodes.jsonl` has all of them (fields: kind, h, r0, r1, len, type,
  replay, team, branches, why, claims, prey, path, tags, goal_dist, sig, ...).

## The D line

```
D round handle branch farm claim wait_altar sx sy ex ey hp gems prey champ_atk camp_g casts
  walks fails goal_n gnx gny goal_dist gcx gcy tags fbest fmode fval fsec fsecval siege crew why
```

- `branch`: `decision` at the turn end (`Branch` in `src/bot_parts.h`): F farm, R retreat, C chase, A attack (strike
  search hit), B bank (carrying a bag to an altar), W wait at altar, T/t tribute kept/cancelled, K/k recall
  kept/cancelled, H mend on spawn, S shop trip, P hold capture, Q capture recall, G siege/kite, X contest,
  E stop game-ender, h Willow support, r Prism recovery, `-` none.
- `farm`/`claim`: `memory.farm_group` / `memory.claim` (camp-group indices, the bot's own numbering), `wait_altar`.
- `sx sy` / `ex ey`: tile at the turn start / end (-1 if dead). `hp`, `gems` (carried) at the end.
- `prey`: chase()'s target handle; `champ_atk`: champion we basic-attacked; `camp_g`: camp group we attacked; `casts`.
- `walks`/`fails`: outermost pathing calls this turn (`Pathing::step_route`, `descend_with`, `try_move`) and how many
  moved nothing. `goal_n`, `gnx gny` (goal tile nearest to us), `goal_dist` (Chebyshev, us to it), `gcx gcy` (goal
  board centroid): the **last** outermost walk call's goals. `tags`: each outermost call in order, `r` route /
  `d` descend / `m` single move, `+` moved / `-` failed (e.g. `d-r+`).
- `fbest fmode fval fsec fsecval`: when farm() chose this turn: its claim, pricing mode, value, runner-up group and
  value (`-9` = farm did not choose this turn).
- `siege`, `crew`: memory flags. `why`: comma-separated notes: `home:<reason>` = `want_home()` (combat/fight.cc)
  returned true and why (low = under recall line, outmatched, camptrap/mono = camp trapped, campfled = camps sent us
  home earlier, willow, standlost = `safety.stand()` says the stand is lost, selffalls); `leave` = decide() took the
  retreat branch; `srch:hit/nohit` = the strike search ran and did/did not attack; `mend`, `contested`, `localsup`,
  `willowstep`, `supretreat`, `joinmarc`, `yieldcap`, `handoff`, `sealed`, `wakering`, `ender`, `chase:unseen`.
- Other stdout lines (CREW PICK/JOIN/PROPOSE, MONO, RF*, REVEAL, HANDOFF, SHORTCUT, OOF, SLOT) are the bot's
  existing traces; grep the source for their printf.

Get a champion's lines: `unzip -p REPLAY team-a.stdout | grep -a "^D [0-9]* 4 "` (handle 4, team A).

## Ground truth and reruns

- Full board state: `node tools/replay/extract.mjs REPLAY --out DIR` (~1 s), then `DIR/<hash>/rounds.json.gz`
  (every champion's x, y, hp, alive, gems, chan, `sees` per round), `events.jsonl.gz` (moves, attacks, camp attacks,
  deaths, captures), `DIR/maps/<hash>.json` (walls, holes, bushes, altars, camps, groups, spawns). Schema:
  `tools/replay/README.md`. Loader: `sys.path.insert(0, 'tools/replay'); from analysis import Game`.
  Handles = engine champion ids (team A's picks first; Cassi before Issac).
- Games are deterministic. Rerun one exactly (0.4 s once compiled; the first build of a new bot dir takes ~60 s):
  `tools/fastengine/runner/fastrunner run <team A bot dir> <team B bot dir> --map <map path from results.json> -o OUTDIR --log-limit 16000000`
  e.g. `tools/fastengine/runner/fastrunner run bots/baselines/v69 bots/variants/astraeus-trace --map maps/02the-pond.map26a -o /tmp/x --log-limit 16000000`
  for a `-21` file of the `osc-trace-v69` batch. Check your rerun's D lines match the original before relying on it.
- **More logging**: copy the trace bot to your own dir, `./copybot variants/astraeus-trace variants/astraeus-trace-<you>`,
  and add `debug_block({ std::printf(...); });` where you need it (fuel is paused inside debug_block, so it barely
  changes the game; if the episode stops reproducing, say so). Never edit `bots/astraeus`, `bots/baselines`, the shared
  `bots/variants/astraeus-trace`, or `tools/`.
- The box is shared: run single games or small sets (a few at once), not batches.

## Deliverable

`research/oscillation-2026-11-04/<GROUP-LETTER>-findings.md`. For each **distinct sub-issue** you find:
1. Examples: replay path, team, handle, champion type, rounds (at least 2-3 per sub-issue, from different maps).
2. What happens on the board: enemy and camp positions, HP, gems, what the champion is trying to do.
3. **The mechanism**: the code path producing each turn's decision (file:line), and which input changes between
   the two (or more) states of the cycle so the decision flips; or why a walk fails or never starts. Go to the code and
   the numbers (add logging and rerun when needed); a plausible story is not enough. If you cannot pin it down, say
   what you ruled out and which directions remain.
4. Confidence (confirmed by trace / likely / guess) and prevalence (episodes, games, turns from the group files).
5. Fix directions (sketches, not patches) and what they could break.
Also list **false positives**: detector categories or examples that are reasonable behaviour, so phase 2 skips them.
Order sub-issues by turns wasted.
