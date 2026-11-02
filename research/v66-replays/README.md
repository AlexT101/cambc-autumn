# v66 against the top 4: replay and trace analysis (2026-11-01)

Data: the 610 v66 ladder games against Intercontinental Fish, Mite, Univardisty of Shingtonwash (UoS) and
prism best girl (PBG) in `replays/v66-farm/` (412 distinct replays: rematches are byte-identical). Record 232-378.
Traces: the replay harness re-run of every game with `trace-bot-v66` (`replays/v66/`, tools/replay/harness README):
release re-runs exact against the ladder 610/610, traces exact against their recorder run 609/610, 82.6% of
rounds trusted (`ladder_trusted_through`). Trace numbers below use trusted rounds only (`scripts/trace/tlib.py`).

**Running the scripts** (from the repo root): build the extract with `node tools/replay/extract.mjs replays/v66-farm
--out replays/v66-analysis/ex` and the traces with `py tools/replay/harness/pipeline.py --version v66` (harness
README). Most `scripts/extract/*.py` and `scripts/trace/*.py` take their own folder as the first argument, e.g.
`python3 research/v66-replays/scripts/extract/ranged.py research/v66-replays/scripts/extract`; outputs go to
`replays/v66-analysis/`. `scripts/opponent/` (opponent behaviour) and `scripts/second_order/` (run `so.py cache`
first) are standalone.

Rates below use the 412 distinct games unless a trace is needed; trace rates use every traced game with its
trusted rounds. "Us" is v66, "them" the opponent. Every number has its script in `scripts/` (run from the repo
root; the extract is `replays/v66-analysis/ex`, made by `node tools/replay/extract.mjs replays/v66-farm --out
replays/v66-analysis/ex`).

## The gap

- In losses, captured gems are 555 vs 994 per game and kill gems 47 vs 178; we lose 176 carried gems to deaths,
  they 60 (`gemsrc.py`). Losers spend 18.9% of champion time dead, winners 6.8% (`macro_stats.py`).
- We die 4752 times to their 2640. We die first in 303 of 399 games (median r88) and then win 29% (57% when they
  die first); more deaths by r300 in 62% of games, which we win 21% (`first.py`). Holds on ~70 maps.
- Total champion damage is level (Fish 2.97M us vs 3.22M them, Mite 3.65M vs 3.67M), but our damage per kill is
  ~5.7k against their 2.1-3.8k. Only 26% of our damage lands on champions that die in that fight, 49% of theirs
  (`focus.py`). Focus fire itself is equal (top target takes 54% / 53%).
- Early fights (before r250) at equal numbers, or HP x Strength within 1.3x: we take 32-33% of kills against
  Fish, Mite and UoS (PBG 43-57%) (`eqfight.py`, `fights.py`). Items cannot explain this; the fights are lost
  on decisions.
- Not the cause (checked): isolation at death (35% us, 36% them); enemies getting two turns in a row (41% both);
  ambushes (we see the killer 6+ rounds before its first hit in 48% of deaths, they 39%; `warn.py`); unspent gold
  (we spend more); A-B-A position loops (3.5% us, 3.3% them); shields (absorb 7% of damage to us, 11% to them,
  21% vs UoS); allies not helping (our healthy allies hit the pursuer at least as often as theirs, `rescue.py`).

## Findings, by evidence strength

### 1. Hits on Issac are valued at zero while a lower-health Cassi is visible (bug, code-confirmed)

`hit_worth` (combat/abilities.cc) values damage on the healthier body of Cassi & Issac only once it takes that
body below its partner (`useful_damage`, model/world.h). Cassi's base health is 600 and Issac's 900, so a hit on
Issac is usually worth 0, wherever Cassi is. `attack_target` and the strike search skip it.

Trace (`trace/issac.py`), turns where Issac is the only enemy within our attack reach:

| | melee hit | ranged hit |
|---|---|---|
| Cassi visible, lower health | 30% (1275 turns) | 17% (698) |
| Cassi not visible | 96% (1402) | 61% (1145) |
| Cassi visible, higher health | 87% (148) | 53% (156) |

Example: 84d2f5aa-2 (00gemfight, vs Mite) r34-38, c0 Vesper: Issac stands adjacent at (8,9) five rounds,
Vesper's reset is ready every turn, it never fires (Cassi at (16,8), 600 < 780) and drops 665 -> 275.
Fish draft C&I in 111 of 112 games; PBG and Mite often. A hit that brings the pair nearer death through the body
we can reach is progress; valuing it needs whether the lower body is reachable by us in the fight.

### 2. Ranged champions give up shots to step back (generalises: 57 of 60 maps)

With a visible enemy within 3 at turn start, our ranged champions hit 43% of turns, theirs 65%; we move 56%,
they 33%. 80% of our moves are away from the enemy, even from distance 3. Against melee at 1-2 tiles they still
hit 68%, we 37-40% (`extract/ranged.py`). Per champion: Vesper 53/70%, Prism 44/72%, Cassi 35/60%,
Willow 28/56%.

Trace (`trace/ranged_why.py`, 33.8k turns): 78% of these non-hitting turns are `retreat` -> `retreat_step`. want_home's
reasons: low 24%, stand_lost 24%, outmatched (pack zone) 23%, willow_threat 11%, stand_falls 8%; 75% at 35%+
health. 58% of ranged retreat steps end where a seen enemy still reaches next turn (walk + attack, +2 for a ready
dash) and 93% of those fire nothing (`trace/futile.py`): retreat_step's own comment says such a step "only
delays", but for a ranged champion it also costs the shot. With the reset ready, Vesper/Willow do walk + reset +
attack (87-94%), so the loss is the reset-on-cooldown turns.

### 3. Retreats from contact fail; theirs succeed

- Retreating with an enemy within 6: we die 25%, they 10%, at every health band, though they start farther from
  home (median 30 steps vs 19) (`retreat.py`).
- Below 30% health with an enemy within 8: we die 58%, they 37% (`lowhp.py`).
- One pursuer: our retreater dies 44%, theirs 21%; their pursuer dies 3-9%, ours 21-39% (29% once 2+ of theirs
  are near) (`chase1.py`). What the retreater does is the same on both sides (dashes, shields, hits back, hits
  taken; `chase2.py`), so the difference is the state the retreat starts from.
- Trace (`trace/episode.py`): in our death episodes (back to the last turn at 80%+ health), 59% of the health
  lost comes after retreat turns. The episode starts with `stand_ok` in 40% (662 of those with no enemy in the
  fight sim yet), and the first retreat comes at a median 61% health. 85% of deaths' last turns are retreats
  (70% `low`).
- Melee pursuers walk and attack every turn, so walking away from adjacent melee only gives them free hits.

### 4. They fight together; we start fights outnumbered (opponent agent, `opponent/`)

Allies within 8 when an enemy is near: us 1.33-1.41, them 1.65-2.18; alone with an enemy near 24-25% vs 12-17%.
We start 36-46% of our fights outnumbered (they 16-25%) and lose them (Fish: our starts 236:416 kills).
Their spread before r300 is a median 11 tiles, ours 18; we take 98% of captures solo, UoS shares (1.62 a
capture) and farms our half (22-30% of its time). They win ~2/3 of contested camps on 31-50 of ~65 maps each.

### 4b. Our outnumbered fight starts come from farm's strike search with a fight sim that leaves out visible enemies

`trace/initiate.py`, `trace/initiate_vis.py`. A fight start is our hit with no cross-team hit within 12 tiles in
the previous 10 rounds; numbers are champions within 8 of the hit at the previous round's end.
- 1198 of our starts are outnumbered (attacker dies within 15 rounds 23%), 1077 even (15%), 993 ahead (12%).
- Outnumbered starts are mostly farm's strike search (`d=F`, site `plan`: 619; bank 204) with want_home
  `stand_ok` (845) and the start-tile fight sim judging the fight not lost (861).
- "Within 8" over-counts (enemies leaving or recalling are rightly left out; b8e53930-5 r127 at trace level 2),
  so the better test is who joins (`trace/initiate_join.py`): of 2451 starts whose start-tile sim was not lost,
  in 1100 more enemies dealt damage within 10 rounds and 12 tiles than the sim counted, and the attacker died
  24%; when the count matched or exceeded the joiners (1351), 3-4%. 60% of the under-counts have no enemy in the
  start-tile sim at all: the attack is chosen by farm's strike search (plan.cc, danger priced per blow at
  `hit_given_reach` 0.25 for the end tile's next turn), which asks no question about who joins over the next
  turns. Enemies missing from the sim were mostly visible (1928 visible, 443 unseen by the whole team, 131 seen
  only by an ally), so shared vision would help little (and shared sightings were tried before and lost).

### 4c. Walking off capture holds and step-on/step-off loops (second-order agent, `second_order/`)

- 2.05 hold walk-offs per game: 73% of our capture resets are the holder leaving on a want_home retreat
  (stand_lost 721, outmatched 308, stand_falls 137, low 73), healthy (median 83-92%). In 89% of stand_lost
  walk-offs our own stand sim gives the enemy more turns to kill us than the rounds left to payout (median 11
  turns vs 1-5 rounds). No enemy stood on a tile through the would-be payout in 75%. 43% repeat by the same
  champion on the same group within 30 rounds. 59 of 70 maps. Outnumbered under pressure we walk off 36%, they 20%.
- Outside holds the same flip: 26 retreat-then-back-on-the-same-tile flips a game, 84% with zero damage taken;
  sent back by farm 64%, step_safely 9%. Worst: 02the_pack (02d860db-4) r508-672, Marcella flips 61 times.
- Cause (code reading, unconfirmed by run): want_home exempts `low` while a hold lasts (`hold_lasts`) but the stand
  and `outmatched` only by `paying_soon` (no enemy can reach before payout); the step guard (combat/guard.cc)
  counts enemies whose strike reaches the tile now, want_home's stand also pursuers within `pursuit_steps`. Farm
  steps on where the guard allows, want_home leaves next turn.
- Not causes: post-first-death cascade beyond numbers (death rate per 100 alive unit-rounds even/down1/down2: us
  0.23/0.54/0.82, them 0.13/0.39/0.73: the gap is at even numbers), respawn returns, recall-trip time (29.6% vs
  27.5%), repeated death sites, tribute cancels, bag losses outside Prism.
- 73% of our deaths are on our half vs 55% of theirs; they spend 16% of off-spawn time on our half, we 8%.

### 4d. Camp damage before fights (`extract/campfight.py`)

Champions within 8 at a fight start took camp damage of 6.1% of max health (us) and 5.6% (them) in the
previous 20 rounds: symmetric. At equal numbers the side with 10%+ more camp damage loses (our kill share: 71%
when we start on camp-weakened enemies, 18% when they start on camp-weakened us), but each happens ~0.35-0.4 a
game. Farming caution is not where we differ; punishing their farming is the asymmetric opportunity.

### 4e. The fight simulator's calibration (`simcal/`, Python port `simport.py` matching 98.6-99.1% of verdicts)

Level-2 traces of 80 ladder games (r1-260) and 29 self-play games. The simulator overrates our side against the
ladder, but not through its damage arithmetic (both sides realise ~0.45 of simulated damage, symmetric; HoR's
missing-health bonus, Vendetta's reset, stuns and heals change little):
1. "Not lost" while our own champion falls in the play-out: 22% of ladder not-lost verdicts (self-play 18%, UoS
   28%); deaths within 10 rounds 20.5% vs 5.2%; about half the deaths after a not-lost verdict. want_home asks
   for our fall only when lethal or linked (`t.lost || ((lethal||linked) && t.self_falls)`).
2. Who counts: `fighting_allies` counts every visible ally within 4, but 35% of them deal nothing in 5 rounds;
   enemies count only if they strike now or walk in within `pursuit_steps`, and 0.52 outsiders a fight join.
   With an idle ally the first-death share is .41 vs .61 (Fish .22). Unflagged verdicts (no own fall, no idle
   ally, no joiner) are as reliable on the ladder as in self-play (deaths 0.6%).
3. Cassi & Issac: the sim kills the pair through Cassi; only 21% of our damage reaches her when she's weakest.
4. Everyone-hits-every-turn: real damage ~0.45 of simulated on both sides; enemies in reach hit next round 0.38
   of the time (plan.cc assumes 0.25).

### 5. Smaller, specific

- **Willow heals late.** With the heal ready and a hurt ally in range missing under half a heal, we heal 2% of
  turns, they 13-14% (`willow.py`). `heal_min_share` 0.6 (combat/self_abilities.cc) waits for 60% of a heal:
  ~124 rounds a game with the heal ready and an ally hurt. Casts: us 25 a game, them 44; healing done vs Fish
  232k us, 752k them. Our Willow dies 3.2 a game, theirs 1.3.
- **Shields.** Heart of Ruin has its shield up for 35% of champion hits it takes, theirs 48% (shield-ready
  unused: 19% vs 17%); casts 44 vs 65 a game; Varg 40 vs 90 (`shield.py`, `abil.py`).
- **Prism's bag in lost races.** In losses Prism collects 156 gems a game, tributes 8, and loses 101 to deaths
  (3.04 deaths); `retaining_gems` (economy/bank.cc) ignores the enemy's race. Example: 02the_pond
  (eb97bca3-4) r971: 443 gems, one Fish Marcella Damage cast for 1986.
- **Heart of Ruin trades worst**: 0.89 kills, 3.11 deaths a game against their HoR's 2.95 / 1.41.
- **Opponents' carries**: Fish and PBG funnel gold into Vesper (Bruiser Health/Strength, 4.1k gold a game on
  Fish's) and Marcella (Bruiser Focus): 6k-20k health, Marcella Damage casts of ~2k by r900.

## Examples (replay path under replays/v66-farm/, then rounds)

- Vesper ignoring an adjacent Issac: `20261101-002432-newer-team-vs-Mite-84d2f5aa/2-00gemfight` r33-39.
- Marcella chased to death by two melee while full-health HoR stays on spawn 6 tiles away:
  `20261031-210040-newer-team-vs-Intercontinental-Fish-d1c9c9e1/4-00gem_fields` r31-40.
- HoR at 338 dashes away, Focus-stacked UoS HoR dashes after it for 411: `...8cc4c286/1-00ribs` r556-561.
- 443-gem Prism within a walk-and-cast of Marcella: `...eb97bca3/4-02the_pond` r962-971.
