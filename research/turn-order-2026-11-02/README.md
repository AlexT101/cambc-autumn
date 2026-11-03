# Turn order and ally coordination (2026-11-02)

Work started from a review of astraeus at e9c37971 (frozen as `bots/variants/astraeus-e9c3797`, the baseline for
every A/B here). Direction is in [TODO.md](../hyperion/TODO.md) "Turn order and ally coordination".

## Findings of the review

- Each champion bids for next round's rank alone at its turn end (`set_turn_order`, after `act()`): kill band >
  protect band > danger > dead > idle, packed as `rank_code * 8 + (7 - index)` above a 16-bit payload.
- **No commitment between allies.** A teammate acting later this round bids for itself only (`offer_kills`,
  `can_act_before`): it never checks whether it pushes an earlier teammate, who already moved on its bid, below the
  enemy it had to beat. Kill outranks protect by band, so a kill bid can push an escaping ally under its killer.
- **Value order, not deadline order**: needs with different deadlines can all fit by deadline but not by value.
- **Rank chosen after the move**: the move search prices safety at a rank about to change ("price rank and decisions
  together", EXPERIMENTS camp-tank sequencing).
- **Enemy order assumed to persist**: `enemy_next_rank` treats every enemy as settled until one is seen changing
  (`turn_order.cc:190`), and Safety's `turns_before_ours` uses last-read enemy ranks for next round.
- **Dead allies outrank idle ones** (`dead_priority`): their slot is useless and pushes the living an alternation later.

## Guarantees the rules give

Equal team sizes: in rounds we start our rank 0 acts first; in rounds they start our last rank acts after every enemy.
At the boundary from a round they start into one we start, our last turn and our first come back to back with no
enemy turn between: one champion in both seats gets two full turns in a row whatever the enemy order. A larger team's
extra champions act last.

## Workstreams

- `ast-wc`: worst-case enemy order + adversarial-order sparring bot. Notes: [worst-case.md](worst-case.md).
- `ast-seat`: ally seat commitment, rank chosen before the move. Notes: [seat.md](seat.md).
- `ast-measure`: instrumentation and replay measurements; dead-slot A/B. Notes: [measure.md](measure.md).
- `ast-comms`: ally strike pledges in the priority payload, kept as a constraint (50.8% of 20,480). Notes: [comms.md](comms.md).

## Results

Summarised in [EXPERIMENTS.md](../EXPERIMENTS.md) "Turn order and ally coordination". The headline: idle allies nearer
an enemy acting later is ~52.0% of 27k games; seat commitment and worst-case enemy order are level and held.
`scripts/seat_check.py` rebuilds next-round orders from the seat traces to count broken commitments.
