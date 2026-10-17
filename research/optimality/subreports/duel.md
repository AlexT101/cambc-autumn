# Exact 1v1 solver: kiting, first strike, duels, casting, escape, target order (duel subagent; saved by the main investigator)

Code and tables in this folder: duel.cpp (binary duel7.exe, C++ via zig), spec.py (independent Python rules spec), checks
(verify2d.py, chk_kill.py, chk_reward.py, chk_safe.py, rules_check.py), runners (run_all.py, run_dbl_subset.py), analyze.py,
summarize.py, q6.py, results/, tables/ (q1_kiting, q2_first_strike, q2_standoff, q3_full, q3_full_patterns, q3_brawl,
q4_greedy, q4_examples, q5_escape, q6_*.tsv), pv/ (traced optimal fights).

## Model
Open ground, full information, 0 shards, full HP, abilities ready unless stated; Cassi and Issac as separate bodies.
Rules: one king step; basic attack Strength (melee 1, ranged 3); melee walk/attack independent; ranged walk or attack spends
both; one successful cast per turn; excludes-walking spells not after a walk and no walk after (an attack is not a walk);
reset needs a spent attack and restores only it (melee A,R,A + walk; ranged A,R,A or W,R,A); Marcella's reset stuns with the
next attack; dash lands at any d' in [max(1,d-2), d+2]; unit spells reach 4, ground hits iff d <= 5; cooldown 8 own turns,
ticking at own turn ends incl. stunned turns; stun removes the target's next turn (Marcella immune); Varg shield 250 until the
start of his 5th turn after casting; Ren reflects 20 per damage instance even while dying; HP exact (×4 integers); vision 8
(a turn ending at d >= 9 disengages).
Theorem 0 (turn order): ranks by priority then id; k < j we act first every round, k > j they do, k = j double moves. A
shield covers 5 enemy turns in alternation; under double moves 6 if cast on the second turn of Varg's pair, 4 on the first.
Theorem 1 (distance suffices): a walk reaches exactly {d-1, d, d+1} (never 0), a dash exactly [max(1,d-2), d+2]; verified by a
2D tile-level solver (0/1,536 mismatches). Lemma 2 (pruning) verified on/off identical.
Kill game solved without horizon by induction on HP levels (plus turns-to-kill as a second exact game); free/forced-damage games
by value iteration with ∞ detection.
Checks (all 0 mismatches): per-turn outcome sets C++ vs Python (144 pairs × d 1..10 × 4 readiness combos); 2D vs 1D (1,536);
finite-horizon values vs Python minimax (144 + 48); forced damage vs Python (768) and never-hit sets (112). Horizon 400 vs
no-horizon: 143/144 (the exception is a parity-alternating standoff; 0 is correct).

## Q1 kiting (ranged A never takes damage)
Sustained (∞) free damage exists iff A has a recurring damage action that costs no distance (reset, dash or stun) and the melee
B has no reach-4+ tool. That leaves Varg as the only kitable melee: per 8 own turns Tavi 177, Cassi 114, Prism 94, Vesper 55,
Willow 27; Stellar (no reset/dash/stun) is capped at 575 total. Against Ryth, Ren, Vendetta, Issac, Marcella: no sustained
kiting; only opening pokes (Stellar 140 / Prism 80 vs Marcella from d = 5; Vesper 45 at d = 3 vs Vendetta, Marcella, Issac). A
double move gives the kiter one extra free shot and costs it one tile of safety when the chaser has it; it breaks Prism's endless
kite of Tavi and Willow. Tempo accounting (alternation, Φ = distance at the start of the chaser's turn; plain melee hits iff
Φ <= 2): walk away 0; shoot or exclusive cast without walking -1; shoot + cast -1 for two hits; walk + reset + shoot 0 with a
hit; dash +2; exclusive stun 0 with a hit; Cassi's stun (no walk restriction) +1.

## Q2 first strike and standoffs (alternating)
Standoff distance: neither side gains from d >= 6 when a reach-5 champion is involved (Ryth, Vesper, Prism, Stellar, Cassi), 5
for reach-4 pairs; mirrors tighter (Vendetta, Varg, Issac 3; Vesper, Willow, Cassi 4; Prism, Stellar, Marcella, Tavi, Ren 5).
No standoff within vision for a dasher vs Willow or Varg, nor Ren vs most: those always engage. Moving first one step inside the
standoff distance gains e.g. Ryth +0.11 HP fraction vs Vesper/Vendetta/Issac, Tavi +0.24 vs Vesper, Stellar +0.12-0.20 vs most.
Who moves first changes the winner in 93 (pair, distance) combinations (18 pairs at d = 1, 18 at d = 4), e.g. at d = 4 Ryth vs
Tavi (+0.13 vs loses 350), Vendetta vs Ren (standoff vs loses 620), Prism vs Varg (W700 vs +0.08).

## Q3 duels
d = 1 slugfest (no retreat), alternating, row first: Varg wins every slugfest; turn order decides 20 of 78 (all 11 mirrors plus
Ryth-Marcella, Vesper-Prism, Prism-Stellar, Prism-Tavi, Stellar-Vendetta, Stellar-Tavi, Stellar-Ren, Vendetta-Tavi,
Cassi-Issac). Ren vs Ren: neither attacks (first striker loses the retaliation race).
Open ground from d = 4 (retreat allowed), row first: Ren beats everyone but the mirror and kills Varg from any distance
without losing HP (stun + dash kiting); Varg is kited to death untouched by Ryth (stun every 8 turns from reach 5), Vesper and
Ren; Ryth stun-chases Stellar to death even when Stellar moves first; most slugfest wins become standoffs (the loser
retreats). Double moves flip many open-ground results (Ryth vs Varg from d = 1: lose in alternation, win under every
double-move order but one; Stellar/Vendetta/Varg/Issac mirrors become no-kill).
(Full tables in tables/q3_*.txt.)

## Q4 greedy casting in fights is not optimal
g1 (cast a ready damage spell whenever in reach) loses value in 63 of 936 starting situations and is strictly suboptimal in
644,553 of 48.9M reachable states (1.32%): Marcella 2.6%, Ren 2.1%, Tavi 1.8%, Ryth/Prism 1.3%, Cassi 1.0%, Issac 0.7%,
Stellar 0.7%, Vesper 0.6%, Willow 0.3%, Varg 0.2%, Vendetta 0. Winner flips: Prism vs Tavi (W165 -> L35), Marcella vs Ryth.
Exceptions: (1) one cast per turn: Marcella opens reset + stun-attack, Cassi stuns before her 140 spell; (2) don't hit into a
Varg shield (absorbed damage expires); (3) time stuns to the turn the enemy's big spell/stun comes off cooldown; (4) extra hits
on Ren cost 20 each. Vendetta's greedy reset always optimal.

## Q5 escape (closed form; 5,760 entries, 0 exceptions)
One-turn reach R1: Ryth 5 (ground stun), Vesper 5 (dash + attack), Prism 5, Stellar 5, Cassi 5 (walk + stun; 4 vs Marcella),
Vendetta/Ren/Issac 4 (walk + dash + attack), Marcella/Tavi/Willow 4, Varg 2. Your one-turn retreat r = 1, or 3 with a dash
(Cassi +1 by stunning first if d <= 4; Marcella +1 adjacent).
- Pursuer to move: escape untouched iff d > R1. You to move: iff d + r > R1; if both have dashes also d + 1 > the pursuer's
  dash-less reach (Vesper 4, Ren 4, Vendetta 2, Issac 2).
- A dash pursuer vs a non-dash target: no clean escape anywhere in vision.
- Doom (unbounded forced damage, death at any HP; 1,024 entries with a non-dash pursuer): iff you have no tempo source (dash,
  Cassi's stun, Marcella's adjacent stun vs melee) and d <= the pursuer's repeatable reach: Ryth 5, Cassi 5, Prism/Tavi/Willow 4,
  Varg/Marcella 2, Stellar never. Dash vs dash (observed): Vesper <= 4, Vendetta <= 4 (<= 2 vs Ren), Ren <= 4, Issac <= 4.
- Finite forced-damage tables give the exact HP needed to get away (e.g. Stellar chasing anyone from d = 1: 1045).

## Q6 target order (basic attacks only, everyone in range, exact game vs an optimal enemy)
2v2, 600 sampled of 4,356 fights: Smith (enemy damage / enemy HP) suboptimal in 31% (11 kill-balance changes, 2 winner flips,
mean loss .024); lowest HP first suboptimal in 40% (26, 24, .088); "discrete Smith" (damage / turns to kill) no better.
Counterexample: Stellar + Varg vs Ren + Issac: the optimum focuses Issac, who acts later in the round order; Smith ignores the
enemies' slots. 1v2 (always losing): Smith suboptimal in 433/1,584 and loses a kill in 35; lowest HP suboptimal in 5 and never
loses a kill. When you cannot win, secure kills first.

## Implications
- Priorities matter in mirrors and close fights: get first move or the first double move; shields on the second turn of a double.
- Distance to hold when you cannot win: d > enemy R1 at the start of its turn: 6 vs Ryth, Vesper, Prism, Stellar, Cassi; 5 vs
  Vendetta, Ren, Issac, Marcella, Tavi, Willow; 3 vs Varg. Against a dasher without one: fight, or break line with terrain.
- Kite Varg forever with any reset/dash/stun champion; kite nothing else; as Varg never chase a ranged champion in the open.
- Chase only with a tempo source (dash; Ryth's or Cassi's stun at their reach; Tavi/Willow walk-reset-shoot at <= 4); Stellar never runs anyone down.
- Casting: stun before damage; hold damage while a Varg shield is up; time stuns to the enemy's big cooldown; avoid extra hits on Ren.
- Escape while d + retreat > pursuer R1; inside a stunner's reach without dash/stun, running only bleeds HP.
- Teamfights: winning: focus damage/HP, preferring a target whose turn comes before your kill lands; losing: lowest HP first.
Limits: open ground only, full information, 0 shards, C&I independent, disengage at 9; double-move full duels only for 28
priority-sensitive pairs (Ren vs Varg alone took 275M states / 13.6 GB); Q6 sampled.
