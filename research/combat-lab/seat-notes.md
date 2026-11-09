# Seating engaged flee/chase pairs (notes, 2026-11-08)

Copy: `bots/variants/cl2-seat` (from `variants/cl2-belief` = oc-cl2-base + the heal_if_home belief fix). Reference
for every A/B: `variants/oc-cl2-base`, `--no-test-draft`, suite `maps/suites/merged/cl2-dev`. Scripts: scratchpad
`ana/doubles.py` (pursued flee episodes with each boundary's turn order, from `narrative.game.View.slots`),
`ana/tab2.py` (stratified tables), `ana/feas.py`.

## Falsification (cl2-belief-v1's 1,000 kept games, both sides ~ the base)

Episodes: flee.py's (a champion under 50% steps homeward with an enemy within 5), pursued only (nearest enemy within 4
on 2 of the next 3 rounds): 10,876. A boundary R→R+1 is a double for X of the pair when X acts after the other in R
and before it in R+1. Outcome over 20 rounds: caught (killed by a champion), home.

Patterns over the first 3 boundaries: FPF 3,394, PFP 3,189 (alternating doubles, AABB), no double 712. The
alternating pattern is the default: for one pair, a team's champion acts first in a round it starts unless it is
ranked strictly below the other's, so equal ranks (both contact extremes, or both idle-late by 293's nearness) give
each side the double into the rounds its team starts. Each double one side gets is followed by one for the other at
the pair's next change of order: only the phase can be chosen.

Owner of the first boundary's double (k = 0), gap just before the double's first turn, stratified by pursuer kind
(melee, melee dasher, ranged) and the fleer's health quarter; P minus F, 95% CI:

| gap | caught P − F | home P − F | n P / F |
|---|---|---|---|
| 1 | +6.9 ±4.6 | −5.6 | 523 / 2,041 |
| 2 | +11.4 ±4.5 | −6.9 | 1,159 / 660 |
| 3 | +11.5 ±4.5 | −0.3 | 715 / 1,163 |
| 4 | +12.9 ±5.9 | +0.8 | 968 / 256 |
| 5 | −6.5 ±9.1 | +13.7 | 531 / 113 |
| 3-5 | **+9.4 ±3.3** | +2.0 | 2,214 / 1,532 |
| 2-5 | +10.1 ±2.7 | −1.3 | 3,373 / 2,192 |

- Split by whether the double's owner sat top of its team in R+1 (so the other could not have gone before it):
  pinned (top) +4.4 ±5.8 at 3-5; **not top +9.3 ±4.4** at 3-5 (+20 at 2, +16 at 3). The doubles that idle seating
  hands out are the ones that matter, and they are the deniable ones: 55-65% of first doubles at gaps 3-5 went to a
  champion not at its team's top, so the other could have acted before it.
- Control: gap just before the double (same time point for both owners) and health quarter and pursuer kind. Gap
  measured at the round's end instead is biased (it already holds the double's first move, a step nearer for P,
  farther for F) and reads +4.7 ±2.8 at 3-5.
- Over the 3-point bar: go on.

## Mechanism (v1)

For an engaged pair, the only choice our priority makes is whether we act before the enemy next round ("ahead") or
after it. With f(R) known (whether it has acted this round before us) and g the gap at our turn's end, the pair's
turns until our next are:
- it has acted: ahead = us, it (our double); behind = it, us.
- it has not: ahead = it, us, it; behind = it, it, us (its double).

On a 1-D gap with equal walks (the fleer steps away, the pursuer closes or strikes), ahead is never worse for us in
either role, and it decides a blow only at one gap: r = the next turn's real one-turn reach (`Strike::reach`: walk,
dash, attack reset, spells and stuns at their ranges, cooldowns by round):
- we flee, it pursues: it has acted, g = r(it); it has not, g ∈ {r(it), r(it) + 1} (its double walks then strikes,
  or strikes twice).
- we pursue our prey: it has acted, g = r(us); it has not, g + 1 = r(us).

Off those gaps the base's order stays (464 contact, late, idle): 464's alternating doubles beat the old
always-first danger order by ~2.5 points, so ahead is taken only where it decides a blow.

- **Ahead** is the contact seat for our start (contact_first + j, 464's threat level).
- **Rounds we start:** that seat is first, as 464 already gives a pair in its fixed reach; new only for pairs
  outside it (idle seats).
- **Rounds they start:** 464 seats us last; ahead needs our rank above its. Taken only when feasible:
  - it has acted: its next priority is final, so its rank is exact (`enemy_next_rank`, `can_act_before`);
  - it has not: predicted. Pinned (rank 0) when 464 will put it in contact after its move (pursuer a step nearer,
    fleer a step farther, inside the fixed 3/2 reach of either), or when its last read rank is 0; else its last
    read rank.
- **Engaged:** we flee = this turn's decision is retreat (want_home); the enemy's next turn reaches us within two
  turns. We pursue = we chased it this turn (the chase branch's prey), or struck it while it is under half health
  and not beside us (not a standing trade). Standing trades keep 464.
- **Interactions:**
  - Kill, heal and channel bands are untouched and outrank it; `follow::binding` reads the bid, not the seat.
  - Allies: several engaged allies share the contact seats, ordered by j as 464; an ally's ahead seat pushes ours
    down a rank, which can lose feasibility in their rounds (accepted).
  - Cassi+Issac: each body is its own pair; unequal team sizes go through `next_slot`.
  - Out of fuel: inside set_turn_order's fuel gate; the extra work is a few reach reads (memoised strikes).
  - The opponent seating by 464: in their rounds it pins its contact pairs at rank 0, which the feasibility
    prediction reads; in ours its contact seat is last, so ahead always holds there.

## Results

| Round | What | cl2-dev win % (20,480) | OOF cand / ref | Notes |
|---|---|---|---|---|
| v1 (`cl2-seat`) | ahead for decisive pairs; their rounds only when feasible, unacted enemies pinned by a distance prediction | **50.7 (50.0-51.4)** | 210,080 / 205,129 (+2.4%) | level; paired per map against cl2-belief +0.56 ±0.69 |
| v3 (`cl2-seat3`) | v1 + no pin prediction + bursts (hurt fleers, pursuers) + channel/stun check | **50.1 (49.4-50.7)** | 210,420 / 205,646 (+2.3%) | level; paired per map against v1 −0.66 ±0.85, against cl2-belief −0.10 ±0.70 |
| v2 (`cl2-seat2`) | v1 without the pin prediction, plus the auditor's fixes | 50.3 ±1.0 of 8,795 (stopped) | | **bugged, a no-op**: its "our next turn is a channel" check read the turn end's recall feint, which nearly every turn starts, so the seat almost never fired (round 3's debug batch: 74 fires in 300 games, none fleeing). Not a test of the pin. |

### v1 diagnosis (debug batch, 300 games on 150 cl2-dev maps; kept 1,000 release games)
- Fires: fleeing 30 a game in our rounds (no change from 464 there, mostly), 18 in theirs; chasing 14 / 1.6.
- Achieved: in their rounds the seat put us before the enemy 92% of the time it fired (4,714 of 5,124 unacted).
- The pin prediction was wrong about half the time: of the decisive pairs it skipped as pinned, the enemy did not
  take its team's first seat in 7,400 of 12,600 (fleeing, gaps 3-6); its last read rank did not predict it either (a
  read 0 was not first next round 75% of the time).
- Kept games (the 1,000 first to finish, short-game heavy, 55% won): our fleers caught 29.0% against the base's
  31.8%, by dashing melee pursuers 29.5% vs 32.6%; boundaries giving the pursuer a double 37.7% vs 40.2% there.
  Kills 10.98 vs 10.22 a game. The full A/B moved only half a point.

### v3 (`cl2-seat3`): what changed from v1
- No pin prediction: in their rounds an unacted enemy is assumed at rank max(1, last read rank) and we try; an
  acted one (or a team that never changes priority) is read exactly.
- Bursts: a hurt (< 50%) fleer also takes ahead whenever the pursuer's next turn reaches it (its double would strike
  twice in a row), not only at the boundary gap; a pursuer takes ahead whenever the prey is in its reach after the
  prey's step (unacted: g + 1 <= r; acted, our double: g <= r + 1). Healthy retreats keep v1's boundary rule.
- No seat while a tribute or teleport channel or a stun holds our next turn (the recall feint is ignored).
- Debug fires (300 games): their rounds, fleeing 34 a game (ahead achieved 70%), hurt fleeing 12 (60%), chasing
  11 (41%); our rounds, chasing with the prey already acted 38 a game.

### v3 diagnosis and conclusion
- Kept games (first 1,000 to finish): our fleers caught 28.5% against the base's 29.8%; alternating-free (ABAB)
  starts 1,590 for our fleers against 966, so the denials happen. But as pursuers the extra ahead seats turn the
  prey's alternating pattern into ABAB too, which removes our own pursuit doubles: the base's fleers got fewer
  first doubles against us (3,534 vs 3,881 F-first) yet were caught no more often (29.8%).
- Why neither round moved the A/B: the seat works as designed (ahead achieved 70-92% when tried) and shifts flee
  outcomes by 1-3 points in short games, which is ~0.1-0.3 kills a game, below the A/B's resolution. Ahead in their
  rounds also gives up 464's double for us at the next boundary, and moves us before every other enemy and ally;
  the 1-D pair model prices neither. v3's wider firing (no pin, bursts) cost what v1 gained.
- Stopped after 3 rounds, best v1 at 50.7 (+0.56 ±0.69 paired over cl2-belief): not a stackable gain.
- Untested leads: the pin prediction is the weak link of v1 (half wrong); an exact read is possible only for an
  enemy that has acted, so a cleaner test is v1 restricted to acted enemies in their rounds. A pair model that prices
  the next boundary's double (two boundaries ahead) would say when giving up 464's double is worth it.

## Round 4 (2026-11-09): on cl2-stack1 (belief + seat v1 + team2c's chase bit)

Copies: `variants/cl2-seat4` (r1), `variants/cl2-seat4r2` (r2). Reference `variants/oc-cl2-base`, cl2-dev, 20,480
games, `--no-test-draft`; paired per map against cl2-stack1's own cl2-dev log (51.2, 50.5-51.8). Scratchpad
`seat4/`: `seatcheck4.py` (SEAT / SEATSKIP lines against the replay's real order next round), `pairsim.py` (the v4
run for simple kinds).

### r1 (`cl2-seat4`): exact rank only
In their rounds the seat fires only against an enemy that has acted (or whose team never changes priority), so its
next rank is final; the pin prediction and the unacted fires are gone. Our rounds as v1.
- Debug batch (300 games, scratchpad `seatdbg`): SEAT's "ahead" matched the real order next round 95-99% in every
  class (their rounds, acted: 99.2% of 507). Fires a game: our rounds 18.3 fleeing acted, 7.2 fleeing unacted, 13.4 /
  1.0 chasing; their rounds 1.3 fleeing, 0.4 chasing. Skipped (unacted, their rounds) 33.2 fleeing and 7.4 chasing a
  game; under 464 we were before that enemy anyway in 19% / 9% of those.
- A/B: **50.2 (49.5-50.8)**, OOF 214,556 / 206,374; paired per map against stack1 **−1.01 ±0.82**. A dip.
- Why (1,000 kept games each, `ana/doubles.py`): our fleers were caught 30.1% against stack1's 28.6%; episodes with
  no double at the first boundary fell from 25.6% to 21.9% and pursuer-first rose from 36.3% to 37.4%; the base's
  fleers were caught 30.0% against 31.4% by stack1's pursuers. v1's predicted fires against unacted enemies were
  real denials (92% achieved), and its half-wrong pin errs toward skipping, which costs little. Exact-only drops
  about 17 denials a game and the point they were worth.

## v4 model (written before its games)

For an engaged pair (us X, enemy Y) our next priority only picks the order of X and Y in round R+1. 464 seats the
round after (R+2) by its starter, the team that started R: in our rounds our contact seat is first, in theirs the
enemy's is. So both orders lead to the same multiset of pair turns over
`[Y(R) if Y has not acted] · {X, Y in R+1, in the chosen order} · R+2 starter's, the other's · R+3 starter's first`,
the last being the team that starts R+1. Ahead denies one double and gives up the next one: the window holds both
boundaries, so the run prices the lost double instead of assuming it away.

- **Run:** 1-D gap. The fleer steps away (+1). The pursuer strikes when its real one-turn reach covers the gap
  (`strike_with` over the slots ready that round and not spent earlier in the run; one cast a turn, the fewest slots
  that land the same blow), else walks in (−1). After a strike it stands at its attack range when it had to move
  (walked or dashed), one step nearer after a reset or spell. A stun takes the victim's next turn.
- **Discount:** a blow k rounds on counts 0.8^k (chases end: home, help, a pursuer turning back). Undiscounted, every
  ranged pursuer ties (walking spends its attack, so the double only moves a blow to a later turn).
- **Value:** fleeing, the damage we take from every pursuer we pass, plus a life (max health, one round discounted)
  when the window's undiscounted total reaches our health and shield; chasing, the damage we deal the prey, plus its
  life when the total reaches its health. Ahead iff that sum is better by > 0.01 and some passed enemy favours it.
- **What it reproduces** (`pairsim.py`, melee reach 2, dash melee 4/2, ranged 3, ranged with reset 4): for melee
  and dashers ahead gains exactly at v1's gap (fleeing r+1 unacted, r acted; chasing g+1 = r unacted, g = r acted)
  and loses at the one or two gaps nearer (the burst gaps v3 fired at, which lost); ranged pursuers gain 0.16-0.29 a
  blow at gaps 3-4. So the lost next double is already outweighed at v1's gaps; v4's changes from v1 come from real
  reach by round (cooldowns spent in the window), stuns, life thresholds, ranged pairs and summing every enemy passed.
- **Who we pass:** our rounds, every enemy (the contact seat is first, as v1). Their rounds: an acted enemy by its
  final rank (`can_act_before`); one yet to act by v1's prediction (pinned when its move leaves us or an ally in
  464's contact, or its last read rank is 0; else its last read rank). r1 showed the predicted fires were worth about
  a point, so they stay.
- **Second-order effects:**
  - Other enemies: ahead moves us before every enemy we pass, not just the decider. v1 priced only the first decisive
    pair; v4 sums the run over each passed enemy (fleeing: all within reach + 1; chasing: only struck prey, so a
    third enemy hitting the pursuer is not priced) and the life term over their summed blows.
  - Allies' seats: the ahead seat is the contact seat for our start (contact_first + j), so it pushes allies below j
    down a rank. In their rounds that can move an ally after one more enemy, unpriced (as v1). Several engaged allies
    still order by j.
  - Kill-bid band: kill, heal, protect (escape) and channel bids outrank the seat and are untouched; a fleer whose
    death is certain whatever the order is in offer_escape's protect band, so the life term matters mostly for
    pursuers and for blows that kill only with the double. `follow::binding` reads the bid, not the seat.

### r2 (`cl2-seat4r2`): v4 model, on stack1 (v1's prediction kept for unacted enemies)
- Implementation: `seat_priority` runs the pair both ways per passed enemy (`PairRun`, `run_pair`); strikes by slot
  mask from safety's strike memo (`strike_slots`); enemies whose max reach cannot meet the gap in the window are
  skipped; stops pricing below end_reserve + 8k fuel (it costs 1.1k a call on average, 9k at p99, 22k at most).
- Debug batch (300 games): fires a game, our rounds 16.9 fleeing acted, 13.5 fleeing unacted, 14.6 / 1.0 chasing;
  their rounds 17.3 fleeing unacted, 1.1 acted, 1.4 / 0.4 chasing: about v1's rates. "Ahead" matched the real
  order: our rounds 95-98%; their rounds acted 92-98%, unacted 88% fleeing, 80% chasing.
- A/B: **51.3 (50.6-51.9)**, OOF 215,031 / 205,315 (+4.7%, as stack1's +5%); paired per map against stack1
  **+0.10 ±0.70**. Level with stack1.
- Why level: the model agrees with v1 where it matters. Its runs for melee and dashers pick exactly v1's gap, and
  the lost next double never outweighs the decided blow there. Its changes (ranged pairs at gaps 3-4, cooldowns spent
  in the window, stuns, life thresholds, the sum over passed enemies) touch few decisions or decide nothing.

### Round 4 conclusion
- v1's one-gap rule is what a two-boundary pair model picks; pricing the next double adds nothing measurable.
- Exact-rank-only loses about a point: the predicted unacted fires are most of the seat's value.
- What's left is feasibility: 12% of fleeing fires in their rounds still fail, and the pin skips about 59%
  feasible cases (v1 diagnosis). Untested: fire whenever the enemy's last read rank allows it and drop only the
  distance pin. v2 meant to test that but was bugged, and v3 mixed it with bursts.
