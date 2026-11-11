# Brief E: Willow as a field spawn (allies price Willow's heals instead of walking home)

You are an implementation subagent for the macro4 lead. Work ONLY in /home/ubuntu/wt/macro4 (git worktree, branch
macro4-20261111). Never touch other checkouts under /home/ubuntu/wt/ or /home/ubuntu/cambc-autumn, never edit
bots/variants/ocean-ref-b7c87cf, bots/ocean, or any bots/variants/macro4-* other than your own, never write to any Claude
memory directory, never run ab.py / fgate / A/B tests, commit nothing. Read /home/ubuntu/wt/macro4/AGENTS.md and
cambc-rules.yaml first (API: docs/api/cpp.md, sdk/cpp/cambc.h).

## Candidate
`cd /home/ubuntu/wt/macro4 && ./copybot variants/macro4-hub2f variants/macro4-willow`; edit only
bots/variants/macro4-willow/src. Do not touch draft/ or emblem selection. hub2f is our current best (55.5% vs ref over
10k fresh games); its diff vs ocean is research/macro-2026-11-11/patches/hub2f.diff (Prism gem hub). Read
research/macro-2026-11-11/macro4-log.md for what won and lost (notably: a "carrier caution" change that made carriers
retreat more lost 6 points by cutting economy).

## Why
Healing happens only on our spawn (turn end) or from Willow (heal 3x Focus to an allied champion within range 4,
cooldown 8; check kit facts in code). Willow restores ~12.3k HP a game against ~100k it could (see
research/**/willow.md if present). Heal trips are 32% of all home trips (home trips = 37% of alive time). Today only
Prism/Tavi wait for a heal instead of recalling (model/world.h support_pair/support_protected ~896-925,
combat/support.cc local_support ~434+, its recovery block ~495-525); every other ally's recall / camp budget / crew
plan ignores Willow. Earlier Willow-only changes (its follow leash) gained +3.7 in Willow games, so the lever is real;
what's missing is the allies' side.

## Design
1. **Recovery for any ally.** Open the existing recovery test (saved = gain/usable x heal_trip vs detour + wait + 1)
   to any ally, not only Prism/Tavi: an ally near a living, visible-or-posted Willow whose heal is ready or ready soon
   waits/steps toward it instead of recalling when that is cheaper than the trip.
2. **Willow covers the neediest.** willow_follow (support.cc ~368-414): follow the ally with the largest expected heal
   gain, min(3F, missing HP + incoming camp fire over the cooldown), not the largest crowd. If comms has room, the
   healer posts which ally it covers (model/support_mailbox.h, model/comms.cc ~123-142); check bit budget first and
   don't displace camp records (worth ~7 points).
3. **Allies' budgets count Willow's supply.** In farm.cc spare/usable health (~663-666) and crew.cc plan_crew
   (~278-294), a covered ally's usable health over a clear includes Willow's supply: u x 3F x rounds/8 split over the
   allies it covers, with u = realised fill per cast measured online (prior from the replays/willow notes; no magic).
4. want_home (fight.cc ~498-519): a covered ally skips the camp-fled/camp-trapped home trip while a heal lands
   sooner than the trip would.
Constants come from the kit (3F, cooldown, range). Keep the change off when we have no Willow (identical play).

Add `debug_block` lines prefixed `WIL` for: an ally choosing a Willow heal over a trip; Willow's cover choice; a
budget raised by Willow supply. Keep fuel bounded.

## Done when
- Builds (debug and `--release`, sequentially) and one or two local games vs bots/variants/ocean-ref-b7c87cf run
  without errors on maps where we draft Willow (check the draft; if it's hard to get Willow on a map, find a ladder map
  in maps/ where our draft picks it); one no-Willow game must play identically to hub2f (compare results).
- Spawn a read-only auditor (Explore or Plan) on your diff: correctness, fuel, magic numbers. Fix what it finds.
- Final reply: design as built, diff summary, audit findings + fixes, WIL trace counts, and a measured baseline of
  Willow heals per game and ally hurt-recalls in your smoke games vs the hub2f game on the same map.
