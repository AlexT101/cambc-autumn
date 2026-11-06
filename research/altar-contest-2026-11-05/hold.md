# Team altar hold (plan items 0-1), `bots/variants/ast-hold-dev`

This is ocean's CHANGES 408 (guard and escort) made general and ported into astraeus 29cd0921. The frozen base is
`bots/variants/astraeus-29cd092`. All of it is in `src/economy/hold.cc`, with hooks in `bot.cc`, `economy/bank.cc`,
`combat/plan.cc`, `main.cc`, `bot_parts.h` and `params.h`.

## What it does

- **Zones** (`link_step`, `zones`). Altars are linked when the walk between their tribute tiles is at most `zone_link`
  = 10. The walk is over `StaticMap::blocked_for_us`, not Pathing's walls, so dashers and walkers agree. It uses one
  capped field per altar and runs once a game, in the turn-end warm-up (`warm_hold`), or on first need.
  - `home` is the zone our spawn walks to soonest. It is the held zone. On one-zone maps it is the only zone.
- **Trigger** (`update_hold`, run every turn by every body, dead ones too). The hold is on when either:
  - some ally carries a long bag: `tribute_turns(bag, its Tribute emblem) > tribute_window` (8), with the bag read as
    seen, else as posted (`comms::bag_of`). A Prism's bag counts only if it wins, because Prism keeps its hoard
    otherwise (`retaining_gems`);
  - or, on a one-zone map, the enemy has 600+ tributed and leads by 200+. It stays on until the lead is under 100
    (408's cooked trigger).

  Every input is shared (scores, liveness, types, bags, static geometry), so the bodies agree without messages.
- **Holders**. Up to `hold_bodies` = 3 empty-handed allies, ranked by base health x Strength (a linked pair at 0.25,
  ties by index). They are chosen from bodies without a long bag, and at least `hold_farmers_min` = 1 of those stays
  at work. A body with any bag banks first (decide's order), so it is not picked.
- **Screen** (`screen`). The stand tiles of the held zone, built once:
  - Candidates are tiles 4-7 steps from the zone's tribute tiles (`screen_near`, `screen_far`), capped at half the
    enemy's walk to the zone.
  - They must be on the enemy's walk from its spawn, `enemy_spawn_steps(p) + steps(p) ≤ enemy's shortest +
    screen_slack` (3). This band covers every near-shortest approach, whatever the walls and holes.
  - Tiles within 1 of their spawn are excluded, and so are tiles in camp reach, unless no candidate is left.
  - Score: bush first, then nearest the shortest approach, then 5 steps out.
  - Picks are kept `screen_spread` = 3 apart while candidates allow, so separate approaches each get a body.
- **Holder turn** (`screen_turn`, in decide after the shop branch, where 408's `guard_turn` was). It drops the farm
  claim, chases (with `chase`'s own pricing) an enemy within `hold_leash` = 9 of the zone's altars, and otherwise walks
  to its screen tile.
- **The carrier**:
  - While the screen is manned, its long bag banks only in the held zone. This applies unless the bag is `closing`
    or no walk reaches the zone, and it changes `bank_gems`' altar pick, `submit_here`, `can_tribute_here`, the
    strike search's goal field and `mend_step` (`bank_field`). No crystal hop leads elsewhere.
  - At the altar it starts its channel only once the screen is up (`hold_wait`). That means either every holder is
    seen on or beside its tile, or a wait set once per hold has run out. The wait is the holders' remaining walk (an
    unseen holder is assumed walking since the hold began), capped at the channel's own length.
  - It never waits while retreating or after taking damage.
- **Locks**. `place_lock` keeps our lock on the held zone's altars, as 408 did.

## Fuel

The static parts (zones, screen, stand fields) are built once, with spare fuel at the turn end. The screen costs
36-55k on 100x100 maps (measured in debug: about 150 fuel a band tile for its two field reads and tests), so
`warm_hold` waits for 200 fuel a band tile. Per turn there is only the ally loop, unless a long bag is carried. There
is no fuel gate.

The auditor's fixes are in: shared walls for zones and the screen, no wait while retreating or hit, the wait capped
at the channel, no crystal hop away from the zone, the zone in the strike search's goal and in `mend_step`,
selection scans instead of a sort, and stand fields warmed. Rejected:
- The cooked trigger idling the team: it is 408's tested rule, and it is in scope.
- The "seen on its tile" check rarely passing (bush tiles are unseen): the bounded estimate covers it.
- One-round bag disagreements from `bag_of`'s rounding, and the Tribute emblem being known only when seen.
- Holder churn when one gains a bag.
- The lock risk to an unseen channelling ally: it predates this change.

## Results (2026-11-05)

**Fuel bench** (`tools/fuel/bench.py`, 16 games, real budget; `replays/fuel/hold/`):

| | mean | p99 | OOF turns |
|---|---|---|---|
| base | 50,938 | 90,459 | 63 |
| candidate | 50,455 | 90,711 | 92 |

- 2 of the 16 replays are identical, and their total fuel is +0.94%: the per-turn ally loop and the warm-up.
- The bench swings by ±20 out-of-fuel turns.

**A/B**: own drafts, fresh ladder-mix `maps/suites/fresh/fresh-560001..560020` (`replays/ab/ast-hold-dev-560`, batches
`replays/batch-20261105-162757-ab-ast-hold-dev-560-*`). Classes use walk zones (link 10) from the map files.

| class | candidate win % | 95% CI | games |
|---|---|---|---|
| all | **48.3%** | 47.3-49.2 | 10,240 |
| one-zone | 49.6% | 48.2-50.9 | 5,214 |
| of which one-altar | 50.3% | 48.2-52.3 | 2,318 |
| multi-zone | **46.9%** | 45.5-48.3 | 5,026 |

- By zone count: 2 zones 47.3%, 3 zones 46.5%, 4+ zones 46.0%.
- No match failed.
- Out-of-fuel turns: candidate 82,109, base 75,237 (+9%).

**Mechanism**: 1,024 games (fresh-560001 and 560002), extracted. Classes use the plan's Chebyshev-10 zones
(`altar_study.py`). Each row is candidate / base:

| class | turns | starts | completed % | manual cancels % | stun cancels % | lock cancels % |
|---|---|---|---|---|---|---|
| 1 zone | 9-20 | 352 / 387 | 81.8 / 79.1 | 9.9 / 10.6 | 3.4 / 4.7 | 2.8 / 3.4 |
| 1 zone | 21+ | 764 / 769 | 27.5 / 23.0 | 37.3 / 42.1 | 14.9 / 17.4 | 17.1 / 12.7 |
| multi | 9-20 | 435 / 484 | 90.3 / 90.7 | 3.9 / 4.1 | 0.7 / 1.4 | 1.6 / 0.6 |
| multi | 21+ | 356 / 379 | 61.0 / 53.6 | 22.8 / 20.6 | 5.6 / 9.8 | 3.1 / 8.2 |

- Long channels with no enemy within 8 at the start completed:
  - one zone: 58.3% against 53.5%;
  - multi: 85.2% against 81.4%.
- Gems banked by long channels: 250 against 240 a game-side.
- Short channels (1-8 turns): 9,097 against 9,674 starts on one-zone maps, 13,063 against 13,597 on multi. The
  candidate farms less.
- From a winning bag to the win:

  | class | sides reaching a winning bag | won from there | median rounds | p75 rounds |
  |---|---|---|---|---|
  | one zone | 251 / 256 | 89.6% / 93.4% | 33 / 37 | 80 / 95 |
  | multi | 278 / 315 | 86.7% / 87.6% | 15 / 15 | 34 / 37 |

## Read

- **The mechanism works but costs more than it gains.** The screen raises long-channel completion by 3-7 points,
  and stun cancels fall.
- **Holders don't farm.** Holds run for every long bag on every map, and in the smoke games the carrier's walk to the
  zone alone took up to 30 rounds. The candidate starts about 5% fewer short channels.
- **Multi-zone maps lose the most** (46.9%):
  - the home-zone redirect adds walk;
  - finding 5 already put the safety ceiling there low;
  - 12% fewer candidate sides ever reach a winning bag.
- **One-zone maps read level** (49.6%), and 408's one-altar gain does not reappear here (50.3%).
- **Manual cancels are still the largest cause** for 21+-turn channels (37%): `tribute_safe` still cancels a
  screened channel.

Next:
1. Hold only where it pays. Drop the multi-zone hold and redirect (one-zone maps only), or gate it by the zone's
   margin. Start holders only when the carrier is within its walk of the zone plus the holders', so the screen idles
   for the channel rather than for the trip.
2. Plan item 4 on one-zone maps: keep a screened channel unless a threat passes the screen. Then measure on a
   one-zone suite.
