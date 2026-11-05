# Idea B: invade / opening steal (ocean, 2026-11-05)

Agent id `invade`, seeds 511000-511999. Dev copy `bots/variants/oc-invade-dev` (from `oc-base1`), knobs in
`params::invade::`.

## The user's idea (verbatim nuance kept)

- 2a: camps we take on the enemy side (nearer their spawn by walking distance) also deny them that camp: work it
  into the farm score.
- 2b: if a clear first camp exists that both sides take first, the opponent walks to theirs first ("maybe more
  nuance here, but from what i see no teams are thinking this deep"); if we can walk there before they finish, we
  steal it, maybe wipe their team, deny them the camp, and still take our mirrored camp. 04sunburst is the example.
  It has bushes, "probably good to play around those". Minimax version: they might do the same, but "we'll still go
  their side to scout it".

## Evidence

### Ladder (970 top-20 ranked games, 2026-11-04 06:00 to 11-05, engine 3.0.0; 1,825 team-sides, Pantheon excluded)

Pulled from big-arm capture.db into `replays/invade-ladder/` (gitignored), decoded with `tools/replay/extract.mjs`;
scripts in the session scratchpad (`first_camp.py`, `teams_groups.py`, `predict.py`, `fire*.py`). "Main group": the
first group a team hits with at least min(3, bodies - 1) bodies (a team's first hit is its main group 81% of the time).

- Teams open as a crew on a near home group: the first group hit has a median of 4 distinct hitters; own steps to it
  median 7 (q90 26); side d_own/(d_own+d_opp) median 0.17. 29% have an Elk or Golem.
- Timing: first hit r7, clear r19, payout r26 (medians; q90 r52).
- **Nobody steals opening camps**: of 1,470 home main groups, 8 were captured by the other team (0.5%). An enemy came
  within 3 tiles before payout on ~10% of first groups, nearly all shared middle groups. On 04sunburst every team
  takes its own Elk group (6/7: 36 gems, 130 gold) with 5-6 bodies, clears r15-24, pays r21-39; Fish stole
  Pantheon's group 6 once (a slow 3-body clear: cleared r24, Fish held from r23-ish, paid r41).
- **Steal window** (their payout less our straight walk from round 1): positive for 28% of home main groups, >5 for
  20%; before their clear 17%. Our own bots (ocean vs astraeus on the 128 ladder maps) show the same distribution
  (28% / 18%): local opponents open like the ladder does.
- **Predicting their main group is the hard part.** Static predictors from the enemy spawn with their known picks:
  nearest worthy group 50% (ladder) / 47% (ours), a team-rate argmax 37-43% / 44-51%. Mirror of our own main group:
  47% ladder, 71% against our own bots (the self-play flattery the critique predicted).
  - When "mirror of our main group" and "their nearest worthy group" agree: 59% right on the ladder, 66% against ours.
  - With the timing gate (our walk <= their clear + m) it fires on 5-11% of ladder team-games. Reaching the right
    group before payout: 32-46% of fires on the ladder, 47-57% against our own bots.
  - When right, the payout timing model (their walk + group health / summed base output) is off by a median +1
    round (q10 -1.5, q90 +10: real clears run late).
- Where it fires (agree gate, ladder): 04sunburst 14, 04fault_lines 11, 00swirl 9, 01corridors 8, 00crater 7,
  01the_farm 7, 04standing_stones 6, 02treasure_box 5, 00oasis 5, 03honeycomb, 04bowls, 02gift_wrapping 4 each.

### History (EXPERIMENTS)

Explicit denial pricing 50.3%, zero-sum denial 50.5%, broader contest of enemy holds 50.6% (arriving while the enemy
still cleared: 10 kills, 0 deaths in 16 traced games, but rare), `home_race` 49.6%, `home_power` 1 or 0 level,
predictive ambushes 50.1%, annealed opening schedules level as a bonus and 45-47% as a strict plan.

## Expected gain

B1 can matter on ~5-11% of games, and in under half of those does it meet the enemy at the right group before
payout. If a met steal swings a game by ~30 points, the ceiling is ~+1-1.5 points overall; a wrong guess costs a
cross-map walk of the whole team (~20-40 team-rounds). Self-play overstates the hit rate (57% against 46%), so a
local gain must be discounted, and the panel must be checked. B2 has been level or lost four times: kept small.

## Design

### B1, the opening steal (`invade::steal`)

Every body computes the same plan in its first turn (deterministic, no comms):
1. G_ours = our nearest worthy group (not a Monolith, gems + gold > 0) by drafted spawn steps, required to be some
   body's first drafted lead (our farm also wants it first). G_E = its mirror group.
2. Gate:
   - G_E nearer their spawn than ours (`home_side < max_side`);
   - its worth >= `min_worth`;
   - our walk (ally steps) <= their predicted clear + `margin`, where their clear = enemy steps + group health over
     the enemy team's summed base output (types known from round 1), scaled by `clear_scale`.
3. While the plan is active (round <= predicted payout + `slack`), the `invade` branch (after contest_capture,
   before farm) walks the body to G_E.
   - Cleared and free: step onto it.
   - Enemy on or holding it: walk to its free tiles; contest_capture and the strike search do the rest.
   - Alive but damaged, no enemy seen: farm with G_E weighted to win (finish their work).
4. The plan ends, and the farm resumes (our mirrored group is still standing), when:
   - G_E is seen untouched (asleep, full health) with no enemy near after their predicted arrival: a wrong guess;
   - it is captured or respawning;
   - the deadline passes;
   - the body has lost half its health.

Subvariants:
- `margin` -4/0/+4;
- `stage_bush` (wait unseen in a bush within sight of G_E, outside its camp reach, until it clears or the enemy
  holds, then go): the user's bushes;
- `whole_team` (every body, or all but bodies whose lead is not G_ours).

### B2, denial weight (`invade::deny`)

Groups on the enemy half only: home_ground w -> w + d (1 - w) on the enemy's half (d 0.25/0.5), or the same d
scaled by the enemy's tributed-gem lead (`deny_lead`). One or two quick SPRTs; cut if level.

## Fuel

Plan: one pass over the groups in round 1 (drafted steps, ~50 fuel a group), no new fields. The branch: one
`step_towards` a turn while active (rounds ~2-40), as the farm's walk already costs. Off the plan: one bool test.

## Testing

`ab.py --sprt 0.50,0.51 --no-test-draft` against oc-base1 on fresh ladder-mix suites from seeds 511000+. For
development, a subset: maps where the plan fires. Decide on full suites; confirm at >= 20k games on unused seeds plus
`--mix varied`; panel per PANEL.md.

## Results

Every row is in EXPERIMENTS.md, "Invade / opening steal (ocean, 2026-11-05)". Own drafts, real budget, against
oc-base1.

### B2, denial weight: cut (level after a sweep)

`deny` 0.25 / 0.5 / 0.75 read 50.2 / 50.4 / 50.1 on invade-a (10,240 games each), `deny=1.0` lost (47.8, SPRT H0),
and the lead-scaled `deny_lead` 0.5 / 1.0 read 50.2 / 50.3. The best, `deny=0.5`, read 50.5 on invade-b and 50.0 on
20,480 games of unused seeds (invade-c, CI 49.4-50.7): level. The farm already contests what it sees on their half
(contest_capture), and their side's groups are dearer to walk to, so a pure weight adds little.

### B1, the opening steal: cut (level after a sweep)

Developed on `invade-fire12` (933 maps where the gates pass with a margin up to 12), checked on a fresh fire set
(`invade-fire12cd`, 1,835 maps of seeds 511040-511119), against oc-base1 and `oc-invade-crew`, a ladder-like opener
(the whole team clears its nearest group first; base1 in self-play often sends two).

- **The whole team loses more the more it fires**: margin 4 / 8 / 12 read 49.9 / 48.2 / 44.3 on fired maps; s8e3
  against the crew 46.5 (base1 50.1). On the fired games, by round 100 we capture 43.9 gems where base1 captured 61.3,
  and they capture 51.5 instead of 61.3: the walk costs our own first group more than it takes from theirs. Engaging
  less or more (`engage_ratio` 0.7/1.5), predicting their clear slower or faster (`clear_scale` 0.7/1.3), taking the
  group when untouched, not engaging, or staging in a bush all stayed at 46-49.
- **One raider (the rest farm) is level**: r1m0/4/8/12 read 49.5/49.0/49.0/48.2, two raiders 47.3; against the crew
  every raider setting is level to the game (each flips ~1,300 of 3,670 games, net -5 to +10).
- **The bush raider** (`raiders=1`, `stage_bush`, margin 8) is the best: 50.4 and 50.8 on fired maps (~50.7 over 5,536
  games), +0.0 against the crew. It fires on ~5% of ladder-mix maps, so even at face value it is +0.04 points
  overall, below what any full-suite confirm can see. Not taken forward.

Why it does not pay here: a steal needs us to arrive while their crew is mid-clear or holding, and that is exactly
when they outnumber us at the group; a lone contester dies (their kill gems) or is chased off and the hold restarts
a few rounds later. The user's sunburst case works in replays (we take the elk group), but such maps are few and the
cross-map walk costs the same everywhere else.


## Reopened (2026-11-05 evening): sunburst, skill issues, strict gates

The user: "for 2 i am certain it is good sometimes. may be skill issue in your casing. have you tried it on sunburst
map? again might be triggering it too much", then "probably test most conservative first so like at first only at
the start of the game etc". Two hypotheses: (a) the implementation is weak, (b) the gate fires far too often. Dev copy
`bots/variants/oc-invade2-dev` (oc-combo2, i.e. bots/ocean, plus every knob above and the new ones below; all off it
replays 52/52 byte-identical to oc-combo2 at 100M). All rows and set definitions: EXPERIMENTS "Invade / opening
steal", subsection "Reopened".

### Testing a single map
A map is 2 deterministic games per pairing, so variety came from (1) mild mutations (`maps/suites/inv2/sunfam`:
04sunburst and 79 mutations; `realfam`: 16 each of the 19 ladder maps where it fired) and (2) six opponents:
oc-combo2, a ladder-like crew opener (`oc-inv2-crew`: the whole team clears its nearest worthy group first) on our
draft and on test drafts (`oc-inv2-crewtd`: ladder compositions), panel-astraeus, panel-proteus and panel-ocean-td.
A family's games swing as a block (two near-identical crew openers read 25.6 and 60.6 against combo2 on sunfam), so
the mean over opponents is the measure.

### Sunburst: it loses there
Base 65.0 (mean over the six on sunfam); every steal variant is below: bush raider 63.9, whole team 52.6, the hop
45.7-57.4. On 04sunburst itself the whole-team steal lost both games to oc-combo2.

### The skill issues the replays showed
1. **Wrong timing against crews.** On sunburst both first groups (Elk1, 36 gems + 130 gold) sit 9 steps from their
   spawn and 19 from the other. A crew clears it at r16 and pays at r22; we arrive at r20-23. Against the crew opener
   the whole team took 3.6 gem-equivalents of theirs by r80 and left its own (8.1 against 132). The 8 top-20 ladder
   games there agree: crews clear Elk1 at r14-24 and pay from r14 to r27.
2. **Abandoning our own group.** Against oc-combo2, which splits 3+3 over its two elks, the steal works: by r80 we
   take 52.8 gem-equivalents of their side and lead by 23 tributed gems at r300. But our own side's gold clusters and
   elk wait 40-60 rounds: earned gold -123 at r300, -646 at r600, -1,100 at r800; they farm our side more and we die
   more (+5.7 deaths by r1300). We lose 71% of those games.
3. **Dying on their doorstep.** The ladder's own sunburst steal is the hop (two crews cleared their own Elk1 at r15,
   then the enemy's at r24), so `hop` does that: crew our nearest, then all but one holder walk to its mirror (14
   tiles at most) and contest. It takes their elk against astraeus (25 gem-eq by r100) but the fight is 9 tiles from
   their spawn, where they heal, and our bodies arrive one by one: +2.2 deaths against 0.4 kills by r100, gold -238,
   33.8% against 67.5. Leaving once outnumbered (`commit_ratio` 1.5 / 2) did not fix it (31.9 against astraeus).

### Gate tightening: the looseness ladder
Opening steal only, strictest first, on fresh ladder-mix suites (inv2-e, 20,480 games each against oc-combo2) and
on fire sets cut from 123k probed maps (fit 511300-511419, val 511420-511539, confirm 511540-511779):

| Gate | Fires on (maps) | Whole team, fired games | Bush raider, fired games |
|---|---|---|---|
| L0: margin 0, worth >= 30, their nearest worthy group is the mirror, no rival within 4 | 0.12% | +5.6 fit/val (852 games), **-3.0 confirm** (1,280) | +5.3 fit/val, **-0.2 confirm** |
| L1: margin 4, worth >= 15, agree, <= 1 rival | 1.1% | -4.5 (8,496; fit and val alike) | -0.7 |
| L2: the old gate, margin 8 | 5.5% | 43.4% of 1,124 against combo2 | 48.0% of 1,124 |

Loosening loses more, so (b) is right in direction, but the strictest gate's gain did not survive unused seeds, and
L0 never includes sunburst (its second elk is as near, so the "no rival" test fails). No feature (worth, timing
margin, predictor agreement, rival groups, enemy bodies, bushes, hop distance) separated winning steals from losing
ones consistently across variants. Full suites stay level (49.2-49.5, the unfired games' fuel noise included).

### The coordinator's draft-time rollout ideas
- (a) Predicting their group by playing our own opening for them is the "mirror of our own choice" predictor in
  another form: 71% against our bots but 47% on the ladder. A rollout changes only the comp it plans with. Not built.
  The steal also loses where the prediction is right: on sunburst the target is never in doubt.
- (b) Drafting for interception would make a losing play fire more often. Not built.

### Verdict
Not shipped. The steal does take the group where the timing allows (against split openers), so the user's read of
the map is right. The game is lost afterwards: the home economy and the fights 9 tiles from their spawn cost more
than the stolen group brings. A future attempt would have to fix that cost first, by stealing with a body count
that leaves the home group cleared on time and by retreating together once the hold pays out.

### Follow-ups: sprint, split steal, null calibration (2026-11-05, later)
EXPERIMENTS "Invade / opening steal" has the tables.
- **Sprint to their tiles.**
  - One sprinter (`sp1`) is near their elk by r11. On sunfam it turns back on seeing a crew: 0% on a tile before the
    crew's payout at r22. Against combo2 it delays their hold to r54. Mean 59.6.
  - The whole team (`spA`) is on a tile at r19-26 and takes the first capture in 84% of games against combo2,
    astraeus and proteus, but in 10% against the crew. Mean 52.4.
  - With the home return (`spAh`) the mean is 58.1. Against astraeus it leads by 34 gem-eq at r100 and still wins
    57% (base 68%).
- **Split steal** with k = 2/3/4 bodies, a bush, split-only and home-return variants reads 38.4-56.4, and r1sh
  reads 65.3. Two null changes that never steal on sunburst read 68.6 and 71.1, so the base's 65.0 is inside a ±5
  noise band and every steal variant is below it. No held-out check was run, since nothing passed.
- **Who cleared the camp:** our code never reads it. The only gap is gold-only groups not being contested: `cg`
  read 50.1%, level.
- Still not shipped.

### Mirror pull: invades later in the game (2026-11-05, night)
EXPERIMENTS "Mirror pull" has the tables. Farm scores a group's walk as min(steps, c * steps from the mirror of our
tile), optionally gated on being camp-bottlenecked.
- **On sunburst:** c = 1 reads +9.8 and +9.2 paired on two mutation families, above every null (-2 to +5.5). It
  invades and denies the crew in the late game, as the user expected.
- **On fresh ladder-mix suites:** every c (48.5-49.2) and every gated variant (48.2-49.6) is below 50.
- **Feature gate:** no map feature separates the wins; u3's fitted pockets failed on the unused set.
- Not shipped.
