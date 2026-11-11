# T8: breaking a lockout is a team objective (candidate `bots/variants/macro2-lock`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/ocean-ref-b7c87cf` to `variants/macro2-lock`.

## Rules (cambc-rules.yaml `altar_locks`, `turn`, `shop`)
- A lock is placed from within 2 of an altar, and each team has at most one lock per altar. It blocks only the
  other team's tributes and cancels every tribute channel at that altar when placed.
- Five basic attacks remove a lock. Spells don't. An enemy tribute attempt at a locked altar counts as one of the
  attacks. Locks never expire. Melee basic range is 1 and ranged is 3. A ranged champion's walk or attack spends
  both, while melee walks and attacks independently.
- A lock costs 10 gold and a champion carries at most 1, bought on its own spawn.

## Evidence (256 distinct mirror games of ref vs ref; replay-watcher report)
- 63 of the 256 games have one altar. In 44 of them the eventual loser was locked out of every altar at least 50
  rounds longer than the winner; the reverse happened in 5. Examples:
  - gen-colosseum game 1ccbb262: A locked the only altar at r168, and the lock stood untouched until r283. B's
    tributed total stayed at 212 from r150 past r400. B's Ryth, carrying 39 gems, cycled bank walk / retreat
    (branches B/R) for 120 rounds 3-8 tiles from the altar and never hit the lock. By contrast, A broke B's
    earlier lock within 13 rounds of starting on it.
  - gen-monolith game 57dcf4f3: B's lock at (15,15) from r153 was never broken. A's champions arrived one at a time
    against five, then made B/R walks with 32-gem bags as close as 1 tile from the lock, and died with the bags.
  - mut-meander game 16a9098e: A locked 3 of 4 altars. B's Vesper, carrying 82 gems, flipped B/R five times beside
    the locked middle altars and was killed. B's other three champions kept farming 6 tiles away.
- B/R oscillation (4+ flips in 30 rounds): 1711 episodes in 203 games, split evenly between the sides. 99 loser
  episodes ended in death within 15 rounds, against 35 for the winner.
- Ref code: a lock is hit only when a bank walk happens to end in attack range of it (`break_lock` and
  `lock_hit_ends_turn` in economy/bank.cc ~1100-1180; `lock_turns` prices it for the walk). Retreat then fires
  near the guarded altar, and the walk flips back and forth. Locks are bought and placed by `buy_lock` (shop.cc,
  bot.cc:330) and `place_lock` (bank.cc:52), and guarded by economy/altar_guard.cc.

## Principle
Our team's score rate is zero while every altar we can reach carries an enemy lock: every gem carried or farmed
waits on that lock. Breaking it needs five basic attacks in total, so k champions in range break it in ceil(5/k) of
their turns. A lone carrier that walks up and leaves achieves nothing and risks its bag. Breaking the lock is
therefore a team task with a known cost (the walk there plus ceil(5/k) attack turns) and a known value (the team's
whole banked flow resumes). It should be done together, by champions that can hit it, and carriers shouldn't walk a
bag up to a lock they can't break.

## What to build (bounded)
1. **Lockout state** (team-shared, recomputed each round from the existing altar beliefs, `world.altars[a]`
   `enemy_lock`/`enemy_lock_hits`): we are locked out when every altar our bankers could use carries a believed
   live enemy lock. Reuse the existing reachability and altar lists in bank.cc; don't invent a new altar model.
2. **Siege task:** while locked out and our team has gems to bank (carried by anyone, or a Prism retaining a
   bag), pick the lock with the lowest team cost (walk plus attack turns, as `lock_turns` already prices). Send
   the nearest available champions that can attack it there:
   - Exclude anyone channelling, recalling or dead.
   - Exclude Willow if ocean's support code needs her elsewhere. Otherwise she can hit too.
   - Take as many as it takes to break the lock within about one turn of arrival, up to the whole team, nearest
     first.
   - Let them stand on the tiles within their attack range of the lock (ranged 3, melee 1), and hit it each turn
     until it's gone.
   Wire this in like the existing branches. An economic objective in `decide` (bot.cc) or the farm's target
   selection both work; pick whichever is cleaner and say which you chose. Use the existing pathing and step code.
3. **Safety stays:** the siege goes through the existing step guard, lethal checks and stand test. Don't override
   them. The intended gain is that attackers arrive together, so the stand test counts them as a roster, and that
   no one wanders up alone. If the stand test sends attackers home, accept it. A champion near the lock may wait at
   the edge of the enemy's reach until the others arrive (reuse any existing gathering or formation code; don't
   write a new one).
4. **Carriers wait:** while locked out, a carrier stops bank-walking toward a locked altar unless it is one of the
   assigned breakers. It keeps farming, or holds its bag at a safe tile. Stopping the B/R oscillation on locked
   altars is the second gain.
5. **Keep:** `place_lock`, altar guarding, bank walks to unlocked altars, the draft, emblems, and everything else.
   When not locked out, behaviour should be identical to ref.
6. **No new tuned constants.** Derive from the rules: 5 hits, attack ranges, and the walk/attack spend rules.

## Check
Trace `SIEGE round handle altar role(breaker|wait) hits_left` with debug_block. Build. Play 2-3 local games against
ref on one-altar maps: find maps whose map file has one altar, in /home/ubuntu/wt/macro2-maps/s-200001 (e.g.
gen-colosseum, gen-monolith) or among the `maps/` ladder maps. Report how long each side was locked out (rounds with
all altars enemy-locked) against ref in the same seat. Audit and report as common.md says.
