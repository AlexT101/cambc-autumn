# astraeus code audit, 2026-10-28

Thirty auditors, one per `.cc`/`.h` pair or standalone file of `bots/astraeus/src` (`draft/draft_model.h` is
generated and was skipped; `unity.cpp` went with `main.cc`). Each read `cambc-rules.yaml` and its files, but not
`research/` or the git history, so the findings are unanchored by past experiments. Each report has **Changed**,
**Considered, not changed** and **Suggestions** sections with file:line references.

- **Cleanup** (comments, helpers, renames, dead code): merged to main as CHANGES 202. Fuel bench at 100M,
  test drafts: the 4-map set 8/8 replays identical, fuel -0.84%; the wide set 52/52 identical, fuel -0.96%. The bench
  builds in debug mode, so part of the saving is farm's removed experiment traces and a release build saves less.
- **Fixes** that change behaviour: on branch `audit/fixes-2026-10-28`, above the cleanup, untested by A/B. See
  [Fixes awaiting A/B](#fixes-awaiting-ab).

Reports: [abilities](abilities.md), [bank](bank.md), [bot](bot.md), [bot_parts](bot_parts.md), [camps](camps.md),
[capture](capture.md), [champions](champions.md), [combat_priority](combat_priority.md), [comms](comms.md),
[crew_work](crew_work.md), [draft](draft.md), [farm](farm.md), [fight](fight.md), [guard](guard.md),
[idle_priority](idle_priority.md), [main](main.md), [map_economy](map_economy.md), [map_features](map_features.md),
[params](params.md), [pathing](pathing.md), [plan](plan.md), [safety](safety.md), [self_abilities](self_abilities.md),
[shop](shop.md), [siege](siege.md), [support](support.md), [support_mailbox](support_mailbox.md),
[turn_order](turn_order.md), [util](util.md), [world](world.md).

## Fixes awaiting A/B

| File | Fix | Bench replays |
|---|---|---|
| turn_order | `packed_priority` mapped raw priority 0 to engine priority 0, which `comms::payload_of` reads as no payload: an idle gemless Prism at 80-90% health lost its claim and its support request. Found independently by comms and support_mailbox too. | 2/8 differ |
| farm | A turn whose group loop weighed nothing reset `memory.crew`, so a helper took over its ally's claim. | 3/8 differ |
| bot | Damage taken on our spawn read as 0 (the turn-end heal hid it); ending on spawn now records max health. | identical |
| safety, guard | A visible enemy with a pending teleport now acts from its destination everywhere (`acts_from()`), as `approach()` and `fight_key` already did. | identical (no teleports) |
| abilities | `camp_cast` applies the Monster/Collectors factor to every camp spell value, not only the finishing test. | identical |
| siege | `siege_load`'s strongest-member Strength counts live members only. | identical |
| capture | `contest_capture` skips an enemy hold that pays after round 2000. | identical |
| shop | `affordable_prefix`'s cache key includes `main_stat`. | identical |
| world | Respawned or unseen-recalled enemies keep their damage factor and lose their stale shield; an unseen payout clears `held_since`. | identical |
| map_features | Crystal `travel` leaps from every tile, matching the JS (34/400 fuzzed maps differed). The bot never runs this path. | identical |

Left out: camps' Varg splash fix (skip targets whose splash would wake a Monolith we aren't besieging). That is a
judgement call about what Varg may hit, so it stays a suggestion ([camps](camps.md)).

## Recurring findings

Several auditors reached the same gap from different files; these are the strongest leads.

- **Camps hit the nearest champion, not all of them.** Sums over every awake monster in reach overstate damage when
  an ally stands nearer: bank `access_fire`, siege's `low` and `siege_ready`, self_abilities `threats_near` and
  `shield_if_needed`, support's finish checks (asleep monsters too), siege `kite_productive_action` (respawning and
  asleep groups too). Safety's `find_members` errs the other way: it trusts champions who haven't acted to stay
  nearer. `exposure(p, supported)` in siege already models it.
- **Kiting.** Melee spell users (Marcella, Ren, Heart of Ruin) never spell-kite though their spells out-range wolves
  (draft, camps, farm). Ground spells reach 5 and could kite elk and golems (reach 4), but `spell_clear_rounds` and
  siege's cast tiles exclude them (camps, siege). Farm's kite tile ignores neighbouring awake groups.
- **Reach and turn timing.** A walk before a non-exclusive stun adds a tile (Cassi 5, Heart of Ruin 4, Marcella 2;
  champions). Spell reach and ranged basic attacks arrive a turn later than modelled (crew_work). The two-turn threat
  misses dash then reset-strike, understating Vendetta and Vesper ~3x (safety). Reaching attack range doesn't stop a
  tribute or teleport; only a kill, stun or lock does (fight). Prism's escape trusts stuns only on enemies that have
  acted (abilities).
- **Per-champion gaps.** Vesper skips shop, farm and her dash after a ranged attack (bot); Ren can spend its escape
  dash's cast on a stun (fight); Varg can end a turn with neither reset nor shield (self_abilities) and its splash
  wakes groups unmodelled (camps, self_abilities); only Prism and Stellar get a walk-only option (plan); the turn
  order's exact bids skip Prism, Vesper, Ryth, Vendetta, Marcella and Heart of Ruin (combat_priority); one 0.35
  recall threshold for all (params); shields ignored in `tribute_safe`, hurt checks, heal bids and `main_stat` (bank,
  params, turn_order, shop); Greed, Skirmish and Collectors are never bought (shop).
- **Valuation consistency.** plan and abilities disagree on pricing a cancelled recall, and both count a stun's value
  on a blow that kills (plan). `attack_target` leaves out the victim's gem bag (params). Monoliths and clear time
  distort the draft's map-economy checks (map_economy).
- **Comms.** The round tag is 2 bits, so a sender out of fuel 4-5 turns reads as fresh (support_mailbox); capture
  records can be overwritten unread when turn order changes (comms); the second sighting slot is lost on 100x100 maps
  with 5 enemies (comms).

## Fuel gates that could go

farm.cc:711 dash-aware fields on many-group maps (champions); guard's two gates, which drop the whole guard
(guard); pathing's static-descend gate, which trips before the free route reuse, and its unchecked ~45k second search
(pathing); siege's `tiles` and kite prepare loops (siege); safety's `trade()` floor (safety); turn_order's fuel-short
path (turn_order); farm's partial evaluation (farm); map_features' crystal fallback (map_features). Latent: the draft
ward search can never finish after a failed first turn (draft).

## Cheap fuel savings

`holding_capture` recomputes `prism_capture_holder` ~12x a turn (capture); `make_field`'s `unique_ptr` costs ~420 a
field (util); `stun_pending` and `shield_value` read the same buffs twice (util); refused camp attacks throw at
~3.9k each, up to 16 a turn (bot_parts).

## Probes needed

The Prospector bonus's rounding with the lowest-id remainder (capture); whether a heal needs its target in vision
(support); whether a dead member's tile in a live group is a teleport target (pathing); `make_field`'s cap boundary
(util).
