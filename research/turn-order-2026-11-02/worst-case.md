# Worst-case enemy order (`ast-wc`) and the adversarial sparring bot (`ast-adv`)

Both are astraeus at e9c37971 (frozen as `bots/variants/astraeus-e9c3797`). Direction is in
[TODO.md](../hyperion/TODO.md) "Turn order and ally coordination".

## The model: `model/enemy_order.{h,cc}` (new, in `unity.cpp` after `turn_order.cc`)

Enemies may set any priority at any turn (rules `rounds.team_order`), so no enemy order is assumed. Relaxed only
where the rules force it. `enemy_order(world)` is worked out once per World update (keyed by round and
`observations`):

- **Settled** (`EnemyOrder::settled`): visible, acted this round, priority read this round (after its turn). Only
  a settled enemy's next priority is final. Its next-round rank lies in `[earliest, latest]`: `earliest` = settled
  enemies above it, `latest` = that + the unsettled count (unsettled ones may insert above, which only pushes it
  later). An unsettled enemy: `[0, n-1]`. Beyond next round, any rank.
- **Permutation**: `enemies_before(slot, r)` = the enemy turns before a slot of ours, so the most enemies that can
  act before it (k at our rank k in a round we start, k+1 in one they start; a larger team's extras last, as in
  `World::slot`). Dead and stunned enemies hold their slots.
- **This round**: `unseen_after` = enemy turns after ours this round not held by a visible enemy yet to act.
  `may_act_after_us(e)`: a visible enemy by its `acted` flag; an unseen one while `unseen_after > 0`.
- **Second turn before ours** (`first_next`, Safety only): each live enemy whose earliest slot next round is before
  ours could be the one, but no more than `enemies_before(our next slot)` can be. Those surely before us
  (`latest` slot before ours) take their places; the nearest of the rest (to our turn's start, strongest first at a
  distance) take what's left. The last-read ranks used before were a permutation too, so this keeps the old count
  of second-turn threats, with the nearest threats chosen instead of the ones whose stale ranks put them first.
  Without this bound, out-of-fuel turns rose 27% (below).
- Helpers: `team_slot`, `earliest_slot`, `latest_slot`, `first_next_round`.

"Worst case" depends on the question:
- The relevant enemy acts first, at its **earliest**: our kill, escape or channel, and an enemy channel completing.
- It acts last, at its **latest**: anything that must land after its turn (a camp's tie hit sparing us, an ally
  still blocking its dash).

## Changes in `ast-wc` (file: function)

- `model/turn_order.cc`:
  - `enemy_next_rank` returns the model's `earliest`. This removes the persistence fallback
    (`!world.enemy_priorities_change` made every enemy settled until one was seen changing).
    `World::enemy_priorities_change` is now read nowhere; it is still set by `read_priorities` and left there for
    an easy merge. `can_act_before`, `offer_channel`, `offer_heal` and `side_damage`'s `before` take the new ranks
    through `enemy_next_rank` unchanged.
  - `offer_kills`: **fork**. With n targets in our strike's reach (not on their spawn), we bid kill at the least
    of their values if, at the slot that bid gives us, more of them are killable (`side_damage` with `before` = our
    slot) than enemy turns before that slot. A single target that can act first can escape, but two can't both act
    first. It is skipped when a single kill bid already covers that value. It is rare: 6 new offers against 158
    single kill bids in 26 traced games.
- `model/safety.cc`:
  - `next_turn_round`: an unseen enemy has a turn left this round while `may_act_after_us` (was its last-read rank
    this round, whose priority may have changed unseen). Allies unchanged.
  - `turns_before_ours`: enemies: this-round term by `may_act_after_us`, next-round term by `first_next_round`.
    Our own next slot is still `world.slot(me, round + 1)` (the seat agent changes how it's chosen).
  - Camp tie ranks (`o.first` in the camp-strikers pass): an enemy spares us a tie hit only at its `latest` slot.
  - `Reach::build`'s dash blockers (`last_slot`): an enemy at its `latest` slot next round, so fewer allies count as
    standing still through its dash.
- `combat/plan.cc` `Search::find_wakers`: an enemy takes a woken camp's tie hit only at its `latest` slot.
- `combat/fight.cc` `last_round_before_channel_ends` and `turn_start` (used by `stoppable_winning_tribute`,
  `ally_stops` and `game_ender`): an enemy's channel completes at its `earliest` slot in later rounds.

### Consumers of `turns_before_ours` / `next_turn_round`, judged

- `threat_strike` (two-turn widening), `Reach::build`'s `twice`, and `offer_escape` / `may_escape` /
  `offer_channel`'s `< 2`: questions about our safety, so the enemy at its earliest is right. Bounded by
  `first_next` (permutation).
- Stun control: `plan.cc` `drop_stun` (`== 1`), and `abilities.cc` escape proofs (`turns_before_ours != 1`,
  `controls`). The question is whether a stun removes the enemy's only turn before ours. Worst case (2 turns, so
  the stun doesn't stop the blow) is right for the escape proofs, which must be proofs. For `drop_stun`, a value,
  it is conservative: it counts the stun's worth as nothing whenever the enemy may get a second turn. An expected
  value would be truer here, e.g. stun worth times the chance the enemy is not among the first.
- `damage_bound` / `bound().doubled` / `damage_ceiling` with `double_unacted` double every visible unacted
  enemy's blow whatever the order, and that blow is already widened to two turns when `turns_before_ours >= 2`.
  So it counts a two-turn blow twice. This was already true before for enemies whose last-read rank came first;
  now it applies to the `first_next` set. `offer_escape` guards against it (`turns_before_ours < 2`); these don't.
  **Not changed** (it changes HomeWalk, `recovered_for_work` and the retreat). Next: double only when
  `turns_before_ours(e) < 2`.
- `make_fighter` (`next_turn_round` for enemies): an unseen enemy joins from this round when it may still act.
  That's the worst case for our fights. For our chases it's neutral.
- Not changed, belief inference rather than decisions (`world.cc`): respawn dating, unseen shield and channel
  expiry, `hold_start`, and `track`'s turn counting, which already counts an unseen enemy's turn this round
  whatever its rank. Note that `track` plus the new unseen `now` term counts an unseen enemy's walk this round
  twice (its `possible` already includes it). That was already true before for enemies ranked after us.

## Results

Fastrunner native. 20 fresh suites, seeds 85000-85019 (`maps/fresh-85000` ... `-85019`), 512 games each with both
sides, 10,240 games per row. `--no-test-draft`. Run names under `replays/ab/`.

| Run | CAND win % | 95% CI | OOF turns CAND / REF |
|---|---|---|---|
| ast-wc vs astraeus-e9c3797 (`wc-final-vs-base`) | **49.6** | 48.7-50.6 | 82,575 / 72,369 (+14%) |
| ast-wc vs ast-adv (`wc-final-vs-adv`) | 49.0 | 48.0-50.0 | 85,593 / 70,134 |
| astraeus-e9c3797 vs ast-adv (`wc-base-vs-adv-final`) | 49.3 | 48.3-50.2 | 75,170 / 73,044 |

**Paired against ast-adv** (same 10,240 map/side games): ast-wc 48.99 vs baseline 49.26. The difference is
-0.26 points, 95% CI -1.47..+0.95, z -0.43. 1,984 games went ast-wc's way and 2,011 the baseline's. Level: the
adversary punishes neither.

Ablations against the baseline, same suites:

| Variant | Win % | OOF CAND / REF |
|---|---|---|
| all of it, every enemy before us that could be (no `first_next` bound) | 49.8 | 94,124 / 74,120 (+27%) |
| that, without the unseen this-round term | 50.7 | 98,263 / 76,046 (+29%) |
| that, Safety as baseline (only turn_order, camp ties, reach blockers, channel ends) | 50.3 | 79,199 / 75,860 (+4%) |
| final (`first_next` bound) | 49.6 | 82,575 / 72,369 (+14%) |
| final without the unseen this-round term | 50.3 | 84,638 / 74,562 (+13.5%) |

The win rates are level throughout (noise about ±1). The unseen term costs no fuel.

### Fuel

The rise comes from the next-round term: visible enemies counted a second turn. The bound halved it (+27% to
+14%). Debug-fuel profiles of 26 games against the baseline (100M fuel, so no shortcuts, `debug_fuel` with
sub-meters in a scratch copy) show:
- The logic costs little. `Reach` builds went +46 fuel a turn and `Safety::build` +25.
- The rest is diffuse. Turns over 85k rose 8% (19,886 against 18,353), with farm (+490 a turn on average), chase
  (+174), retreat and plan each slightly dearer.
- The bot is just in more threatened positions per turn: more tiles near the nearest enemies are threatened by a
  two-turn reach, so every Safety-guarded step does more work.
- `bench.py --set wide` (against hyperion, 100M): mean +0.9%, p99 +1.2%, turns over 100k +6%. In the 5 identical
  games total fuel was +0.05%.

There's no single function to make cheap. Options are in Next steps.

## `ast-adv`: the sparring adversary

astraeus with one change, in `turn_order.cc` `set_turn_order`. Without a band bid (kill, protect: a kill, an escape,
a heal or a channel saved by acting first), its rank is the **idle order** (`idle_priority`: health and camp ties,
which moves slowly and has nothing to do with enemies). Astraeus's **danger buckets** are gone. Near enemies, then,
a reader sees a calm, static-looking order, which changes only at the turn end where acting first wins. That is
exactly when a reader acting earlier in the round has already moved on its stale read. Dead champions keep
`dead_priority`.

A first version held a fully constant order (raw 0 by index; no idle order, no dead priority). It was **5 points
weaker** (the baseline beat it 55.1%, 54.1-56.1, `wc-base-vs-adv`): the idle order's camp-tie absorption matters.
The idle-order version is as strong as astraeus (the baseline 49.3% against it).

Why it punishes no one:
- Astraeus readers already go worst case in bids once they see any priority change, and the comms payload in every
  ally's priority changes each turn, so the flag flipped at first sight anyway.
- Only Safety's last-read next-round ranks were exploitable. Exploiting them needs a move search that puts a
  champion where a stale read believes it gets one turn before the victim's next, but it actually gets two (walk in
  after the victim moved, then bid first). astraeus has no such search.

A stronger adversary would:
- keep its priority byte-for-byte constant between band bids (move comms out of the payload), so a flag reader
  believes the order is static;
- add a "two-turn ambush" term to the move search: tiles from which its next two turns (rest of this round and,
  bidding first, next round) kill a target whose own read of us says one.

## Next steps

- **Fork-aware move search** (out of scope here). The bid fork only fires when the move already left several
  targets in reach. To make the search seek forks: in `plan.cc`'s scoring of a candidate end tile E, compute
  `m = enemies_before(our slot at the bid we would make)` once per turn, and count targets killable from E by our
  next turn plus allies before our slot (`side_damage`'s logic with `before` = our slot). If more than m are
  killable, credit the least kill value (at the unacted share where it applies), as the bid does.
  - Defensively the same rule bounds our risk: the damage at E from second turns is at most the m largest
    increments (widened minus single blow). That needs each enemy's single and widened blow at E. Strike tables
    give both without Reach, so `top-m` can replace `first_next`'s fixed nearest choice per tile at a few hundred
    fuel per tile; bound it to the tiles the search already prices.
- **Fuel**: double `double_unacted` blows only when `turns_before_ours(e) < 2` (removes the double count, fewer
  "threatened" tiles). Or choose `first_next` by threat to our current tile rather than distance (fewer widened
  enemies that never reach us).
- **Stun value** (`drop_stun`): price by whether the enemy is in `first_next`, not by "could be first".
- **Merge with ast-seat**: our next slot in `first_next`, `turns_before_ours` and the fork should use the rank
  chosen before the move once that lands; `enemy_order` keys on `world.slot(me, next)`.
- **Confirm** on suites no A/B has used (seeds 85020-85039 are still free in this workstream's range).

## Open questions

- Whether to keep the change: level at 10k (49.6, -0.4 ± 0.95) for +14% out-of-fuel turns. It is rule-derived and
  removes the persistence assumption, but it has to be traded against the fuel.
- How much the qualifier field actually reorders adversarially. Against the field's static-order bots, the old
  last-read ranks were exact and the worst case gives up some aggression.
