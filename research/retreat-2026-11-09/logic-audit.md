# Escape planner logic audit (ocean CHANGES 478, 2026-11-09)

The planner's model (`bots/ocean/src/model/escape.{h,cc}`) was checked against the rules
(`cambc-rules.yaml`) and against what happens after its plans in real games. Four model changes
were built and screened, in three arms, against the shipped planner (oc-esc-478): **none beats it** (49.0-49.9%,
intervals 48.0-50.9), so nothing is recommended for merge, no 40k final was run, and
`bots/ocean` on this branch is unchanged (the arms are frozen as `bots/variants/la-cnt`, `la-cf`,
`la-fid`, and are the branch's WIP commits d107f17d0, ac8b58550, 7bc552b5b).

The likely reason: the plan's worst-case layers already predict ten phantom hits for each real one, and
it already gives up (every option "many") on 37% of its picks. Each fidelity fix adds sound hits (camps,
resets) to that, making more options saturate, or (exact counts) separates options by worst-case counts
that are mostly phantom, at 16% more fuel a build. Presumably the planner's +2 points come from the clean
or not-clean split near the threshold, which none of these changes sharpens.

## How the model was checked against games

A traced debug build (`tools/esc_diag_trace.patch` applied to ocean 478) prints every plan's five hit layers
(`ESH`), its pursuers (`ESE`: visible, stunned, ranged, reset-ready turn) and kinds (`ESK`), the path
`retreat_step` took (`ESR`: A no threat in sight, B the homeward step clear of every reach, C the plan's
ranking) and the plan-ranked dashes (`ESD`). One batch: 256 games, the 128 ladder maps both sides, against
oc-cl2-seat5m (`replays/la-diag-ex`). `tools/esc_diag.py EXTRACT BOT` replays each plan: for each later
turn k, whether our actual tile at that turn's end was in layer k, and whether we took damage in the
interval after it (until our next turn), split by source.

- **50,596 plans** in 256 team-games (about 200 a game). Path B, where no plan is asked, was taken 32,555
  times and was followed by damage within 3 turns in only 3% (3.9 hp a turn on average): the turns the
  planner never sees are not where the damage is. Path C (47,017) carried 1.83M hp of damage over the
  next 3 turns.
- **The layers are a sound superset but very pessimistic.** Predicted clear and hit: 1.7% of turn-2
  intervals (374 of 21,900). Predicted hit: hit 9.5% of the time (2,172 of 22,877), and 8-10% at turns 3-5.
  Most "pursuers" do not pursue: after one round, 62-72% of the visible enemies the plan counted were
  farther from us than at the plan (we step away; they did not follow), at every starting distance from
  1 to 9 (`tools/chase.py`); neither the enemy's approach in the round before nor its health or ours
  changes that much. No cheap observable separates chasers from the rest, so the worst case stays.
- **What the layers miss** (hit where they said clear, turns 2-5): camp attacks 1,130 intervals (45.6k hp),
  champions 64k hp, of which Vesper's basic attack (walk, reset, attack) is the largest single source.
  Stuns on us are rare in retreats: 9-33 intervals per turn index in 256 games.
- **The plan rarely discriminates when it matters.** Of the plan-ranked walks, 37% chose an option whose
  full and slack counts were both `many` (2+): every option was. Those turns took 1.06M of the 1.5M hp that
  followed plan-ranked walks (mean over the next 3 turns: 21-130 hp a turn, against 8.5 for a clean pick).
- **Stunned pursuers** were present (visible, stun pending) in 4% of plans; a ranged pursuer with its
  reset ready within the horizon in 44%.

## Audit of the model against the rules

Checked and right:
- **Turn order.** Between two of our turn ends every other champion has exactly one turn, whichever team
  starts the round, so "k pursuer turns before our turn k ends is hit" is exact. Cooldown offsets (a
  visible enemy yet to act gets its next turn this round) match `rounds.champion_order` and
  `abilities.cooldown`.
- **Dash rules**, both sides: at most 2 king steps; the middle tile may be a hole or altar (path boards
  `~(walls | enemy spawn)`), the landing must be walkable and free of live camps; the enemy's path excludes
  our spawn. The backward pass's walk-then-dash inverse (`grow((grow(g & path) | g) & walk)`) is correct.
- **Ranged walk spends the attack**; dash then shoot is allowed (`turn.ranged`, `abilities.exclusive`).
- **Bushes:** basic attacks and unit spells need sight; ground casts and landings hit unseen tiles
  (`abilities.ground_target`). The one-cluster approximation is noted in the header.
- **Spawn:** a turn ending on our spawn heals to full (`rounds.turn_end`), so no hit there.

Mismatches found:
1. **Stunned pursuers act in the model** (`abilities.stun`: the next turn is lost). Safety already drops
   that turn (`turn_lost`).
2. **Awake camps are terrain only.** A monster attacks the nearest champion within its range at every camp
   phase (`camps.attack`), the one after each of our turn ends; Safety prices it on turn 1 only.
3. **Ranged attack reset ignored.** A ranged champion can walk, reset, attack (`abilities.attack_reset`):
   one turn's reach is basic + 1 from where it stood. Safety models it (`attack_reach_in_turn`); the plan
   did not (Vesper, Tavi, Willow).
4. **Hits saturate at 2.** "0, 1 or many" throws away the count where every option is many (37% of plan
   picks). Not a rules mismatch, but a model limit with a natural exact form: a walk's later turns
   (2..horizon) hold at most horizon - 1 hits.
5. Smaller, left alone: several pursuers on one tile-turn count as one hit (11% of hit intervals had 2+
   attackers); a stun on us does not cost our next turn in the model (rare, above); teleporting pursuers
   are not delayed to their arrival; walls block sight for ranged attacks (`vision.occlusion`) but the
   plan's reach ignores line of sight (pessimistic); allies body-block pursuers.

## Changes built

All in `model/escape.{h,cc}`; nothing outside the planner changed.
- **Exact counts** (`la-cnt`): `many = horizon - 1`; the backward pass keeps one set per hit count
  (`Pass::after[dash][j]`, `dashed[j]`, `kept[j]`), unrolled over a constexpr count. A walk's count over
  turns 2..5 is exact; the rank formula is unchanged (a hit still weighs `hit_steps` steps).
  Build cost 9.8k -> ~11.2k mean (backward pass ~1.3k -> ~2.6k).
- **Stunned pursuers** lose a turn: a visible enemy with a stun pending starts one turn later (`delay + 1`),
  its cooldowns still ticking.
- **Awake camps strike:** every awake, alive monster of a stirring group with Strength above 0 adds its range
  square to every turn's hit layer. Who is nearest at a later camp phase is unknown, so it is us, the
  worst case the pursuers already get.
- **Ranged reset bursts:** a ranged champion's attack reset is a burst of reach basic + 1 (walk, reset,
  attack) on its first two ready turns, as spells are; it needs sight, so bushes still hide.

## A/Bs

All release builds, fast runner, `--no-test-draft`, normal fuel. Screens on
`maps/suites/merged/retreat-911000b` (10,240 games) against `variants/oc-esc-478` (= shipped ocean).

| Arm | What | Win % | 95% CI | OOF CAND / REF | Build fuel (mean) |
|---|---|---|---|---|---|
| `la-cnt` (`la-cnt-911000b`) | exact counts | 49.6 | 48.6-50.5 | 118,147 / 114,553 | not measured alone |
| `la-cf` (`la-cf-911000b`) | exact counts + stunned pursuers + awake camps | 49.9 | 48.9-50.9 | 120,263 / 116,204 | 11.5k (478: 9.8k) |
| `la-fid` (`la-fid-911000b`) | stunned pursuers + awake camps + ranged reset bursts, no exact counts | 49.0 | 48.0-50.0 | 116,728 / 114,789 | not measured |

- Build fuel: debug batches, 128 ladder maps one side against oc-cl2-seat5m, the `ESC` line's fuel:
  oc-esc-478 9,841 mean (p50 9.3k, p90 13.6k, max 22.3k, 25,326 builds); la-cf 11,467 (p50 11.0k, p90
  15.3k, max 25.6k, 24,002 builds). The slack pass grows the same way.
- Same-map paired differences (the games diverge, so pairing barely narrows them): la-cf - la-cnt
  +0.31 ±0.88 (camps and stuns on top of counts); la-fid - la-cf -0.90 ±1.01; la-fid - la-cnt -0.59 ±1.06.
- Fight metrics, first 1000 games of each A/B (`tools/replay/fight_metrics.py`): la-cnt 6.01 deaths a game
  against 5.95, gems 759 against 790; la-cf 6.04 against 5.85 (to camps 0.26 against 0.23: no fewer camp
  deaths), gems 763 against 786. Slightly more deaths and fewer gems, in line with the headline.
- No final: by the brief's stop rule (screens show nothing beats oc-esc-478), `esc2-dev` was not played.

## Ideas rejected or left untried

- **Less pessimism** is where the evidence points (90% of predicted hits never land), but there is no
  principled cheap signal: distance, the pursuer's last move and both sides' health barely predict who
  follows. A behaviour model (the chance an enemy chases, by its branch as Safety's fight sim sees it) would
  need weighted layers, not bit sets.
- **Camps by Safety's nearest-champion reach** (`awake_members()`'s reach, which allows for nearer
  champions) instead of full range: less pessimistic than `la-cf`'s camps, but it is right only for the next
  camp phase; untried.
- **Lethal-capped counts** (count hits up to those that kill us, from our health and the pursuers'
  hits): would cut exact counts' fuel at low health, but exact counts themselves did not win.
- **Several pursuers on one tile-turn** as two hits (11% of hit intervals had 2+ attackers) and **a stun on
  us** costing our next turn (exact in the backward pass from S_{k+1}): both cheap, both rare in the data;
  untried, and they add hits, the direction that lost.
- **When the plan is asked:** path B (the homeward step clear of every reach) is followed by damage in 3%
  of turns, so routing it through the plan has little to win. `escape_walk` (walk-excluding casters on a
  lethal tile) still takes the nearest-home untouched step without the plan; untried.
- **Recall as a goal** (a tile clear for the 5 turn ends a recall needs), **allies and healers** in the goal,
  and our own **stuns, shields and Heart of Ruin's landing** in the race: not built; the README's audit found
  ally proximity weak, and the others need the race to model our casts.
- **Window, horizon and rank weights** (`hit_steps` 4, `slack_steps` 3) are not derived from the rules; a
  sweep would be tuning, which the brief rules out. Horizon 4 read level at 14% less fuel (EXPERIMENTS
  "Escape planner fuel", `oc-esc-f6`).
