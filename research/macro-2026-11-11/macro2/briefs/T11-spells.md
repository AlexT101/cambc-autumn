# T11: spend ready damage spells on camps (candidate `bots/variants/macro2-spells`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/ocean-ref-b7c87cf` to `variants/macro2-spells`.

## Evidence
- macro2-duelr kept the Prism's stun off camps while an enemy Prism could arrive. Prism camp stuns fell from 14-32 a
  game to 1-4, and it lost **39.3% of 10240** vs ref. Camp spell damage is therefore a large share of the economy.
  The Prism's stun does 1.5 x Focus, and its Focus grows by 1.5 per retained gem, so a big Prism bag means
  900+ damage a cast.
- Camp casts in 512 ref-vs-ref games, per champion-game, as a share of that slot's capacity (alive rounds / 8):

  | Champion | Spell | Casts | Share |
  |---|---|---|---|
  | Prism | stun | 26 | 0.28 |
  | Prism | area | 28 | 0.30 |
  | Cassi | damage | 31 | 0.32 |
  | Cassi | CC | 9 | 0.09 |
  | Marcella | damage | 15 | 0.14 |
  | Ryth | area | 21 | 0.20 |
  | Stellar | area | 14 | 0.24 |
  | Stellar | damage | 15 | 0.26 |
  | Ren | CC | 29 | 0.26 |
  | Tavi | CC | 25 | 0.24 |

  Champions are in farm branches ~59% of turns, so part of the gap is time away from camps. How much of it is ready
  spells left unused at a camp is unknown, and finding that out is step 1.
- Rules: one successful cast per turn across both slots. A slot cast in round t is ready at t+8, so a ready slot
  left unused loses its value by the round. Unit and ground abilities have range 4. `exclusive` abilities exclude
  the walk. A stunned camp skips its next attack.

## Principle
A spell's cooldown runs on the clock. A ready damage slot not cast this turn is not saved: it delays every later cast
by a turn. So the bar for casting a ready damage slot on a camp we are already fighting is low. Cast it unless:
- what it would buy is worth less than what it costs this turn: the walk it excludes, if that walk matters, or the
  basic attack, if that matters;
- an enemy-champion target could come within range before the slot is ready again, where the spell would matter
  more. Ref's existing enemy-cast logic decides that; keep it as is;
- the damage would be wasted: overkill on a camp that dies to basics anyway this turn, or a harmless group a cast
  can't advance.

## What to build (bounded)
1. **Measure first.** Add a debug trace at the end of every farm or capture turn spent at a live camp group: champion,
   each damage/CC slot's readiness, whether a cast happened, and if a ready slot was not cast, which condition in
   `camp_cast` / `cast_at_camp` / `cast_at_camp_on_approach` (combat/abilities.cc) or its callers (economy/farm.cc
   161, 834, 982, 2393, 2415; economy/capture.cc 729) rejected it. Examples: the `threshold` (cast_cost + walk for
   exclusive casts), `attackers_only`, `any_value`, the harmless-group rules, the overkill rule, the caller not
   calling at all, or the cast budget `room(cast_least...)`. Play 3 local games (stock cambc, debug, `--fuel 200000`),
   at least one with Prism drafted, and tabulate the rejections by reason and champion.
2. **Relax only the rejections the principle says are wrong.** Examples, if the data shows them:
   - a ready slot held at a camp with no enemy-champion target in prospect, judged against a threshold that prices
     the excluded walk even though the champion stands where it means to fight;
   - a caller that doesn't attempt a cast on turns it could.
   Keep the overkill and wasted-damage protections, the enemy-cast priority and all safety. Don't touch the draft or
   emblems.
3. **No new tuned constants.** Use the rules (cooldown 8, range 4, damage multipliers) and the existing measured
   cast_cost and walk prices.

## Check
Report the rejection table from step 1 (base behaviour) and the camp casts per champion-game in your candidate's
test games vs ref in the same seats. Audit and report as common.md says.
