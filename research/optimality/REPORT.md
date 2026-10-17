# Replacing heuristics with exact rules: theory report for morgana and rival

2026-10-17. Sources: cambc-rules.yaml (the engine-verified ruleset), the morgana and rival source, 361k+ champion hits and
9,000+ deaths from ladder replays since 2026-10-16, three exact solvers (1v1 duels, camp clears, team farming LP), and a
port of morgana's own fight simulator. No bot code was changed. Every claim below is one of: a theorem proved from the
rules, an exhaustive solver result, or a ladder measurement (with sample size). The few claims that rest on the YAML alone
and still need an engine probe are marked.

## Executive summary (ranked by expected effect)

**1. The economy is where we lose, and it is mispriced, not out-tuned.** Against procless, who draft the same five
champions, we win 10% of 115 ladder games. Kills are even (2.5 vs 2.2); they bank 35% more gems. In the first 300 rounds
they take 53% more camp damage, take 62% more wolf gems and 104% more elk gems, carry 2.3x our gem-rounds and recall 1.6x as
often. Exact clear solvers show why: health is priced exactly by the heal trip (camps never regenerate, so a clear can be
paused and resumed), and morgana's proration has the right form but wrong inputs (a 0.35·H floor instead of the enemy
burst floor; the full recall + walk instead of the marginal detour; the deficit charged twice; and two guards,
`affordable()` and the face-to-face test, that forbid exactly the clears pausing makes cheap). Its averaged clear
formulas overprice hit-taking clears by up to 68% (Varg/Ren on elk; 2-3x on groups). Fixing the pricing raises the
modelled melee farm rate 15-31%; the bag limit should be an economic-order quantity (~100-200 gems near home, not 50; +18%
team rate in the LP); and the job index should be surplus r - ρ̂τ, not the ratio r/τ (different choice in 27-43% of
decisions at ρ̂ = 0.3). Every sign of the procless gap is predicted. (§13, §8)
**2. Our melee champions forfeit their spells by walking.** Farming with a spell ready and no enemy within 6 (where a fight
follows within 8 rounds only 2-5% of the time, so the correct play is to cast), our Ren walks on 43% and our Ryth on 49% of
turns, and an excludes-walking spell is illegal after a walk. procless's Ren and Ryth walk on 7-8%. That is ~31 lost
casts per game in the first 300 rounds, 11-16% of our camp damage. Cast first, and pick attack tiles adjacent to more
members. (§11)
**3. The threat model misses double moves.** The engine's turn order is exactly rank-merge alternation (13.7M turn events,
0 mismatches): each of our champions plays alternating double turns with the same-rank enemy and strict alternation with
everyone else, and priority changes create extra double moves. So an enemy gets n ∈ {0,1,2} turns before our next one.
morgana's Safety always assumes 1. In double-move windows 37% of melee hits come from distance 3, which a one-turn model
calls safe (moderate for us: 3.5% of hits before our deaths come from beyond one-turn reach). And the fight sim always lets the enemy strike first: given the true first striker it predicts 80.5% of
decided ladder fights against 78.6%, and the enemy-first rule calls 27% of actual winners "lost". (§1, §2)
**4. Retreat timing is decidable exactly.** In open ground: escape untouched iff d > the pursuer's one-turn reach (pursuer
to move) or d + our retreat > it (us to move). A dashing pursuer runs down any non-dasher (+2 tiles per 8 turns). Only
Varg can be kited indefinitely, and only by reset, dash or stun champions. With terrain the same rule is a cheap time-expanded
BFS. 70-80% of every top team's deaths (and 78% of ours) were escapable when the killer was first seen; the point of no
return came a median 2-4 rounds before death. The solver also says the optimal stun/dash chase kills a Stellar (Ren from
d = 4, Ryth even when Stellar moves first), yet on the ladder Stellar wins those isolated 1v1s 288:201 and 207:118: an
unexploited exact edge for our Ren and Ryth. (§2.4, §3)
**5. Wards belong in bushes, and the periodic ward destroys them.** Sight is symmetric for a fixed opaque set, so only
bushes let an enemy see us unseen; only a ward inside the cluster reveals it. On the ladder maps 64% of camp work tiles
need no ward at all, and for the rest one bush ward placed on the approach covers 96% of the threat. Top teams put 96%
of wards on bushes; we put 34%, and morgana's every-20-rounds off-bush ward overwrites our single bush ward. (§4, §9)
**6. We win the priority race but do not spend it.** The exact accounting is n_e = [we act before e this round] +
[e acts before us next round]. morgana already acts before nearby enemies in 79% of close encounters and takes a free
double move (n_e = 0) 51% of the time an enemy acted first (top teams 18-34%). But Intercontinental Fish lands 12.1% of
its hits on double moves it manufactures (us 6.1%), and such hits convert to kills at 21.8% vs 15.2%. Our Safety ignores
the n_e = 0 windows in which the mirror enemy cannot touch us at all. (§1.3)
**7. Smaller exact corrections.** Target choice: Smith's rule (damage per turn / turns to kill) when winning, lowest HP
when losing (an exact 2v2 game: Smith suboptimal in 31%, lowest-HP 40%; small measured effect on ladder outcomes).
Casting: greedy is optimal on camps; in fights stun before damage, don't hit into a Varg shield, time stuns to the enemy's
big cooldown. Items: Tavi and (tanking) Ren build Focus; `main_stat` ignores passives (Ren's reflection, Ryth's health-to-Strength); top teams build Bruiser Health on Ren/Ryth/Cassi. The farm-only model's Monster emblems are not bought by top teams. Camps: Varg tanks at range 1, partners at 3;
k staggered stunners prevent exactly k/8 of monster attacks (rival's 0.75 should be 0.625). One currency (gem-equivalents)
for every decision: morgana's constants undervalue kills ~8x and gems ~3x relative to damage. Shop trips for gold alone
lose value. The draft order is already within 2% of the farming optimum; use the draft turn's 1M fuel for per-body camp
assignments and ward tiles. (§5-7, §10-15)

**What did not survive testing.** Lanchester's H·D (morgana's pack test) is the exact square-law winner rule for
continuous fire, but on ladder fights it predicts worse than the discrete sim (74.9% vs 80.5%). Champion-level turn order
inside the fight sim adds nothing over block alternation. Smith's rule is not optimal in team fights. Greedy casting is not
optimal in fights. "Chasing a fleeing target never pays" holds only without dashes and double moves; on the ladder fleeing
targets are still hit 23% of the time (anchored 40%). Getting double moves is not a gap for us (we take more of them than any top team); spending them is. The
farm-only item model's Monster emblems are contradicted by what top teams buy. The uniform blind-tile ward objective was wrong
(argmax on a bush only 12%); the asymmetric-sight version reproduces the ladder.

## Contents
1 Turn structure · 2 Reach, exposure, escape · 3 Pursuit, escape and kiting · 4 Bushes and wards · 5 Currency · 6 Target
choice · 7 Fights · 8 Job selection and banking · 9 Ward replacement · 10 Tanking · 11 Action order · 12 Unexploited rules ·
13 Camps · 14 Items · 15 Draft · Appendix A heuristic inventory · Appendix B damage tables · Appendix C data and scripts

# Part 1: turn structure, reach, pursuit, vision, value

## 1. Turn structure (exact)

**Rules used.** Team A starts odd rounds, B even rounds; teams alternate one champion at a time; within a team by
priority (desc), ties by id; a new priority applies from the next round; dead champions keep their slot.

**Model.** Let our champion u have team rank k and enemy e rank j (1-based) in round r. With equal team sizes n,
u's slot is 2k-1 if we start round r, else 2k; e's is 2j or 2j-1. Hence within round r:
u acts before e  <=>  k < j, or k = j and we start r.
For j > min(nA, nB) the larger team's extra champions act after everyone, every round.

**Theorem 1.1 (pairwise patterns).** Holding ranks fixed:
- k < j: u acts first in every round: strict alternation U E U E ...
- k > j: e first in every round: strict alternation E U E U ...
- k = j (the *mirror* pair): U E | E U | U E | E U ... = U E E U U E E U ...: the pair plays **alternating double
  turns**: each side gets two consecutive turns at every other round boundary.

**Corollary 1.2 (enemy turns before our next turn).** n_e := number of e-turns strictly between u's turn in round r
and u's turn in round r+1 = [u before e in r] + [e before u in r+1] in {0,1,2}. With fixed ranks n_e = 1 for every
non-mirror enemy, and n_e alternates 2,0,2,0 for the mirror. Summed over enemies u faces n-1 and n+1 enemy turns
on alternate rounds.

**Corollary 1.3 (priority manufactures double moves).** The first term of n_e is fixed when u decides; the second is
set by the priorities for r+1 (u's own, its teammates', and e's team's). If u acted after e this round, ranking u
before e next round gives n_e = 0: a *free double move* against e (and against every enemy u jumps). If u acted
before e this round, ranking after e next round hands e a double move (n_e = 2). Since priorities only order a team
internally, "before e" means k < j(e) (or k = j and we start r+1), so the rank-1 slot is the contested resource.

**Verification.** A slot model built from these rules (priorities read at the end of round r-1) reproduced the turn
index of all 13,657,422 champion events in the ladder replays since 2026-10-16 with 0 mismatches.

**Evidence that it matters.** 361,607 champion hits since 10-16:
- 14.1% of all hits are delivered on the attacker's second consecutive turn (n = 2).
- Of those, 45% (Fish), 60% (us, Mite), 83-86% (SBC, Univardisty, procless) are mirror pairs; the rest come
  from priority changes. Manufactured double moves are 12.1% of everything Intercontinental Fish (#1, 68% wins)
  hits with, vs 6.1% for us and 1.6-1.9% for SBC/Univardisty/procless. Fish keeps priority 0 at rest and raises it
  to 1-10 during fights (changes on 4.7% of champion-rounds): a computed urgency.

- Who gets the windows (enemy within 5 at the start of our turn; 3,000 games): when the enemy acted before us this round,
  the share of times we rank before it next round (a free double move): us 51%, Fish 34%, procless 25%, SBC 20%, Mite 18%,
  Univ 18%. When we acted first, the share of times the enemy ranks before us next round (a double move given away): us 15%,
  others 22-35%. And we act first in 79% of these close encounters. So morgana already wins the priority race; what it
  does not do is spend the windows: Fish lands 12.1% of its hits on manufactured double moves, we land 6.1%.
- Conversion: the victim died within 2 rounds after 15.2% of hits from attackers with one turn in between,
  18.7% of mirror double-move hits and 21.8% of manufactured double-move hits (n = 363,644; partly selection,
  since teams raise priority when a kill is near).

**Code gap.** morgana's Safety threat model (safety.cpp `strike`, `Safety::build`) evaluates every enemy for exactly
one turn: `next_turn_round` returns one round and the area is square(pos, one-turn reach). It is wrong in both
directions for the mirror enemy every round: it misses the n = 2 threat (see 2.2) and ignores the n = 0 window in
which the mirror enemy cannot touch us at all. `turn_order.cpp` `can_act_before` ignores our own rank and the
merge structure; `offer_escape`/`damage_bound(double_unacted)` double *damage* for unacted enemies but keep the
one-turn *reach*.

**Exact replacement.** For each enemy compute n_e from the slot formula (current ranks; for visible enemies read their
priority, unseen ones keep their last rank) and use the m-turn reach/damage below with m = n_e. For priority:
each champion's urgency for "acting before e next round" is the value difference of the next-turn state with
n_e reduced by one (a kill that becomes possible, damage avoided, a channel that completes or is cancelled). With
n <= 6 the team's best rank permutation is a 720-way argmax; decentralised, a sort by individual urgency is the
greedy approximation the band system already implements; what it lacks is the n_e accounting.

## 2. Reach, exposure and the point of no return

**2.1 m-turn reach (exact, open terrain, abilities ready).** With m own turns before our next turn, the farthest
Chebyshev distance an enemy can damage us at:
- melee basic: 1 + m (walk m, attack on the last); dash ready: +2 (once per cooldown) → 3 + m.
- ranged basic: 3 + (m - 1) (a ranged walk spends the attack, so only earlier turns move); attack reset ready:
  +1 (walk, reset, attack); Vesper dash: +2.
- unit spell (range 4, excludes walking on its turn): 4 + (m - 1); ground spell: 5 + (m - 1); Cassi's stun (does
  not exclude walking): 5 + (m - 1) (stun only).
- m = 0: nothing.

| champion | R1 basic | R1 best (all ready) | R2 basic | R2 best |
|---|---|---|---|---|
| Ryth | 2 | 5 (ground stun) | 3 | 6 |
| Varg | 2 | 2 | 3 | 3 |
| Ren | 2 | 4 (dash; unit stun 4) | 3 | 5 |
| Issac / Vendetta | 2 | 4 (dash) | 3 | 5 |
| Marcella | 2 | 4 (unit) | 3 | 5 |
| Cassi | 3 | 4 dmg / 5 stun | 4 | 5 / 6 |
| Stellar / Prism | 3 | 5 (ground) | 4 | 6 |
| Tavi / Willow | 3 | 4 (reset; Tavi unit 4) | 4 | 5 |
| Vesper | 3 | 5 (dash) | 4 | 6 |

**2.2 Verification (600 ladder games, 100,131 hits).** Distance from attacker to victim at the end of the victim's
previous turn, by attacker turns in between:
- melee, 1 turn, no dash: d <= 2 in 99.3%; with dash: d = 4 in 26.7% (walk 1 + dash 2 + range 1).
- melee, 2 turns, no dash: **d = 3 in 36.9%** (outside the one-turn model); with dash d = 5 in 22.5%.
- ranged, 1 turn: d = 4 in 1.5% (reset); 2 turns: d = 4 in 25.6%, d = 5 in 0.8%.
Every observed hit lies inside R_m; the residue at R_m + 1 (<= 0.7%) is reconstruction noise. So the reach rule
is exact, and a one-turn model misses 37% of melee hits in double-move windows.
Size for us: 2.1% of all hits we receive, and 3.5% of hits in the 2 rounds before one of our deaths, come from beyond
the one-turn reach on a double move; 14% of pre-death hits land on the attacker's second consecutive turn (damage a
one-turn model also undercounts). Real but moderate: the larger effect of n_e is on our own opportunities (n_e = 0
windows and manufactured double moves, §1.3).

**2.3 Exact exposure bound.** For a candidate end tile x:
I(x) = camp(x) + Σ_e D_{n_e}(e, d(e,x)), where D_m(e,d) = max damage e can deal at distance d within m own turns
(a 3-variable DP over (turn, distance, cooldowns): one cast per turn and per-slot cooldowns make D_2 differ from
2·D_1: Stellar at d=3 with both slots ready: D_1 = 200 + 35 = 235, D_2 = 235 + (140 + 35) = 410, not 470; with only
slot 0 ready D_2 = 270). Use I(x) for lethal checks (worst case) and for tile choice; unseen enemies keep
their probability weights.

**2.4 Escape region and the point of no return (exact algorithm).** Safe_k = tiles outside every visible enemy's
reach R_{m_e(k)} after our k-th move, with m_e(k) = cumulative e-turns (k for non-mirror; n_e,2,... pattern for the
mirror). Frontier_0 = {us}; Frontier_{k+1} = dilate(Frontier_k) ∩ open ∩ Safe_{k+1}. An escape exists iff the
frontier reaches our spawn (or survives H layers). Using Chebyshev balls for enemies makes it a guarantee
regardless of walls (conservative); using enemy walking fields makes it tight. Cost: H·(n_enemies + 3) host
bitboard ops (≈ 8·8·150 ≈ 10k fuel).
Decision rule ("never cross the point of no return unless the fight is won"): before ending a turn at x, require
escape(x) for next turn unless the exact fight at x is won under the true first-strike order.

**2.5 Death audit (this rule against the ladder).** For 9,094 deaths to champions in games of the top six and us
since 10-16: at the round the victim first saw a future attacker, a guaranteed escape (8-turn BFS, conservative)
existed in 70% (Fish), 76-80% (Mite, SBC, Univ, procless) and 78% (us) of deaths; 2-8% never saw the killer; the
last escapable round was a median 2-4 rounds before death. Deaths are decision outcomes, not geometry, for
every team.

**2.6 First strike.** In 6,427 isolated 1v1 kills since 10-16 the killer landed the exchange's first hit 83% of the time
(ranged killing melee 92%, ranged>ranged 85%, melee>melee 81%, melee killing ranged 66%). Partly selection, but
it confirms that whoever concedes the first strike usually loses. Who concedes it is determined exactly: the side
that ends a turn inside the other's R_{n} without striking. morgana's fight model assumes "they strike first" in
every fight (`trade`), which is the worst case, not the actual order: it marks fights we would open as lost.
**Validation (replay agent; morgana's Trade sim ported to Python, 9,756 decided fights in 1,274 games since 10-16,
95% CIs by ladder group).** Block sim given the true first striker: 80.5% accuracy, AUC 0.876 (93% in 1v1). Enemy-first,
as morgana runs it: 78.6% (-1.9 [-2.3, -1.6]); it calls 27% of sides that actually won "lost" (us 20%), and in 11% of
fights both sides "lose" when struck first. Champion-level slot order instead of block alternation: level at best
(+0.1, only when started at the real first striker; -1.3 from the round start). Lanchester H·D ratio: 74.9%; HP ratio
72.1%; "first striker wins": 69.3%. So: keep the block sim, feed it the first striker that positions and n_e imply,
and do not bother with slot-level order inside the sim (slot order matters for reach and threat, §1-2, not for
resolving the exchange).

## 3. Pursuit

**Theorem 3.1 (equal speed).** Pursuer P and evader E each walk at most one king step per own turn, Chebyshev
distance d. On open ground, from any offset with max(|dx|,|dy|) = d >= 1 the evader has a step to distance d+1
(step along the sign of both components). Hence if E steps away after every P-turn, the distance after each
P-turn is non-decreasing. P closes only if:
(a) E does not walk (a ranged attack, an excludes-walking cast, a channel, farming, a stun);
(b) P gains a move: a dash (+2, once per 8 own turns), a double move (mirror, every other boundary, or one
manufactured by priority);
(c) E is blocked: walls, map edge, units, dead ends: exactly the escape region of 2.4 computed for E.
**Corollary 3.1b (dash closing speed; duel solver Q5).** A dash adds 2 steps once per 8 own turns and an evader without a
dash cannot win them back, so a dashing pursuer (Ren, Issac, Vendetta, Vesper) closes on a non-dashing evader at 1/4 tile
per turn net. On unbounded open ground it always forces damage eventually: the exact solver finds no safe start distance
within its whole search range for every dasher vs non-dasher pair (Ren/Issac/Vendetta vs Ryth, Stellar, Varg, Cassi, ...).
It catches in about 4·(d - R) own turns. A non-dasher escapes only by reaching spawn (or terrain) first: the escape
condition is steps to spawn < 4·(d - R). Non-dashing pursuers (Ryth, Stellar, Cassi, Prism) need d >= 5-6 to be
escaped with zero damage when they move first, Varg only 3. Ren and Issac are in nearly every meta draft, so this
governs every retreat against them.
**Theorem 3.3 (escape, closed form; duel solver, all 5,760 solved 1v1 open-ground entries, 0 exceptions).** With R1 the
pursuer's one-turn reach (Ryth, Vesper, Prism, Stellar, Cassi 5; Vendetta, Ren, Issac, Marcella, Tavi, Willow 4; Varg 2) and r
our one-turn retreat (1, or 3 with a dash): pursuer to move → escape untouched iff d > R1; we to move → iff d + r > R1 (both
dashing: also d + 1 > the pursuer's dash-less reach). A dasher vs a non-dasher: no clean escape anywhere in vision. Doom (death
at any HP): no tempo source of our own (dash, Cassi's stun, Marcella's adjacent stun vs melee) and d ≤ the pursuer's repeatable
reach (Ryth 5, Cassi 5, Prism/Tavi/Willow 4, Varg/Marcella 2, Stellar never). This is the open-ground special case of the
escape BFS (2.4); terrain only helps the evader.
**Theorem 3.4 (kiting; duel solver Q1).** A ranged champion deals unbounded damage to a chasing melee without ever being hit
iff it has a recurring damage action that costs no distance (attack reset, dash or stun) and the melee has no reach-4+ tool.
That leaves exactly one kitable melee, Varg: per 8 own turns Tavi 177, Cassi 114, Prism 94, Vesper 55, Willow 27 (Stellar,
with none of the three, is capped at 575 total). Against Ryth, Ren, Vendetta, Issac and Marcella there is no sustained kiting,
only an opening poke (Stellar 140 / Prism 80 vs Marcella from 5). Standoff: nobody gains by stepping in from d ≥ 6 when a
reach-5 champion is involved (5 for reach-4 pairs); moving first one step inside it is worth up to +0.1-0.24 HP fraction, and
who moves first flips the winner in 93 (pair, distance) combinations. So the replay agent's finding that top ranged champions
hold d = 4-5 (not exactly 3) is the standoff band, not sloppiness.
**Solver vs ladder (isolated 1v1 kills since 10-16, row kills : column kills).** Agrees: Ren vs Varg 77:26 (solver: Ren kills
Varg untouched), Ren vs Issac 103:18, Stellar vs Varg 265:93, Stellar vs Tavi 299:106, Stellar vs Cassi 553:168, Cassi vs Varg
112:50. Disagrees: Ren vs Stellar 201:288 and Ryth vs Stellar 118:207, where the solver says the optimal stun/dash chase
kills Stellar. Ladder bots do not play that chase, so Stellar over-performs; our Ren and Ryth have an exact, unexploited edge
against enemy Stellars, and our Stellar must respect d > R1 = 4 (Ren) / 5 (Ryth) against them.
**Corollary 3.2.** A chase of a healthy enemy that walks away and has a non-empty escape region gains nothing until
one of (a)-(c) occurs. Its value is the probability of (a)-(c) within the chase horizon, minus the rounds spent.
**Data (73,322 chase streaks since 10-16: >= 3 consecutive turns approaching the same visible enemy from outside
our one-turn reach).** When the target kept its distance over the streak, the chaser hit it within the streak or
the 3 rounds after 23% of the time; when the target let the distance shrink (anchored), 40%. The same for every top
team (Fish 26/47, Mite 18/36, us 24/40). So (a)-(c) do happen in practice, but a fleeing target pays about half as often. morgana `prey()` (bot.cpp) ranks targets by
turns = max(0, d - range) + health/strength, i.e. assumes the target stands still. Exact replacement: a target is
catchable iff (i) it is inside our R_{1} now (burst), (ii) it is anchored (channelling, attacking a camp as a
ranged champion, stunned), or (iii) its escape region against our team is empty within the chase horizon.

## 4. Vision: bushes and wards

**Theorem 4.1 (bush cover).** Basic attacks and unit abilities need a visible target; a bush tile is invisible to
every viewer outside its cluster; vision is personal (own body + own ward). So a champion on a bush tile can be
hit only by: ground AoE (Ryth s0, Stellar s1, Prism s1), Varg's splash, camps, an enemy inside the same cluster,
or an enemy whose own ward is in the cluster.
**Verification (1,500 ladder games).** Of 11,878 basic attacks on bush-standing victims, 97.8% had the attacker in
the cluster or its ward in it (the 2.2% residue is splash/noise); non-ground casts 99.3%. 60% of all hits on
bush-standing champions were enabled by the attacker's own ward in the cluster.
**Implications.** (1) Exposure at a bush tile x not covered by an enemy ward drops to AoE threats + enemies that can
enter the cluster within n_e turns. Against the meta comp this removes Varg/Ren/Issac/Cassi entirely and cuts a
Stellar's expected output from ~77/round to its ground spell (~17.5/round). (2) Tribute tiles, waiting tiles and
camp attack tiles should be chosen by I(x) with this rule. (3) The ward is the counter: one ward inside a cluster
makes it transparent to its owner.

**Theorem 4.2 (only bushes need wards).** "Sight is symmetric for a fixed set of opaque tiles." So an enemy behind
a wall that we cannot see cannot see us either. To basic-attack or unit-cast us it must stand where we would see it
(blind ground AoE needs information it does not have from its own vision). The opaque set differs between viewers
only through bushes (a viewer's own cluster is transparent to it). So the only tiles from which an unseen enemy
can target us are the threat set
  B(p) = {bush tiles x in clusters other than ours, d(x,p) <= 5, p visible from x},
and they can be revealed only by a ward inside the same cluster. Hence every safety-optimal ward is a bush tile, and
a work tile with B(p) = ∅ gains nothing from a ward.
**Ward value.** V(w) = Σ_{x ∈ B(p) ∩ Vis(w)} π(x)·c(x), w a tile of a threatening cluster, minus what the current
ward w0 already covers (one ward per champion; a new one replaces it). The ward is placeable within 2, so it goes
down on the approach to the work tile, not from it.
**Check on the 17 ladder maps** (every attack tile of every own-half group with damaging monsters; approximate
line of sight): 409 of 642 work tiles (64%) have B(p) = ∅. On the other 233, the best ward (a bush tile within 6
of the work tile, i.e. within 2 of a tile within 4 on the way in) covers 96% of B(p) on average, and all of it at
204 (88%). From the work tile itself (within 2) it covers only 18%. The theory reproduces the top teams'
behaviour: 96% of their wards are on bushes, one every 7-27 rounds per champion.
**Cost.** Vis(w) is a shadowcast (StaticMap::viewers ~10k fuel), so compute it once per work area, or in the draft
(1M fuel) for each group: best ward tile and the approach tile it is placed from, ~4 bytes per group in the
1024-byte draft memory.
morgana: `ward_bushes` wards the largest bush cluster within 4 of where it stands. Every 20 rounds
(`ward_period`) it moves the ward to the tile farthest from spawn, explicitly off bushes, overwriting the bush ward
(see 9.1).

## 5. One currency for every decision

Everything converts to **gem-equivalents** (team differential). Measured since 10-16: production
ρ ≈ 0.30 tributed gems per pick-round (0.27-0.34 by team), gold ≈ 1.4 per pick-round; walk spawn→farm W ≈ 15-35.
Gold's value γ: a shard (30 gold) adds its growth g to a stat s; a champion that clears a fraction f_c of its time
gains Δρ ≈ ρ·f_c·g/s per round for the rest of the game L: early (s=50, g=5, f_c≈0.3, L≈500) γ ≈ 0.15 gem/gold,
falling towards 0 late. A champion-round is worth v_r = ρ + 1.4γ ≈ 0.5 (early) to 0.3 (late).
- **Kill** of an empty-bag enemy: v_r·(60 + W) + 50γ ≈ 40-50 gem-eq; plus each carried gem counts ~2 (they lose
  it, we carry it). A Cassi/Issac kill is two bodies: ~85 gem-eq plus both bags.
- **Non-lethal damage** x to an enemy: at most the heal trip it forces, δ = v_r·(recall 5 + W + 1)/H_usable ≈
  0.02 gem-eq per HP (0 if it will go home anyway before needing to).
- **Camp damage**: (gems + γ·gold)/HP: gem cluster 0.048, wolf 0.026, elk 0.025, Monolith 0.012, gold cluster 0.01.
- **Stun**: one enemy turn: its turn's damage δ·D_e, or one production round v_r out of fights, plus channel
  effects (recall: turns already channelled × v_r; tribute: channel turns lost and the exposed bag).
In HP units (divide by δ ≈ 0.02): a kill ≈ 2,000-2,500 HP, a carried gem ≈ 50 HP each side. morgana
(abilities.cpp, turn_order.cpp, self_abilities.cpp) uses kill 300 HP and gem 15 HP: relative to damage it
undervalues kills ~8x and gems ~3x. Consequences: chip damage is overrated against finishing, against holding a
spell for a kill breakpoint, and against farming (chip damage ≈ a wolf hit at best).

## 6. Target choice

**Theorem 6.1 (Smith's rule).** If our side delivers attacks one at a time into a set of enemies that all stay in
range, enemy j needs p_j = ceil(H_j/s) attacks and deals D_j per turn while alive, then total damage taken
Σ_j D_j·C_j is minimised by killing in decreasing D_j/p_j (exchange argument: swapping adjacent j,i changes the
cost by D_i p_j - D_j p_i). With kill values V_j and per-turn escape hazards h_j the index becomes
(δ·D_j + h_j·V_j)/p_j. "Lowest health first" (morgana `attack_target`, Trade sim `weakest`) is the special case of
equal D_j; it also ignores that targets needing the same number of hits are tied.
Example: our 100/turn; enemy A (Stellar, 750 HP, ~120/turn averaged) vs B (Varg at 600 HP, 50/turn). Weakest-first
B→A takes 50·6 + 120·14 = 1,980; Smith A→B takes 120·8 + 50·14 = 1,660 (-16%). An enemy Cassi or Issac counts
both bodies' D in the index (both stop when one dies).
**Exact check (duel solver Q6, 2v2 basic attacks, exact game vs an optimal enemy, 600 sampled fights).** Smith is the best
heuristic tested but suboptimal in 31% of fights (lowest-HP-first 40%; Smith's mean loss .024 vs .088, winner flips 2 vs 24).
Its blind spots are the assumptions of 6.1: the enemies' turn slots (the optimum may focus the enemy who acts later, because
its turn comes before our kill would land) and survival (a side that is losing should secure kills: in 1v2 lowest-HP-first is
suboptimal in 5 of 1,584 fights and never loses a kill, Smith loses one in 35). Rule: winning → Smith, tie-broken towards
targets whose turn falls before our kill completes; losing → lowest HP (finish what can be finished).
**Measured effect.** Swapping weakest-first for Smith targeting inside the ported Trade sim changes outcome-prediction
accuracy by -0.1 [-0.4, +0.2] on all decided fights and +0.4 [+0.2, +0.6] (+0.9 in 2v2+) on the participant set: on
the ladder, fights are rarely close enough for target order to flip them. The theorem stands for our own target
choice (it never does worse), but expect a small effect.
Stuns: a stun removes one turn, so it goes to the enemy whose next turn is worth most (max D_e this turn including
ready spells, or a channel about to complete), not the one with the highest Strength (Trade sim `act`).

# Part 2: decisions

## 7. Fights: what the health × damage test really is

**Proposition 7.1 (Lanchester square law).** Continuous focus fire, every unit in range: side A has N_A units of
health h_A and damage rate d_A; dN_A/dt = -N_B·d_B/h_A and symmetrically. Then N_A²·h_A·d_A - N_B²·h_B·d_B is
invariant, and with total health H = N·h and total damage D = N·d this is H_A·D_A - H_B·D_B. So morgana's
`pack_zone` test (bot.cpp, sum health × sum damage, outmatched when theirs > 1.3 × ours) **is** the square-law
winner test. The winner keeps a fraction sqrt(1 - r) of its force, r = (H_B·D_B)/(H_A·D_A) < 1.
**But it is a worse predictor than the sim.** On 9,756 decided ladder fights the H·D ratio predicts the winner 74.9%
of the time against 80.5% for morgana's own Trade sim given the true first striker (2.6). The square law assumes
continuous fire, everyone in range and no cooldown burst; small discrete fights violate all three. `pack_zone` should
use the sim (with the first striker implied by positions and n_e) rather than a ratio with a margin.
**What the heuristics add or miss.**
- The margin 1.3 (0.75 when hurt) stands in for first strike and uncertainty. First strike is computable (2.6):
  one free volley adds D·1 turn to the striker's effective health-damage product. The exact discrete Trade sim with
  the true slot order replaces the margin.
- Even a won fight costs: at r = 1/1.3 the winner loses 1 - sqrt(1 - 0.77) = 52% of its health pool, i.e.
  ~0.5·H·δ gem-eq of heal trips plus death risk. Engage iff E[kills]·V_K - E[deaths]·V_K' - ΔH_ours·δ > the
  surplus of what the fighters would do instead (farming ≈ v_r per champion-round).
- Being outmatched does not by itself mean leaving now: if the escape region (2.4) is non-empty next turn, the
  decision can wait a turn (farm, finish a capture); leave when the next action would empty it.
- pack_radius 7 / pack_ally_radius 5: replace by "enemies whose R_m reaches us within the fight horizon" and "allies
  whose walk minus reach is below the fight's duration" (7.3).

**7.2 Asymmetric stakes.** A death costs V_K' = v_r(60+W) + 50γ + 2·(our bag), so the fight threshold rises
linearly with the bag; rival's `brake_bag = 30` ("retreat when carrying 30+") is the step-function version. With
the currency: carrying B extra gems raises the cost of a death by 2B gem-eq, so a fight with death probability p
needs extra expected gain 2Bp.

**7.3 Rally.** An ally at walking distance L with reach R arrives after max(0, L - R) turns; it changes the fight iff
that is below the fight's length T from the sim (turns_to_kill). morgana's `rally_radius 12`, `chase_radius/2`,
`fight_ally_radius 4` are fixed stand-ins for L - R < T.

**7.4 Camps are a third party.** Monsters hit the nearest champion of either team within 3 (ties lowest id).
morgana's `awake_members` models this for our own exposure, but the fight sim gives camp damage to us only
(`Side::camp`). Fighting where the enemy is nearer the awake monsters adds 20/60/200 per member per round (wolf,
elk, Monolith) to their side's damage taken, and a champion killed by a camp loses its bag. A ground spell that
hits an enemy next to a sleeping group wakes that group on them; `wake_risk` avoids waking groups near us but never
counts waking them near enemies.

## 8. Choosing the next job: surplus, not ratio

**Theorem 8.1 (average-reward optimality).** Model play as a semi-Markov decision process: each job a (a camp
group, a fight, a banking trip) takes τ(a) rounds and yields r(a). The long-run reward rate ρ* is maximised by a
policy satisfying h(s) = max_a [r(s,a) - ρ*·τ(s,a) + E h(s')]. The myopic index this gives is the **surplus**
r - ρ*·τ, not the ratio r/τ. They pick the same job only when ρ* equals the best ratio. Since ρ* also counts
walking, waiting and fighting, it is below the best ratio, and the ratio rule over-prefers short jobs. Camps are
not repeatable at will (respawn timers), so the difference is real.
morgana `farm()` picks max `worth(cycle)` = (share·(gems + gold·clear/cycle) - death·stake)/cycle: a ratio.
Exact replacement: maximise share·(gems + γ·gold) - death·stake - ρ̂·cycle, with ρ̂ the champion's realised rate
over the last ~100 rounds (or the team's). The same index compares farming with chasing, rallying and banking,
which `decide()` now orders by fixed branch priority.

**8.2 Bag chaining.** Chaining another capture onto bag B saves the altar round trip T_s but carries B for T_x more
rounds at local death hazard h: chain iff v_r·T_s > 2·B·h·T_x (+ the new capture's own risk). With the measured
hazards (0.15-9 per 1000 rounds by position): B = 50, T_x = 30 costs 0.45 gem-eq near home and 27 deep in
enemy ground, against ~20 for a saved 40-round trip. farm() already prices death × stake, so
`chain_bag_limit = 50` is a redundant cap that is too tight at home and too loose forward. The optimal bag size
itself is an economic-order quantity (13.4).

**8.3 Heal value.** A hurt champion's trip home is worth the heal it buys: (deficit/H_usable)·(recall + W) rounds.
At 40% deficit and 65% usable health that is 18 rounds, against the fixed `recall_heal_bonus = 6` (bot.cpp
capture_recall).

**8.4 Shopping trips.** A trip home only to shop costs about (recall 5 + W) rounds ≈ 30·v_r ≈ 15 gem-eq. Buying
150 gold of shards now rather than at the next natural visit gains Δρ·T_n. With Δρ ≈ 0.045 gem/round for 5 main-stat
shards early and T_n the time to the next visit (top teams: median 58-81 rounds between spawn visits), the gain is
≈ 3 gem-eq. Pure shopping trips (`wants_shop`, `shop_trip_gold = 150`) lose value; shop when home anyway.

**8.5 Partial clears persist.** "Camps never regenerate." Leaving a half-cleared group loses nothing but the walk
and the risk of an enemy finishing it. morgana's `finishing_camp` comment ("the clear is lost") and its 0.6 health
rule should compare the remaining clear damage (exact via min_camp_damage) with health above the enemy-burst
floor (2.3), not a fixed share.

**8.6 Endgame.** The race is to reach 1000 first, so near the end the objective changes from the gem differential to
hitting times. If score + team bags ≥ 1000, extra farming is worth zero: bank the subset of bags that reaches
1000 with the earliest last completion (walk + ceil(bag/10) turns). If the enemy's earliest possible win
(their score + carried bags + time to altars) comes before ours, bags we cannot tribute before it are worth zero.
Denial (locks, stuns on tributes, killing carriers) then has priority. rival's `close_margin 60`,
`enemy_close 100` and morgana's `endgame_horizon 400` / `margin 20` are fixed stand-ins for these times.

**8.7 Parallel tribute.** Tribute lasts ceil(bag/10) turn ends and only a stun cancels it. Splitting a bag of G
among k holders who tribute in parallel cuts the exposed channel from G/10 to G/(10k) turns. That is the exact
reason behind rival's `big_holders = 3` for 150+-gem groups. Splitting does not change expected death losses on
the way, which are linear in the bag.

**8.8 Altar locks.** A lock (10 gold ≈ 1.5 gem-eq) cancels every tribute at its altar and costs the enemy 3 basic
attacks (an enemy tribute attempt counts as one and spends its attack), plus the lost channel turns. Locking an
altar where an enemy is tributing (rival `lock_tributers`) is positive EV whenever ≥ 2 enemy turns are lost.

# Part 3: wards, tanking, action order within a turn

## 9. Wards: the replacement rule

**Lemma 9.1.** A champion has exactly one ward; a new one replaces it. So the decision is never "place a ward" but
"move my ward from w0 to w", worth V(w) - V(w0) (4.2). A placement can lose value.
**Code.** `place_ward` (bot.cpp:1070) first tries `ward_bushes`. Otherwise, every 20 rounds (`ward_period`), it puts
the ward on the tile within 2 farthest from spawn, explicitly off bushes (`ward_targets(true)`, pathing.cpp:371),
replacing whatever the champion had, its bush ward included.
**Data (replay agent).** Top-6 teams put 96% of their wards on bush tiles (four of them 100%), at 2.2 wards per 100
alive champion-rounds, a champion re-warding every 7-27 rounds. We put 34% on bushes, at 7.0 per 100. Bushes are the
only tiles that need a ward (Theorem 4.2), and 60% of hits on bush-standing champions were enabled by the attacker's ward in the cluster (4.1).
**Replacement.** Use V(w) - V(w0) with V from 4.2 (the bush threat set B(p) of the work tile). Under that objective a
forward non-bush ward has V ≈ 0 for the owner's safety, so it should never replace a bush ward that covers the
work area. Scouting value (tracking enemies for teammates through the 8 shared bytes) is real but second-order: it
only matters through the comms sighting slot.

## 10. Tanking camps: the nearest-champion rule as an assignment

**Rule.** Each awake monster hits the nearest champion within 3 (Chebyshev, ties to the lowest id), once per camp phase.
**Proposition 10.1.** For a crew clearing a group with attacking members M, champion T takes every hit iff for all
m ∈ M within 3 of T: d(T,m) < d(X,m) for every other crew member X (or equal and T has the lower id). Non-tanks
then take zero camp damage. Given the tank's tile, the safe tiles for the others are
S = {x : ∀m ∈ M, d(x,m) > 3 or d(x,m) > d(T,m) (≥ with higher id)}: a few bitboard ops.
**Choice of tank.** Total camp damage taken is fixed by the clear time (Σ_m str_m·alive time, Smith's order); the
crew chooses who pays. The cost of damage is the heal trip it forces, prorated by usable health (8.3), and lower with
Jungle (-30%), Durability (-10%), Varg's shield (2.5·Focus per 8 rounds = 31/round at base, more than a wolf's 20).
So the tank should be the champion with the largest effective usable health per camp damage (Varg, then Ryth).
Spreading the damage only adds heal trips: concentrate it on one tank until its recall, then rotate.
**Data.** In mixed melee+ranged clears top teams' melee take 86% of camp damage while dealing 54%, and the
highest-HP champion takes 60%. Ours are 77% and 42% (others 77% / 59%). morgana has no tank coordination: each
champion picks attack tiles alone (`attack_tiles`), and `farm()` only marks a group "shielded" when a melee ally is
already in its threat area.

## 11. Order of actions within a turn

**11.1 Cast before walking (exclusive spells).** An excludes-walking spell is illegal after a walk, and the walk is
illegal after the spell. If a target is in spell range from the current tile, the cast is available now and the
walk is not needed to attack (melee attacks the same turn when already adjacent; otherwise the walk was only
repositioning). Casting first and skipping the walk dominates walking first whenever the spell's damage (100-200)
exceeds the value of one step (≤ one basic attack, 35-50). morgana farm() walks, then calls `cast_at_camp`
("only casts that allow walking remain").
**Data.** While actively farming with a damage spell ready, we cast 60% of the time against procless 80% and Mite
72%. Ren 45% vs 68%, Ryth 48% vs 76%: both are melee champions with excludes-walking spells. Stellar s0 63% vs 89%,
s1 67% vs 94%. That is about 31 uncast spells per game in the first 300 rounds, roughly 3-5k camp damage, or 11-16% of our
camp output.
**Mechanism isolated (115 games vs procless, first 300 rounds, farming with a spell ready and no enemy within 6, where
a champion fight follows within 8 rounds only 2-5% of the time).** Our Ren walked on 697 of 1,608 such turns (43%) and our
Ryth on 844 of 1,717 (49%), and never cast on those turns (illegal after a walk). Standing still, they cast 82% and
95%. procless's Ren and Ryth walk on only 8% and 7% of those turns. So the melee spell loss is walking between members
instead of (i) casting first when a member is within 4 and (ii) choosing an attack tile adjacent to as many live
members as possible (fewer re-positioning walks). Stellar standing still: s0 86% vs 95%, s1 72% vs 95% (ground: the
`wake_risk` skip and the value floor are the remaining filters).
With an enemy within 6 a fight follows within 8 rounds 52-74% of the time, so holding there (hold_range) is
defensible: casts 16-26% for us, 20% procless, 78% Mite.

**11.2 Greedy casting on camps.** With no enemy that could fight within the cooldown window, a damage spell held
for d rounds loses d/8 of a cast and gains nothing (camp HP is not discretised against the spell). So cast at the
first legal turn. morgana's `cast_at_camp` returns nothing while any visible enemy is within 6 (`hold_range`), and
its `min_camp_value = 50` floor is the only other filter (the walking loss of 11.1 is separate). The correct hold condition: the
expected value of having the spell in a fight within 8 rounds exceeds its camp value now. An enemy within 6 is a
proxy for that.
**11.2b Greedy casting in fights is almost, not exactly, optimal (duel solver Q4).** Casting every ready damage spell in
reach is strictly suboptimal in 1.32% of 48.9M reachable duel states (winner flips in 3 of 936 starts). The exceptions are
exactly the cases where the cast's value depends on timing: (1) one cast per turn, so order matters: stun before damage
(Cassi), Marcella opens with reset + stun-attack; (2) don't hit into a Varg shield that will expire with damage left;
(3) save a stun for the turn the enemy's big spell or stun comes off cooldown; (4) extra hits on Ren cost 20 each.
On camps, every DP-optimal plan casts on the first legal round (econ T1).
**11.3 Attack reset.** A reset is a full extra basic attack every 8 rounds (+1/8 of basic damage). Holding it has
option value only for a fight within the cooldown. Top teams use it on 85% of ready camp-attack turns; we use it on
72%. morgana holds it while any visible enemy is within attack range + 2 (`reset_hold_margin`).
**11.4 Melee hit-and-step.** A melee champion may attack, then walk. Ending the turn one tile farther gains nothing
against an enemy with n_e = 1 (its reach is 2) unless the step leaves R_{n_e} entirely or blocks a line. Univardisty
hit-and-steps 50% of the time. The exact rule is I(x) minimisation over the end tile after the attack.

# Part 4: rules neither bot exploits

**12.1 Respawn denial.** "The group returns at the start of round payout + timer, or later while any of its camp tiles
is occupied." A champion standing on a captured enemy group's camp tile holds its respawn indefinitely. Value per
round = the group's reward rate to the enemy (gems + γ·gold)/(respawn + clear + capture), e.g. a 48-gem cluster pair
on a 50-round respawn ≈ 0.8-1 gem/round, against our champion's own v_r ≈ 0.5, plus its risk (deep in enemy ground,
hazard 5-9 per 1000 rounds there). It pays only for the enemy's best groups and only where the enemy cannot contest
cheaply. Enemies can do the same to our groups, and our own champions must step off a respawning group's tiles (morgana
already does).
**12.2 Hidden-blocker probes.** Acting onto a tile that holds an unseen unit fails, spends nothing and reveals the tile
for the rest of the round. A move into an unseen bush tile either reveals an enemy for free or succeeds; dashes the
same over 2. Moves we would make anyway through bush tiles are free scans; a move whose success we do not want is not.
**12.3 Altar locks as tribute cancellers.** Placing a lock cancels every tribute channel at that altar (both teams').
With one lock carried (10 gold), a champion within 2 of an altar where an enemy is channelling a bag cancels it at once;
the enemy then needs 3 basic attacks to clear the lock before re-starting (its own tribute attempt counts as one and
spends its attack). rival does this (`lock_tributers`); morgana does not.
**12.4 Tavi's full refunds.** Tavi buys shards anywhere and sells everything at full price on spawn ("refunds are not
earned gold"), so a Tavi can hold a farming build (Jungle) and swap to a fighting build at every spawn visit at no
cost.
**12.5 Tribute timing.** The channel length is set by the bag at the start, but completion scores the whole current bag.
Gems only arrive by capture shares (paid at round start to champions on the camp tiles) and kills (impossible while
channelling), so this matters only where a camp tile lies within 1 of an altar. There, starting the tribute with a
small bag the turn before a capture pays banks the payout one turn after it lands, whatever its size. This follows
from the YAML text but is unverified: it needs a probe before use. 12.1 likewise rests on the YAML respawn rule.

# Part 5: farming, items and draft (exact solvers, checked against ladder data)

## 13. Camps as an exact optimisation

**13.1 Exact clear fronts.** A camp clear is a deterministic single-player game: champion position, both cooldowns,
the group's sleep state (asleep / awake with 0 or 1 quiet phases), Varg's shield, each member's HP. A DP over that state
gives the full Pareto front of (rounds T, damage taken D) per champion × camp type × shard level (validated: 1D ring model
= 2D map model for 5 champions; hand checks). The cost of a plan is T + λD, with λ the price of health (13.3). morgana
prices clears with averaged formulas (`output` spreads spells over the cooldown; `min_camp_damage` = ceil(hp/strength)
face to face; `spell_clear_rounds` spell-only kiting). Against the exact optimum these overprice the clear cost by:
wolf Ren +51%, Varg +39%, Tavi +27%, Stellar +25%, Ryth +21%; elk Varg +68%, Ren +67%, Cassi/Tavi +28%; groups 2-3x for
Varg and Ren (e.g. solo WW: Varg exact 36 vs bot 102). Sources: spells fire in rounds 1-2, not uniformly; stuns, Varg's
shield (Varg's wolf damage: exact 160 vs bot 460) and Ren's reflection are ignored; and melee mixed plans are
missing: dash/stun/shield windows plus the sleep rule give cheap or zero-damage clears (Ren elk: 89 rounds with no damage
vs the bot's spell-only 154).
**13.2 Kill order.** Face to face, D = Σ σ_i (C_i - 1): single-machine weighted completion time, so σ/hp descending
(Smith) is optimal by exchange. That is `min_camp_damage`'s sort. Brute force: optimal in 173/176 ladder groups (the 3
failures are Varg splash: target the member with the most live attacker neighbours).
**13.3 Health is priced exactly by the heal trip.** Camps never regenerate and an abandoned group sleeps after 2 phases.
So a clear can be paused at the health floor, healed and resumed at no loss beyond the trip. Hence total damage ≤ (trips +
1)·U (U = usable health) and the long-run rate is max Σr / Σ(τ + λD) with λ = c_h/U, attained up to O(1) per trip:
morgana's proration (`heal_rounds`) is exactly the right form. Its inputs are not:
- c_h should be the marginal detour, recall + d(spawn, next job) - d(here, next job), and 0 when the trip also banks or
  shops; using recall + the walk out overstates λ about 1.4x;
- `owed = damage + deficit` charges the existing deficit to whichever job overflows the spare health, which overprices
  big jobs (each HP should cost λ once);
- the floor should be the absolute enemy-burst floor of 2.3/3.3 (hazard-weighted), not 0.35·H;
- the face-to-face guard (`dps·3 < recall_line`) and `affordable()` forbid exactly the big clears that pausing makes cheap.
Modelled effect of fixing them (solo farm rate): Varg +14.8%, Ryth +21.1%, Ren +17.8%, Issac +31.2%, casters +3-6%.
The elk choice between face-to-face and kiting flips for λ between 0.015 and 0.05, the realistic range, so λ matters.
**13.4 Bag size (economic order quantity).** Carrying B gems at death hazard h per round loses h·B per round in
expectation (2hB in the race, since the killer gains them). Banking costs a detour c_b. Minimising cost per gem gives
B* = ρ·sqrt(2·c_b/h): with ρ = 0.5, c_b = 40, h from morgana's own hazard table, B* ≈ 218/116/81/57 gems at 1/3/5/7
tenths of the way to the enemy spawn (÷ √2 if the killer's gain is counted), against `chain_bag_limit = 50`. In the
team LP, raising the bank size from 50 to 150 lifts team rate +18% on average.
**13.5 Surplus vs ratio (8.1).** On the ladder maps r/τ and r - ρ*τ choose a different next group in 27-43% of decisions
at ρ* = 0.3 and 4-21% at 0.45; each differing decision loses 4-30 gems of surplus (collision: a lone wolf at ratio .68
taken over EEE, 108 gems at .58).
**13.6 Crews and tanking.** The tank stands at 1, partners at 3 and take nothing (10.1). Best pairs (elk rounds, tank damage):
Varg + Stellar 17, 460; Varg + Ryth 18, 360; Varg + Ren 21, 360; Varg + Cassi 23, 420; Issac + Cassi 25, 1260 (Issac tanks for
Cassi: equal distance goes to the lower id). A Varg-led elk crew costs 25-31 champion-rounds per member vs 85-107 solo.
Crew beats splitting iff the walk to the next camp is below a threshold: elk 17-36 steps, EE 26-93, wolf 4-15.
**13.7 Stun schedule.** A stun cast at turn t cancels the camp-phase t+1 attack. k staggered stunners prevent exactly k/8
of a monster's attacks (simulated hit share .874/.745/.621/.478/.375 for k = 1..5). The meta comp has 3 stunners (Ryth,
Ren, Cassi) → hit share .625 (.594 with Varg's shield); rival's `siege_hit_share = 0.75` assumes 2. A level-0 Monolith
siege: 57 rounds, 6,650 tank damage, more than the team's 5,450 HP, so it needs a rotation; about 0.33 gems per
body-round, below wolf/elk farming.

**13.8 The head-to-head test.** The theory predicts that mispriced health pushes us onto zero-damage gem clusters and off
wolves and elk, and that the right policy spends more health, recalls more and carries bigger bags. procless (same five
champions) vs us, first 300 rounds: camp damage taken +53%, wolf gems 285 vs 176, elk 87 vs 43, gem-cluster gems 193 vs
230, recalls 23 vs 14.5, carried gem-rounds 2.27x. Every sign matches. The modelled sizes (bags +18%, health pricing
+15-30% for the melee half, crews +5-14%) add up to roughly the observed +35% production gap, though that gap was not
decomposed empirically.

## 14. Items

Buying whole emblems greedily on marginal farm rate equals the exhaustive optimum for all 9 champions tested (per-shard
greedy is not safe: the passive arrives with the 5th shard). Best three emblems: Stellar/Cassi Jungle(F), Jungle(F),
Monster(F); Prism Jungle(F), Power(F), Monster(F); Tavi Power(F), Power(F), Monster(F); Varg Jungle(S), Power(S),
Monster(S); Ryth Jungle(S), Durability(S), Monster(S); Ren Jungle(S), Durability(H), Monster(S). morgana's
Jungle → Power → Durability(H) is 10-15% below the best for Stellar, Cassi, Prism and Tavi and 2.6-7% for the melee.
Monster (+10% camp damage) is missing from the build but ranks first or second for almost everyone. `main_stat` picks
Strength for Tavi (10·2.2 < 5·5) where Focus is right. Treasure beats Power only with more than ~107 rounds left and never
beats Jungle or Monster. Durability's fight value is not in this farm-only model.
**Checked against what top teams own at round 300 (2,500 games; shard-equivalents per champion).** Partly consistent:
everyone buys Power, Jungle and Durability, and Stellar builds Focus everywhere. But (1) top teams barely buy Monster
(Fish 0.37, Univardisty 1.27, others ~0; us 0.08), so the farm-only model overrates it relative to fight stats; (2) they
build Bruiser (Health) on Ren, Ryth and Cassi (2-4.7) where we build almost none; (3) **Ren builds Focus** at the top
(Fish 9.2 Power-Focus, SBC/procless 3.3-3.5) where `main_stat` gives Ren Strength. The exact reason is Ren's passive: 0.2 x
Focus reflected per hit taken, monster hits included. Per shard, Strength adds 5 per basic attack; Focus adds
10 x (1.25/8 + 0.2·k) per round, with k hits taken per round. Focus is better once k > (5 - 1.56)/2 ≈ 1.7: a Ren tanking two
monsters, or fighting in front, should build Focus. `main_stat`'s rule (Focus iff focus.growth·Σmult > 5·strength.growth)
omits passives entirely (also Ryth's 1% health → Strength, which makes Health shards partly Strength shards).
Item choice therefore needs the fight term the econ model lacks; the farm-only ranking is an upper bound on Monster's value.

## 15. Draft

**Theorem 15.1 (no denial).** Both teams may pick the same champion and picks are revealed per round. So the draft is not a
denial game: it is a choice of composition, with information only from the enemy's earlier picks. The order of a
preference list matters only through prefixes (a 3-pick map takes the first 3). The draft bot can read the pick count
(`draft::team_size()`) and the camp groups, so neither nesting nor map-independence is forced.
**Farm value.** In the econ team LP (visit-rate variables for solo, crew and siege jobs, group visits ≤ 1/(respawn + 16),
body time ≤ 1), morgana's order is within 2.0% of the best farming composition on the ladder maps on average (max
10.3% on stampede; contest 6.1%) and 0.8% on 132 generated maps (exact on 86). Ladder data agree: the observed
best non-mirror composition at each pick count is our prefix (3: C&I + Stellar + Varg .62; 4: + Ryth .72; 5: + Ren .59). Tavi or
Prism as 5th farm slightly better than Ren, but Ren's value is in fights (the duel solver: Ren beats every champion but the
mirror from d = 4 when moving first, and kills Varg from any distance untouched).
**Use of the draft turn.** 1M fuel and 1024 bytes are enough for per-body camp assignments and per-group ward tiles
(~330k fuel for distance fields, ~260k for costs; ~470 bytes for assignments + ~4 bytes per group for wards). morgana writes
an empty DraftPlan.

# Appendix A: heuristic inventory (morgana, plus rival-only parameters)

Paths are under bots/morgana/src unless marked rival. "Exact replacement" names the computed quantity from the report
sections (§).

| # | where | constant / shortcut | what it assumes | exact replacement | evidence |
|---|---|---|---|---|---|
| 1 | params.h:12 | fixed `draft_preference` | one nested order fits every map and pick count | per pick count (`draft::team_size`) and per map composition value (§13 econ) | current order = best observed composition at every prefix (3: .62, 4: .72, 5: .59), so map-adaptive is the only open gain |
| 2 | params.h:23 | `track_horizon = 10` | after 10 rounds unseen, anywhere | exact reachable set keeps growing; drop only for fuel | — |
| 3 | params.h:28 | `recall_health_fraction = 0.35` | one health line fits camps and enemies | renewal-reward heal threshold (econ T3) + enemy burst floor max_e D_{n_e} (§2.3) | top teams' break-off is soft around .3-.5 HP, threat-adjusted |
| 4 | params.h:30 | `finish_camp_health_fraction = 0.6` | leaving a camp loses the clear | camps never regenerate: compare remaining clear damage with health above the burst floor (§8.5) | rules |
| 5 | params.h:31; bot.cpp:1070; pathing.cpp:371 | `ward_period = 20`, forward off-bush ward | scouting ward worth replacing any ward | V(w) - V(w0) over the bush threat set (§4.2, §9) | top teams 96% bush wards vs ours 34%; one approach ward covers 96% of the threat set |
| 6 | params.h:33 | `bush_watch_radius = 4` | threats from bushes within 4 | threat set B(p): bush tiles within 5 that see p (§4.2) | reach table §2.1 |
| 7 | params.h:35; bot.cpp:1347 | `shop_trip_gold = 150` | a shop trip pays at one emblem | trip iff Δρ·T_next_visit > (5 + W)·v_r (§8.4) | top teams visit spawn every 58-81 rounds; gain ≈ 3 vs cost ≈ 15 gem-eq |
| 8 | params.h:37; bot.cpp:1217 | `chase_radius = 8`, prey turns = (d - range) + hp/str | target stands still | catchable iff in R_1 now, anchored, or escape region empty (§3) | fleeing targets hit 23% vs anchored 40% |
| 9 | params.h:40 | `rally_radius = 12` | fights last ~5 rounds | join iff walk - reach < sim fight length (§7.3) | — |
| 10 | params.h:44-45 | `pickup_steps = 12`, `pickup_memory = 5` | pickups within 12 are worth it | surplus of the capture (gems + γ·gold - ρ̂·steps) like any job (§8.1) | — |
| 11 | params.h:49 | `chain_bag_limit = 50` | doubling a bag is the risk limit | chain iff v_r·T_saved > 2·B·h(x)·T_extra (§8.2); farm() already prices it | procless carries 2.27x our gem-rounds and banks more |
| 12 | params.h:53-56; bot.cpp:1115 | `pack_radius 7`, `pack_ally_radius 5`, `retreat_ratio 1.3`, `hurt 0.75` | square-law with a margin | Lanchester H·D is exact for continuous focus fire (§7.1); replace the margin by true first strike + exact sim, radii by R_m and arrival times; act on the escape region (§2.4) | rival (ratio 100 unless hurt or carrying) beats morgana-v5 |
| 13 | params.h:58; bot.cpp:1340 | `recall_heal_bonus = 6`, hurt if < 0.6 HP | a heal is worth 6 rounds | (deficit/H_usable)·(recall + W) rounds (§8.3) | — |
| 14 | safety.h:28 | `hit_given_reach = 0.25` | calibrated hit rate | keep as calibration for expected cost; use worst case only for lethality | ladder 23-27% |
| 15 | safety.h:31 | `recall_risk = 0.2` | cancel a recall at 20% hit chance | keep iff P(cancel)·(turns channelled) < cost of walking (§5) | — |
| 16 | safety.h:34 | `credible_weight = 0.5` | ignore unlikely unseen threats | weight all by probability; cutoff only for fuel | — |
| 17 | safety.h:36 | `unknown_camp_weight = 0.5` | coin flip on sleep | sleep is deterministic: asleep iff no champion within 3 for 2 camp phases; P(enemy there) from possible sets | rules |
| 18 | safety.h:38 | `fight_ally_radius = 4` | allies within 4 fight | allies with walk - reach < fight length (§7.3) | — |
| 19 | safety.cpp `strike`, `Safety::build`, `next_turn_round` | one enemy turn before ours | n_e = 1 always | n_e ∈ {0,1,2} from slots (§1.2); reach R_{n_e}, damage D_{n_e} (§2.1, App. B) | 37% of melee hits in double-move windows come from d = 3 |
| 20 | safety.cpp `trade` (they_first = true) | enemy strikes first in every fight | worst case | true first striker from positions and slots (§2.6) | killer struck first in 83% of isolated 1v1 kills; enemy-first calls 27% of actual winners lost (accuracy 78.6% vs 80.5% with the true first striker) |
| 21 | safety.cpp `Side::hurt/weakest`, self_abilities.cpp:201 | focus the weakest | equal damage rates | Smith index (δ·D_j + h_j·V_j)/p_j (§6) | example -16% damage taken |
| 22 | safety.cpp `act` | stun the strongest Strength | Strength = turn value | stun the max next-turn value (damage with ready spells, channel completion) (§6) | — |
| 23 | safety.cpp `Side::camp` | camps hit only us | — | camps hit the nearest champion of either team (§7.4) | rules |
| 24 | safety.cpp `unseen_weight` | uniform over possible tiles | — | Bayes filter over the reachable set, or calibrated | comment: in-reach 0.6-0.9x uniform |
| 25 | turn_order.cpp:20-26 | `life 300`, `gem 15`, `tribute 100`, `recall 60`, `unacted_share 0.5` | HP-point utilities | gem-eq currency (§5); exact n_e accounting (§1.3) | Fish: 12% of its hits from manufactured double moves (us 6%) |
| 26 | abilities.cpp:14-21 | `kill 300`, `gem 15`, `stun 80`, `tribute_stun 100`, `recall_cancel 60`, `min_value 40`, `keep_walk 250`, `min_camp 50` | HP-point utilities | currency (§5): kill ≈ 2,000-2,500 HP-eq + ~50 HP per carried gem each side | — |
| 27 | abilities.cpp:23 | `hold_range = 6` (no camp casts with an enemy within 6) | a fight is likely | P(fight within 8 rounds) × marginal fight value vs camp value (§11.2) | fight within 8 rounds follows 52-74% with an enemy within 6, 2-5% without: hold is right; the loss is elsewhere |
| 28 | bot.cpp farm(), lines 1009-1016 | walk, then `cast_at_camp` | casting order irrelevant | cast first when a member is within 4; pick attack tiles adjacent to more live members (§11.1) | our Ren/Ryth walk on 43-49% of ready farming turns (procless 7-8%) and cannot cast |
| 29 | self_abilities.cpp:17 | `reset_hold_margin = 2` | hold resets near enemies | same option-value rule as spells (§11.3) | reset on camps 72% vs top 85% |
| 30 | self_abilities.cpp:18 | `travel_dash_clearance = 10` | keep dash near enemies | dash for travel iff saved steps·v_r > P(dash needed within 8 rounds)·value (escape/engage) | — |
| 31 | self_abilities.cpp:19-20 | `heal_min_share 0.6`, `heal_low_health 0.5` | heal efficiency floor | heal value = min(heal, deficit)·δ + kill-prevention vs option value | — |
| 32 | self_abilities.cpp:22-23 | `dash_min_health 0.5`, `chase_health 0.4` | dash in only when healthy | dash in iff kill achievable before escape and post-dash I(x) < health (§2.3) | — |
| 33 | self_abilities.cpp `danger()` | depth-weighted danger score | — | exact exposure I(x) (§2.3) | — |
| 34 | bot.cpp:23-26 | `endgame_horizon 400`, `margin 20`, `slack 2`, `shop_rounds 100` | — | hitting-time race (§8.6) | — |
| 35 | bot.cpp:352 | `stickiness = 1.2` | hysteresis | explicit switching cost (walk) in the surplus index | — |
| 36 | bot.cpp:356 | `death_hazard` table | calibrated hazard by position | keep (calibration) | — |
| 37 | bot.cpp:65 | `main_stat`: Focus iff focus.growth·Σmult > 5·strength.growth | burst horizon of 5 attacks | marginal damage per shard including passives: Ren Focus iff hits taken per round > 1.7; Tavi Focus (§14) | top teams build Focus Ren (Fish 9.2 Power-Focus); we build Strength |
| 38 | bot.cpp:85 | Jungle → Power → Durability | — | greedy on marginal rate per gold (econ T4) | — |
| 39 | bot.cpp:878 | skip if 4·wait > respawn | waits are bad | surplus with ρ̂ prices waits correctly (§8.1) | pricing waits as rounds lost games under the ratio rule |
| 40 | bot.cpp:936 | face to face only if dps·3 (melee) or ·2 < recall line | — | exact clear damage (Smith order) vs health budget (econ T1/T3) | procless takes 53% more camp damage and captures 28% more |
| 41 | bot.cpp:974 `worth` | ratio objective | — | surplus r - ρ̂·τ (§8.1) | — |
| 42 | farm()/attack tiles | no tank coordination | — | nearest-champion assignment (§10) | top: highest-HP takes 60% of camp damage, us 42% |
| rival 1 | rival params.h | `camp_risk 0.35` | bolder camp choice | heal-trip pricing (§8.3, econ T3) | — |
| rival 2 | rival params.h | `home_power 2` | enemy-ground discount | hazard × death cost (morgana's form) | — |
| rival 3 | rival params.h | `help_radius 8` | — | arrival vs remaining clear time | — |
| rival 4 | rival params.h | `close_margin 60`, `enemy_close 100` | — | hitting-time race (§8.6) | — |
| rival 5 | rival params.h | `retreat_ratio 100`, `hurt 1.3`, `brake_bag 30` | fight unless hurt/carrying | EV with 2B·p bag term (§7.2) | — |
| rival 6 | rival params.h | `max_wait 10`, `clear_share 0.15` | — | surplus; f_c from own cycle | — |
| rival 7 | rival params.h | siege: `hit_share .75`, `pool_share .6`, slack 1.3, waits, `heal_fraction .6` | — | exact stun schedule min(k,8)/8 and tank rotation (econ) | — |
| rival 8 | rival params.h | `big_gems 150`, `big_holders 3` | — | parallel tribute G/(10k) (§8.7) | — |

# Appendix B: exact m-turn damage D_m(champion, d)

Base stats, both slots ready, stationary target at Chebyshev distance d, open ground; brute force over legal per-turn plans (dtable.py). Use with m = n_e (enemy turns before our next turn: 0, 1 or 2). With slots on cooldown the entries fall to the basic-attack values. Varg's shield, Ren's retaliation and items are not included.

```
D_1(d): max damage within 1 own turn(s), both slots ready, base stats
champion  d=1    d=2    d=3    d=4    d=5    d=6    d=7   
Ryth         150    100    100    100    100      0      0
Varg         100    100      0      0      0      0      0
Ren          165    125    125    125      0      0      0
Issac         80     80     40     40      0      0      0
Vendetta     140    140     70     70      0      0      0
Marcella     145    100    100    100      0      0      0
Cassi        170    170    170    140      0      0      0
Stellar      235    235    235    200    140      0      0
Prism        155    155    155    120     80      0      0
Tavi         255    255    255    220      0      0      0
Willow        90     90     90     45      0      0      0
Vesper        90     90     90     45     45      0      0

D_2(d): max damage within 2 own turn(s), both slots ready, base stats
champion  d=1    d=2    d=3    d=4    d=5    d=6    d=7   
Ryth         250    250    100    100    100    100      0
Varg         150    150    100      0      0      0      0
Ren          205    205    205    205    125    125    125
Issac        120    120    120    120     80      0      0
Vendetta     210    210    210    210    140      0      0
Marcella     235    235    100    100    100      0      0
Cassi        200    200    200    170    140      0      0
Stellar      410    410    410    340    200    140      0
Prism        270    270    270    200    120     80      0
Tavi         325    325    325    290    220      0      0
Willow       135    135    135     90     45      0      0
Vesper       135    135    135    135    135     90     45

```

# Appendix C: data, scripts and sub-reports

All measurements use replays/.analysis (tools/replay/extract.mjs) of ladder games since 2026-10-16 unless stated.
Bots are deterministic and teams meet repeatedly: judge samples by ladder groups (5-game sets), not by turn counts.

Scripts (in `scripts/`; run with `py`, paths point at replays/.analysis):
- turnreach.py / turnreach2.py: slot model check against every champion event; distance at the victim's previous turn end vs
  attacker turns in between (n), double-move shares, kill conversion.
- bushhits.py: hits on bush-standing victims and who could see them.
- rates.py, walk.py: production, gold, deaths per pick-round; walking distances spawn -> groups.
- deathaudit.py: exact escape BFS at the first sighting of the killer, point of no return.
- firststrike.py, pairkills.py: isolated 1v1 kills: first striker, pair balance.
- h2h_econ.py: production breakdown in head-to-head games.
- spellwaste*.py, spellhold*.py: spell casts while farming, with/without enemies, walked vs still.
- chase.py: chase streak outcomes.
- wardargmax*.py: ward argmax under the uniform blind set (refuted) and the bush threat set.
- dtable.py: exact m-turn damage tables (Appendix B).

Sub-reports (in `subreports/`, with the solvers' own code in the scratchpad folders named there):
- duel.md: exact 1v1 open-ground solver (C++ + independent Python spec, 0 mismatches over all cross-checks): kiting,
  standoffs, first strike, duel tables, greedy casting, closed-form escape, 2v2 target order.
- econ.md: exact camp-clear DP (Pareto fronts), Smith check, renewal-reward health pricing, EOQ banking, surplus vs ratio,
  crews, stun schedules, item optimisation, team farming LP and draft.
- replay.md: top-team micro measurements (spacing, retreat, ability timing, focus fire, wards, bushes, priority, camps).
- fightmodel.md: morgana's Trade sim ported and scored against 9,756 decided ladder fights under enemy-first, true first
  striker, slot-level order, Smith targeting and Lanchester.
