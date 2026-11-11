# T10: relock the enemy's altars fast (candidate `bots/variants/macro2-relock`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: named by the lead
in your prompt (ref or the T8 lock-siege candidate).

## Rules (cambc-rules.yaml `altar_locks`, `turn.free`, `shop`)
- A lock is placed from within 2 tiles of an altar. Placing it is a free action: it spends no walk, attack or cast.
- It blocks only the other team's tributes. Placing it cancels every tribute channel at that altar, both teams'.
- Five basic attacks remove it. It never expires.
- A lock costs 10 gold. Each champion carries at most one, bought on its own spawn or while dead.
- A tribute channel lasts ceil(gems/10) turns, so a 400-gem bag needs 40 turns.

## Evidence (512 ref-vs-ref games)
- On one-altar maps (23% of games), after the enemy breaks our lock, ref relocks after a median 39 rounds
  (quartiles 18 and 74). The enemy tributes ~109 gems in that window, and about 2.3 tributes complete.
- Ref relocks only by accident. `place_lock` (economy/bank.cc:52) runs at every turn end for a champion that
  carries a lock and stands within 2 of an altar: first where an enemy is tributing, otherwise on our side or at the
  guarded altar. No one is sent to relock.

## Principle
While an altar the enemy can bank at has no lock of ours, every enemy bag can score there. Our relock costs one
champion's walk to within 2 tiles, and the action itself is free. It also cancels any enemy tribute in progress.
That makes an enemy tribute channel the highest-value target: the longer it is, the more rounds we have to reach
lock range before it completes.

## What to build (bounded)
1. **Relock task:** when an altar the enemy can use carries no lock of ours, a champion carrying a lock goes to
   place one. Use the existing beliefs (`world.altars[a].ally_lock`) and, as in `place_lock`, only altars ref would
   lock (`our_side` or guarded) or ones an enemy is tributing at. If those include every altar the enemy can reach,
   all of them count. Pick the champion that is nearest in steps to within 2 of that altar. Skip anyone channelling
   or carrying a bag that is better banked now, and skip it if the walk is unsafe by the existing step guard and
   stand test. It walks there, and `place_lock` places the lock on arrival.
2. **Urgency:** a visible enemy tribute channel at that altar has its turns left known. The task matters most when
   our champion can reach lock range before the channel completes. Otherwise it is an ordinary relock, worth the
   enemy's future bank flow.
3. **Restock:** a champion that relocked buys a new lock the next time it is on spawn (ref's `buy_lock` already does
   this when consumables are bought; check it).
4. **Keep:** safety (step guard, lethal, stand test), the draft, emblems, and everything else. With our locks up,
   behaviour should be identical to the base.
5. **No new tuned constants.** Use lock range 2, the channel length rule, and step counts.

## Check
Trace `RELOCK round handle altar steps enemy_channel_left`. Play 2-3 one-altar maps against ref, and report rounds
from each break of our lock to our relock (candidate vs ref seat). Audit and report as common.md says.
