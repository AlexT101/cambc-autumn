# Retreat audit (ocean, 2026-11-09)

How ocean dies while retreating, and whether five retreat ideas have room: a dash route that loses a
non-dashing pursuer, hiding in bushes, leaning toward allies, longer or fire-crossing routes, and waking a camp
behind us. Nothing shipped; this is the feasibility evidence.

## Data

Debug builds, fast runner, the 128 ladder maps both sides: ocean mirror (`replays/retreat-mirror`, 128 distinct
games: the two sides are byte-identical) and ocean vs astraeus (`replays/retreat-astr`, 256). Extracted to
`replays/retreat-analysis`. 512 ocean team-games: 3,463 deaths to champions (6.8 a team-game), 149 to camps.

```
python3 tools/retreat_audit.py replays/retreat-analysis eps.jsonl --procs 16   # one row per retreat episode
python3 tools/summ.py eps.jsonl                                                  # the tables below
python3 tools/show.py eps.jsonl SEED          # ASCII of three random avoidable deaths
python3 tools/turns.py REPLAY CHAMP R0 R1     # per-turn table: decisions, positions, hits
python3 tools/dash_spend.py eps.jsonl         # what spent the dash before a retreat death
```

**Episode:** a run of `R` decisions (D lines; gaps up to 2 rounds) whose first turn has a visible enemy within 8.
The window runs to the episode's end + 3, death, or spawn. 33,470 episodes; 2,197 end in a death to champions:
**63% of all deaths to champions come in or within 3 rounds of a retreat.**

**Pursuit model** (worst case, terrain only): the enemies visible at r0 move optimally and dash once when ready.
A melee one hits if our tile after our turn k is within 1 of a tile it reaches in k turns. A ranged one hits if
we are within 3 of a tile it reaches in k-1 turns, since a ranged walk spends the attack. Our spawn ends exposure.
A DP over turns gives the least exposure, under two constraints: the same K turns, and ending at least as close
to home as ocean did (`opt_*['act']`). It is solved walking only, with our dash as its cooldown was, and with
the dash ready (`opt_dash_ready`). The model ignores body blocking, range-4/5 spells, reset shots, enemies who
join later and turn order. Its exposure tracks real damage (mean taken 59 / 93 / 119 / 212 / 432 hp by exposure
bucket 0 / ≤2 / ≤5 / ≤10 / more), but death rate only weakly (5.0% → 9.4%). 13% of retreat deaths have zero
model exposure on ocean's own path.

## Findings

| Idea | Precondition in retreat deaths (of 2,197) | Verdict |
|---|---|---|
| Route choice (longer / safer path, fire then safe) | Zero-exposure walk at ocean's progress while ocean was exposed: 582 (26.5%); 297 of the 1,135 never stunned (26.2%). Walk optimum ≤ half ocean's exposure: 36%. 49% of deaths start with every visible enemy 4+ away. | Largest pool. The model is optimistic, so the real ceiling is lower. |
| Dash shortcut vs non-dashers | Dasher victims 1,026 (47%). Only 181 faced non-dashers alone; a dash-only escape in 23 (1%). Over all deaths, dash-only escapes 103 (4.7%). | Small as a standalone rule. Free inside a route planner. |
| Dash kept for the escape | 733 of 1,026 dasher deaths start with the dash cooling. A ready dash gives a zero-exposure escape in 422, 230 of them beyond what the actual cooldown allows. Of those 230: dash cast 1 round before r0 in 143; same turn hit an enemy champion in ~half; ~95 hit nothing (F 62, C 14, R 11, B 5). | Real pool. The no-hit dashes are mostly strike-search positioning, not travel: `travel_dash` already withholds within 10 of an enemy. |
| Escape dash ready but unused | Ready on some unstunned turn in 731 dasher deaths; never cast before death in 86. | Small. The landing choice matters more than casting. |
| Hidden bushes | Hidden bush adjacent on some window turn: 35% of deaths, 42% of exposed survivals. When one was adjacent, ocean stood in a bush 77% of the time. | Already in place (bt3, and Safety's attack viewers drop hidden bush tiles). Enemy forgetting can't be modelled. Hiding where a melee pursuer can enter the cluster is a trap. |
| Lean toward allies | Ally within 4 at r0: 62% of deaths, 71% of exposed survivals; within 8: 79% vs 86%. | Weak, and confounded. Earlier cohesion leans lost or were level (EXPERIMENTS "Cohesion"). Tie-break at most. |
| Wake a camp behind us | Sleeping member in our attack range, with a pursuer in its range and nearer to it than us, on some window turn: 101 deaths (4.6%), 465 exposed survivals. | Rare, and worth only 20-120 hp a camp phase. Not worth its code. |

**Example of the route failure** (`retreat-astr/141-03homonoliths-12`, our Vesper, r538-545): a full-health Vesper
retreats from a better-itemised enemy Vesper (203 a hit against 140). The shortest way home runs south along a
corridor toward it; the safe way runs north-west around a wall line. The champion flips between the first steps of
the two routes, (13,15) and (14,14), for seven turns. Home distance goes 33 → 35, the dash is ready from r542 and
never cast, and it dies at r545. `retreat_step` ranks one step by next-turn damage; a sideways or longer step wins
only on damage, so no route is ever committed to. `escape_landings` takes only landings with less one-turn danger
than here, which a ranged dashing pursuer's reach rarely allows.

The combat lab's one-step arms found nothing that beats ocean's retreat step (analyst-findings §3). That is
consistent with this: a committed route is a multi-turn plan, which a one-turn deviation followed by ocean's own
policy can't express (§6, "multi-turn plans").

## Integrated design, if built

One escape planner in `model/` that replaces `retreat_step`'s ranking beyond the first turn and
`escape_landings`' choice:

- **Input:** our walk and dash (its ready turn), the credible enemies' reachable sets turn by turn (visible ones from
  their tiles, unseen ones from `possible`), and each enemy's strike reach (basic, plus ready spells for its first
  turn).
- **Search:** time-expanded reachability on a local window around us, bit-parallel rows as Safety's `Window` code
  does, layered by hits taken (0-2) and by whether the dash is spent. A tile in a bush cluster is safe from ranged
  enemies outside it until they could enter it.
- **Output:** per first move (8 walks × dash landings), the least hits to the goal and the turn it arrives. The goal
  is the spawn, or ending out of every pursuer's reach by the horizon, with ally proximity only as a tie-break.
- **Turn 1** keeps Safety's exact pricing. The plan prices only turns 2+.
- **Fuel:** ~10-30k a retreat turn on a ~21×21 window, horizon ~8; whole-board host ops would be ~1.6k fuel a
  dilation on 100×100. Make it anytime on the fuel left.

That covers the dash shortcut, the detour, fire-then-safe and bushes in one model. Its with-dash versus
without-dash value is also the price the strike search could charge for spending the dash.

**Test:** `retreat_audit.py` on a 256-game debug batch should show lower `act` exposure and fewer route flips. Then
an A/B (10k+ games), with deaths from `tools/replay/fight_metrics.py`.

## As built (CHANGES 478)

`bots/ocean/src/model/escape.{h,cc}`, used by `retreat_step` (combat/fight.cc) and `escape_landings`
(combat/self_abilities.cc). Differences from the design above:
- **Window and horizon:** radius 7 (15×15), horizon 5, as SIMD bit rows. Pursuers just outside the window enter at its
  edge, delayed by their distance (less a ready dash).
- **Pursuer model:** pursuer classes merged by reach, dash turn and burst (a hitting spell's one-turn reach on its first
  two ready turns; ground casts and landings ignore bushes). Unseen enemies come from their possible tiles.
- **Ranking:** hits counted 0, 1 or many. The full goal is `horizon` steps nearer home, the slack goal 3 steps short of
  that and worked out only when the full goal has no clean way. A hit weighs 4 steps of progress. This turn's hit
  comes from Safety, counted twice when it is a third of our health or more.
- **Ally proximity was not built.** The camp stall was not built either: live camps are terrain only.

**Result:** at unlimited fuel, 53.1% local and dgate ACCEPT at +2.2 points. At normal fuel the first version read
33.9% (fuel), and the same plans at a quarter of the fuel read about 51.6%. Deaths barely move; gems rise ~4%.
Numbers in EXPERIMENTS "Escape planner fuel".

## After 478

Three follow-ups (EXPERIMENTS "Escape planner after 478"):
- [fuel-opt.md](fuel-opt.md): an exact build 5.6% cheaper, merged as CHANGES 480.
- [logic-audit.md](logic-audit.md): the plan's hits against the games, and four model fixes, all level or below.
- [fuel-gate.md](fuel-gate.md): the out-of-fuel hazard by caller, and per-caller reserves, which read level.
