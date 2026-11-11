# Brief B: the carry hub (route the team's gems into Prism, keep the team around it)

You are an implementation subagent for the macro4 lead. Work ONLY in /home/ubuntu/wt/macro4 (git worktree, branch
macro4-20261111). Never touch other checkouts under /home/ubuntu/wt/ or /home/ubuntu/cambc-autumn, never edit
bots/variants/ocean-ref-b7c87cf, bots/ocean or bots/variants/macro4-pact (another agent's), never write to any Claude
memory directory, never run ab.py / fgate / A/B tests, commit nothing. Read /home/ubuntu/wt/macro4/AGENTS.md and
cambc-rules.yaml first (API: docs/api/cpp.md, sdk/cpp/cambc.h).

## Candidate
`cd /home/ubuntu/wt/macro4 && ./copybot ocean variants/macro4-hub`; edit only bots/variants/macro4-hub/src. Do not
touch draft/ or emblem selection.

## Why (measured in ocean-vs-ocean mirror games)
- Prism is in 79% of our games. Its passive (+1.5 Focus per carried gem) scales both its spells (stun 1.5x Focus,
  ground 1x Focus area that also hits camps). A probe where Prism banks like everyone else (no hoard) won only 30%:
  the hoard is the team's main engine.
- Prism collects 36% of its team's gems (mean). Teams whose Prism collected >= 50% won 60-66%; <= 30%: 40-44%.
  A Prism bag lead of 60+ gems at r200 goes with a 78% win rate, a 60+ deficit with 34%.
- Today gems reach Prism only when Prism happens to be at a capture: `sole_capture_holder` (capture.cc ~298) makes
  allies step off for a healthy Prism already on/fitting the tiles, only while NO enemy is seen anywhere; Prism's
  farm values crewing an ally's group / taking over an ally's hold (look for this pc1 logic in farm.cc, capture.cc
  `take_capture_handoff`, `yield_capture`). Allies choose groups with no regard for where Prism is, so most clears
  happen far from it.

## Design (the team's gem flow has a hub)
Principle: a gem carried by Prism is worth more than a gem carried by anyone else, because until it is tributed it
also adds Prism output. Derive that premium; don't hand-pick it:
- Marginal Focus value of one carried gem: Prism casts its two damage spells every `ability cooldown` (8) rounds,
  1.5x and 1x Focus (use its kit from champions.h / ChampionFacts, not literals), so one gem adds
  `1.5 * (sum of its damage-spell multipliers) / cooldown` damage a round, for the rounds it stays carried
  (bounded by rounds left in the game, and by a horizon such as the rounds until its bag would be banked/wins).
- Convert damage to gems at the map's camp exchange rate (total camp member health / total group gems over the
  map's groups, from the static map; or the farm's own clear estimates), giving a premium rho = extra gems of output
  per gem carried. Clamp to [0, a sane bound such as 2] and fade it to 0 as rounds_left shrinks.
Then:
1. **Allies route to the hub.** In the farm loop's group value (economy/farm.cc, where `known.gems` / worth is built,
   ~1790-1980), for a non-Prism champion with a living allied Prism: a group with gems that Prism can reach and hold
   (Prism's known position: visible, or its last sighting / comms; its walking steps to the group <= our estimated
   rounds to clear it + capture rounds, and Prism not channelling/banking/fleeing) is worth its gems x (1 + rho),
   because Prism will take the hold. Respect the existing per-group cache in that loop (the value depends on Prism's
   position, so compute the multiplier per turn outside the cached block or include it in the cache context).
2. **The hold actually goes to Prism.** When an ally holds a cleared group's capture and Prism is walking to it and
   would arrive before payout (or the capture can be restarted by Prism without losing more than its premium), the
   ally keeps the tiles until Prism stands on them, then steps off (reuse yield_capture / take_capture_handoff
   mechanics; read them carefully first). Relax sole_capture_holder's `enemy_seen(world)` gate to the threat that
   matters: no visible enemy that could reach the capture tiles before payout (use Safety/World reach helpers that
   exist), keeping `enemy_may_see(world, position_of(a))` semantics where sensible.
3. **Prism is a collector, not a clearer.** Prism's own farm choice should value collecting allies' cleared or
   nearly cleared groups (their claimed groups within its reach) at their gems x (1 + rho) with only walk + hold
   rounds as cost, and not need to clear groups itself when such collections are available. Check what pc1 already
   does and extend rather than duplicate.
4. Keep cohesion as a by-product: no separate "stay near" rule.

Add `debug_block` lines prefixed `HUB` when an ally values a group with the premium (rho, Prism steps), when a hold is
handed to Prism, and when Prism takes a collection. Keep fuel bounded (2x fuel is the test budget; no per-tile loops
over unbounded sets).

## Done when
- Builds (`cambc build bots/variants/macro4-hub`, debug and `--release`; see tools/README.md) and one or two local
  games against bots/variants/ocean-ref-b7c87cf run without errors on a map where both teams have Prism (check
  `cambc run --help`); HUB lines appear in a debug run.
- Spawn a read-only auditor subagent (Explore or Plan type) with this brief and your diff
  (`diff -ru bots/ocean/src bots/variants/macro4-hub/src`) to check it against the brief for bugs, unintended
  behaviour changes (e.g. non-Prism comps must be unchanged), cache-staleness in the farm loop, and fuel. Fix what it
  finds.
- Report back: diff summary (files/functions), how rho is derived and its typical values, the auditor's findings and
  your fixes, anything skipped. Stop there.
