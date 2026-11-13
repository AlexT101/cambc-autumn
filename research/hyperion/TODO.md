# hyperion: open work

Open work for our bots (ocean, charybdis, astraeus), by theme. Audit-level fixes (one function, one rule) are in [DIRECTIONS.md](DIRECTIONS.md);
results in [EXPERIMENTS.md](../EXPERIMENTS.md). Closed items are removed (last pruned 2026-11-02, through CHANGES
288; earlier text is in git history). An item tried and dropped is closed too: remove it and record the result in
EXPERIMENTS.

## Direction

- A robust, intuitive, logical bot: behaviour derived from the rules (reach, sight, cooldowns, health, walking
  distance, measured rates) over tuned constants, fixed decision orders or special cases.
- Logical changes stay even when level or slightly below 50%; drop only what is clearly worse (below ~47% over ~1100
  games) or wrong.
- Fuel-aware code is allowed when it wins by A/B (AGENTS.md "Fuel"); otherwise make work cheap or bounded. The gate
  plan is [GATE-PLACEMENT.md](GATE-PLACEMENT.md).
- Keep the teleport, Tavi and Willow code.

## Charybdis 527: altar locks (2026-11-13)

- Open: whether charybdis should keep buying altar locks. Never buying reads +1.0 in the mirror (chy-nolock 51.0%
  of 40,960 against 525; castor-nyx 55.7 / 55.3 against 527's 54.7 / 54.9 on the same suites) but about level against the Fish r8 and Mite
  bodies (fgate chy-nolock vs charybdis 525, 9 batches, 23,040 fresh map units: -0.07 ±0.27 points; Fish -0.33, Mite +0.19, one-site maps -0.65, multi-site +0.16, ladder side read -0.65), and our own
  locks have mattered live before. Charybdis buys 7.3 locks a game, places 3.8 (3.2 pre-emptive, 2.6 destroyed) and
  cancels 0.75 enemy tributes; a bot that buys and never places reads as charybdis, so the mirror cost is the purchase
  (gold timing), not placement. Patches: [no-lock.diff](../overseer-2026-11-13/patches/no-lock.diff) (never buy),
  [one-site-lock.diff](../overseer-2026-11-13/patches/one-site-lock.diff) (buy only on one-site maps; level with
  no-lock in the mirror), `git apply -p0` from the repo root. Verify on more fgate batches and live before shipping
  either; the 20-variant policy study is [locks/RESULTS.md](../overseer-2026-11-13/locks/RESULTS.md).
- Done: the 527/528 fuel pass shipped as **529**. Independent 4,096-game confirmation against 528:
  release out-of-fuel turns **-12.22%**, debug **-12.95%**, shortcuts **-7.35%**; 50.34% release wins.
  Exact ward geometry/search cuts, Prism premium and shop reuse, altar stands, camp exits and bounded
  threat queries; [evidence and rejected experiments](../fuel-527/README.md). This meets the requested
  10% exhaustion reduction; it does not establish that every gap to 525 or 2x fuel is closed.

## Scylla, and what it showed about charybdis (2026-11-13)

`bots/scylla` (CHANGES 526) wins 35.6% against charybdis 525 ([vfish](../ideas-2026-11-12/vfish/README.md)).
- Open, scylla: winning tributes still complete as often as before the denial (2.7 guards against 2.4 of ours); the
  Prism kill's worth in the engage decision and the kill credit for Vesper were not built; Vesper sees the Prism at a
  median r300 against a teammate's r95 and the shared bytes have no room for a sighting; the draft model was not
  refitted on its games; the unused build and denial switches (`economy/shop.cc`, `params.h`) can be removed.
- Open, charybdis: whether the Prism's 'G'/'L'/'Q' carry picks are skipped on turns the ranged hit in passing ends
  first (on Vesper with that machinery, 79% of her turns near a mate's hold); the shop's pricing horizon as the
  game's rounds left; its hoard tribute against an opponent that wards the altar and stops late (about 4 points to
  scylla); late stops on Fish's tributes (the interrupt arms stopped while the channel had time).

## Charybdis: the out-scaled Prism's Health and shop trip (2026-11-12)

Against Fish r8 the Prism's hoard is killed by a gold-fed Vesper (a median 465 Strength against 2,300 max health), and
the Prism dies holding a median 255 gold unspent ([v118-fish-b](../ideas-2026-11-12/v118-fish-b/README.md)). `r8s-c3`
= 525 + phs (`r8-scale/patches/phs.patch`, `shop.cc`): the Prism's shards stay Health until six basic attacks of the
strongest enemy Strength seen fit its max health, and it takes the shop trip when it is under that and its gold buys
one more such hit.
- Known: level locally on every read. As the only difference between c3 and c2 on 64,512 paired games a body, a
  third of games play out differently and the flips balance (net +0.05 / 0.00 / +0.05 points against fr8-g25, Flp4,
  Mt3q), with wins no slower. On Fish's recorded inputs the Prism's health at its live death rises 300+ in 13 of 37
  games; the goal without the trip changes nothing. Forcing its gold into Greed-Health loses (EXPERIMENTS).
- Open, measure: what the trips cost and buy inside a game. Profile c3 against c2 on replays (the Prism's farm income,
  purchases, trips, Focus, 100+ bag deaths) against fr8-g25, and from live r8 positions (`v118-fish/livefork_arms.py`).
  The local body kills the hoard at under half the live rate, so a level win rate may hide a cost and a benefit that
  cancel: a Fish body fitted to the hoard kill (0.29 Prism deaths with 100+ gems a Prism game live) would price it.
- Open, improve: a form that reaches more of the deaths with gold unspent (39 of 58 hold 150+), e.g. the trip priced
  by the bag riding on the body, or shopping sooner once out-scaled, without the farm cost positional caution paid.

## Charybdis fuel in fights (2026-11-12)

- Done (2026-11-13, CHANGES 531): the pass from 530 confirms **2.87% fewer release exhausted turns**
  and **2.32% fewer uncensored debug shortcuts**. The requested additional 10% was not met; further variants
  stopped paying. [Fuel 530](../fuel-530/README.md) records the 15 screens, identity diagnosis and fresh tests.

On 520 the Prism's own fuel no longer pays; the team's +1.5 at 200k is spread over out-of-fuel turns, gates and the
opening, none of them a lever alone ([fightfuel](../ideas-2026-11-12/fightfuel/README.md)).
- CHANGES 521 (goal steps not started under 4k, the siege and farm under 6k) took out-of-fuel turns down 10%, the
  target 514 left open. [Fuel C](../charybdis-fuelC/README.md) records the exact cuts already tried.
- Open: the turn's tail still runs out 0.68 times a game (the second strike search 0.19, the ward 0.12, heal and
  shield 0.11, the tribute habit's want_home 0.07); the strike search 0.9 times from 43k at the median.
- Open: a step guard whose verdict needs no new fight on fuel-short turns. The guard free is the one gate with a
  price (+0.9); every way of paying for it from the turn's own fuel is level.

## Charybdis: the rest of ATLAS's lethal-model change (2026-11-11)

CHANGES 517 took fixes 1, 2 and 4. Fixes 3 and 5 and the disarmed-enemy press add about +1.3 points at 2x fuel
(51.8% of 19,200 in all) but are level or below at 100k, out-of-fuel turns +21-114%. Make them cheap enough to keep
the gain at the real budget: [HANDOFF-fuel](../macro-atlas/HANDOFF-fuel.md) has the measurements, the remaining
diff and the method.
On 525 (2026-11-13, [atlas525](../ideas-2026-11-12/atlas525/README.md)): against fr8-g25 and mf-f9 the whole change is
+0.52 at 200k (+0.3 against Fish, the rest Mite's) and 49.2% at 100k; fixes 3 + 5 alone 49.8%; sim-free,
cache-only and cut-aware presses 49.4-49.9%. Closed unless fight turns themselves fit 100k.

## Ocean fuel target (2026-11-07)

CHANGES 455 reduces out-of-fuel turns by 3.5% on standard and fresh suites; the requested **20% reduction remains
open**. [Campaign 13](fuel-campaign-13/NOTES.md) records the exact changes, rejected experiments, profiles and
cache-readiness divergences. Start from the applied bundle and its matching draft7 baseline; do not repeat the
level cache/sort/loop experiments without a new mechanism.

CHANGES 495 (2026-11-10) takes a further 13%, most of it from the turn's tail checking its fuel
([fuel-2026-11-10](../fuel-2026-11-10/README.md)). Open there: tail steps that act with 2-8k left (the second strike
search, the tribute habit's `want_home`), the turn order's `offer_heal` and `plain_priority` tails past its 10k gate,
and the ~1.9k a tile the turn-end queue's warm-up costs.

CHANGES 496 (2026-11-10) meets the new **10% fewer OOF turns versus 495** target: -19.3% in a fresh 4,096-game
bench and -16.3% in release, with shortcuts -4.9%. It removes unused full damage bounds from support station
checks, precomputes output coefficients and reuses explicit-mask strikes. The remaining tail work above is
still open; details and failed experiments are in [fuel-2026-11-10-next](../fuel-2026-11-10-next/README.md).

## Turn order and ally coordination (2026-11-02)

- **Enemy order is adversarial**: assume every enemy changes priority, from round 1; never fall back to a default or
  last-read enemy order. An enemy's next priority is final only once it has acted this round and we read it after.
  Relax the worst case only by what the rules force: ranks are a permutation (one enemy per rank), settled enemies
  keep their order among themselves, and at our rank k at most k enemies (k + 1 in rounds they start) act before us.
  "One or the other" forks come from that last rule.
- **Act late when nothing needs you early**: idle allies nearer an enemy act later (CHANGES 293). Only champions with a
  need take early seats.
- Kept: kill bids are kept, made at the real distance, and not while channelling (CHANGES 295).
- Held, level: worst-case enemy order (`ast-pwc`, +21% out-of-fuel turns) and the joint per-tile bound (`ast-safety`,
  correct but 2.1x out-of-fuel turns; next: pick the m worst enemies from Strike's distance tables), ally seat
  commitment v2. Dropped: predicted enemy order, strike-pledge readers, kill-now value. The kill gap is reach (33% of
  turns near a low enemy) and Safety's lost stands (20%), not choice. Notes in
  [turn-order-2026-11-02/](../turn-order-2026-11-02/).

## Held branches

Built and judged; each is level in play or costs fuel. Revive with the "Next", or drop.

- **Camp damage by the nearest-champion rule** (`merge/funnel` 6b0fe83, frozen `bots/variants/merge-campdmg-6b0fe83`):
  a joint clear charges us only the strikers we'd stand nearest (melee at 1, ranged at their range, ties shared by
  output); only committed allies tank. Rule-derived, no params. Against 251: 53.0% of 20,108 against 252's 52.3% on
  the same games (paired +0.73, z 1.85); head to head against 252 on unused suites: 50.3% of 20,478, level;
  out-of-fuel turns +36% (`clear_fire_on_us` builds a camp list per crew evaluation). 256's `share_damage` already
  models the same rule by tank score. Retried 2026-11-06 as one model for every camp-damage reading
  (`bots/variants/astraeus-campdmg2`, `model/camp_target.h`; enemies absorb fire only if held until the camp phase,
  ties by turn order): level, 50.4% of 20,480 and 50.0% of 81,920 against 0305953, out-of-fuel turns +6-7%
  (EXPERIMENTS "Camp damage by the nearest-champion rule, retried"). Combined with the clear estimate's area hits and
  stuns and the attack-count fix (`bots/variants/astraeus-combo3`) and SPSA-retuned with a control: 48.0% of 20,480
  against astraeus tuned the same way, 2 points down on ocean and the panel (research/tune-combo3-2026-11-06.md).
  Dropped; revive only with a change to what the farm does with cheaper clears (big packs), not a retune.
- **The fight play-out with reach** (`held/reach-playout` cb2328dd): each fighter strikes only the opposing members
  within its reach once it has walked the gap. Better calibrated (EXPERIMENTS "Fight play-out with reach"), level in
  play (+0.5 on 6,144 games), out-of-fuel turns +15-22%. Next: a placing kept per roster for the turn, or reach only
  where it changes a target (Cassi and Issac, allies that never arrive).

## Play

### Macro (2026-10-30)

Every macro gain came from champions spending more time working (giving way less, later recalls, recall as travel,
no waiting at respawns); coordination toward fights lost every time. Logs in [macro/](macro/README.md). Ranked:

1. **Fewer, fuller trips**: one home visit that heals, shops and banks; interrupted clears (13% of Elk, 24% of Golem
   clears); crews that commit only when their arrival meets the respawn (pairs camping a respawn cost ~40
   champion-rounds an Elk; crews changed with 256). Two-emblem shop trips alone were level.
2. **Strong groups**: bold chips are right, but still a third of strong-group visits. 256's crews cover planned
   joint clears; a second champion joining an awake chip (ranged behind a melee tank) is untested.
3. **Coordination that saves farm time**: who holds a capture (252) and joint clears (256) shipped; who banks is
   open. The burst op failed on its valuation (instant solo rate against long-run rate), not execution.
4. **Smaller**: Monolith bursts (+4.4 on Monolith maps; 256 added Monolith crews); symmetric contest standoffs that
   freeze (gift-wrapping, the-line, stalactites); altars sealed inside a big group (the-pack mutations, galaxy:
   hyperion scores 0 too); Prism formation and allies farming near the carrier.

Settled, don't retry without a new reason (numbers in EXPERIMENTS): hunts, burst ops, duos, distress and assist,
tank formation, team ops for strong groups, cohesion bonuses; enemy sightings in comms (-2); walk-only or slower
recall banking; a Prism bag cap; camp_risk below 0.35; the cycle horizon; altar-lock wear-down and stall breakers;
recall lines below 0.25 with or without an enemy check; `max_wait` 0 (level held out); draft counter terms (lost 1.6
points; retry `--counters` only if a refit finds larger counters).

### Other play

- **Edge-case maps** (EXPERIMENTS "Edge-case maps", `tools/replay/stalls.py`): serpentines of 600+ layers whose
  search estimate never fits a turn ([portals.md](draft-compute/portals.md)); 1v1 contest standoffs; pocket deaths on
  farm hops; no gold for a crystal while an ally takes the gold camps; a crystal rebought on every spawn visit;
  dash-only pockets once an enemy bars the dash (CHANGES 274: the champion waits there).
- **Stellar/Ren compositions and enclosed maps** (fortress, lanes, caves, maze, sparse camps): against hecate, worse
  fights (outnumbered, struck first), lone champions picked off in tunnels.
- **Chase persistence** (EXPERIMENTS "Chases and leaves on the ladder"): top teams kill hurt targets twice as often
  as we do, and alone too (41% against 22%). CHANGES 290-291 keep pressed fights as chases; overriding the stand or
  pack zone lost (-2 each); ranged retreat firing was level again. Open: what makes a lone ladder pursuer twice as
  lethal on the same steps (contact time, the target's choices), and cohesion (3+ allies near 27% vs 14%).
- **Cohesion** (EXPERIMENTS "Cohesion, four parallel attempts"): CHANGES 292's step tie-breaks close ~20% of the
  allies-within-8 gap for free in choices but +17-24% out-of-fuel turns, from farm and carry turns near allies. Make
  those cheaper. Leans that change choices lost or were level in all four attempts (farm weights, stand radius,
  rallies); B's fight posts were level on 292. The lever left is execution: with an ally near, top teams' death
  rate at contact falls 16 -> 5% and their first strikes kill ~30%; ours stay ~18% and ~20% whatever the count.
- **Spawn healing, open** (CHANGES 328, EXPERIMENTS "Healing on our own spawn"): out-of-fuel turns +8.5%, mostly
  unattributed (`stand_reach` builds ~500 and `min_camp_damage` ~570 more a call on 00lanes round 1). Not yet
  integrated: the draft's heal price (draft.cc, recall + walk), kite on shared-gem maps, Willow's heal value, groups
  with more than 32 strikers. The gain is as large on maps with no camp near spawn (51.0%) as near (51.3%):
  find which part carries it.

## Patch 4.0.0 (cambc 5.0.0, 2026-11-05)

- Rules and stat tables are updated (CHANGES 389). Refit on 5.0.x since: every bot's draft model (draft5, CHANGES 402;
  draft10, 502; draft18, 515); emblem lab rounds 4-5 ran on ocean (499, 504). Pre-patch numbers that still steer
  play: the per-pick-count tables, the emblem lab table (CHANGES 233; Skirmish is now x1.10, Greed 40 shards' stats),
  diana's SPSA constants (oc6's retune on oc-base29 was H0), and every A/B baseline.
- Vendetta (900 health, 65 Strength), Vesper (35 Strength) and Marcella (weaker growth) are weaker; Stellar, Prism
  (+15, +10 Focus) and Varg (+5 Strength) stronger; Heart of Ruin loses Focus.

## Bugs

Logic fixes: A/B each, keep if level.

1. **Mid-turn state after our own hits**. A kill we make is read as a death (CHANGES 116) and a stun we cast is read
   (128). Not read until the next full update: camp members we kill stay in `Pathing::live_camps()` (since 242 they
   also wall routes) and `blocked_` survives attacks; our fighters keep turn-start health, shields and cooldowns
   (`Safety::made_`). Re-reading everything lost (47.3%, lean 49.3%, both more out-of-fuel turns; `p1a-state`,
   `bots/variants/p1-final`): retry with only the reads that change a decision.
2. **An emblem bought mid-turn updates only our own camp output** (CHANGES 181; 185 closed the other gaps).
3. A caught `engine error 5` in the queue's `prepare` (gen-labyrinth-102106300, side b, round 756): no play change
   seen; find the call.
4. Unverified: idle turns under a Golem (dense-camps).
5. **Shared-gem standoff** (EXPERIMENTS "Last-minute bug fixes", dropped B): on gen-shared-gems-600101605 a big
   group leaves one safe station; a guard holds it and every other champion walks at it all game (0-0, both sides).
   Yielding `kite()` to farm when every station is held (worktree commit 4ed5bfc8) was level (50.0% of 10,240) but
   on that map the yielders died to camps for nothing and lost both games. Fix where farm and kite choose the group
   (stations a guard doesn't take from casters), not with a yield.
6. **The stand reads unseen enemies from a point, not from `possible`** (CHANGES 337). `Safety::stand_reach` and
   `want_home`'s early return (`enemy_believed`) count an enemy out of sight only if it was seen last round
   (`age <= 1`), as a walker from its last tile (`walk_in`: `enemy_reach::distance` from `e.pos`). The damage side
   (`threats`, `lethal`, `unseen_blow`) and chase read `ChampionBelief::possible` instead, weighted by
   |square(tile, reach) ∩ possible| / |possible| and dropped below `credible_weight`. So two models of one enemy
   disagree: the point is a turn stale, and at age 2 the enemy leaves the stand while the threat model still weights
   it, which can bring back the retreat, lose sight, step back in cycle a round later. Consolidate: the stand's walk
   from `possible` (one distance field from p, min over each enemy's tiles, shared by every unseen enemy), included
   by the threat model's credibility weight, not an age cutoff. Open: how a wide stale set counts (nearest tile is
   pessimistic; the damage model scales by overlap).

## Candidates

Each needs an A/B (check EXPERIMENTS first). Bundle removals and keep them if level.

- **Removals:** `keep_walk`'s free-stun logic in `enemy_cast` (still used by retreat and the game-ender intercept),
  replaced by a plain threshold; ground casts at unseen enemies (`max_unseen_tiles`); kite's contested branch;
  probabilistic `threatened()` (risky: it gates recalls). Ren's specials change only on ladder evidence.
- **Behaviour:** `spell_clear_rounds` pricing tested both ways. (Walking to lock a big enemy tribute: done 2026-11-12,
  level, EXPERIMENTS "Interrupting Fish r8's big tributes".)
- **Farm and capture pricing** (judgement calls): an enemy hold that pays before we arrive priced as respawning at
  payout + respawn (skipping it lost, CHANGES 181); an empty cleared group unseen for capture + respawn rounds as
  probably taken; `stun_worth` counting a tributer's whole bag though a cancel only delays it; `gems_short` minus
  allies' bags (endgame); `help_radius` from the ally's rounds to its recall line; altar-lock "our side" by walking
  distance; `pick_up`'s 4-step cut-off from the payout round; the protected mate by a rule, not Prism.
- **Emblems:** the lab table (CHANGES 233) decides ~42% of new emblems; elsewhere `income_prior`'s constants (4.5
  rounds a gem, 0.005 kills and 0.015 Tribute turns a gem, weight 30 gems) are measured, never tuned. An ally's
  Capture already covers holds we share (W1-C, not run). Hunter is almost never chosen. The low captures-per-gem
  tercile (big groups) was level (Capture first lost there): check what the model buys on those maps.
  - **After emblem lab round 4** (2026-11-10, EXPERIMENTS "Emblem lab round 4 on ocean"): the table is worth ~3
    points to ocean and nearly all of that is its late Collectors cells; its k0-2 cells are worth nothing. The
    current logic underprices Collectors (`current_emblem` credits it for camp damage only): price its champion
    damage and the table may no longer be needed for it.
  - **Skirmish as everyone's fifth emblem** is in (CHANGES 499, about +0.4 points locally, no live pair yet).
    `passive_saved` prices Skirmish at `fight_weight x fight_share x (1 - 1 / 1.1)` and rarely picks it: raising the
    pricing would make the table cell unnecessary.
  - **The lab's design:** drawing 35-50% of every decision scrambles builds and hides effects of this size. Next
    time randomise whole tables or build orders per team-game (tools/emblab/README.md "What round 4 found").
  - **After emblem lab round 5** (2026-11-10, CHANGES 504, EXPERIMENTS "Emblem lab round 5 on ocean"): the edit lab
    (whole-policy edits per team-game) agrees with A/Bs and plays 1.2M games an hour. Open: no live pair for 504;
    the lab ran on 501's draft, so rerun its replication round on the current bot (`efit.py step` with a new
    `stage.json`, 45 minutes) before trusting the other finalists; the Prism edit's two A/Bs on 503 disagree
    (+0.1 and +1.1); pricing Collectors' champion damage in `or_passive` read level (+0.05 ± 0.13), so the table
    still carries Collectors; Greed and early Health or main-stat emblems lose 2 to 10 points.
  - **CPU-slot registration race fixed (2026-11-10):** Python and fastrunner lock and write a temporary file
    outside `members/` before renaming it into view. Forced Python interleaving and Rust concurrent cleanup
    reproduce the old lost-weight failure and pass with the fix; dead-member cleanup remains intact.
    Existing long-lived Python processes keep their imported code until they finish; do not restart evidence jobs.

## Fuel

Charybdis fuel D (2026-11-11): **10% exhaustion target remains open; nothing shipped**.
The larger 4,096-game development test was +0.21% exhausted turns and -1.43%
recorded shortcuts, both intervals spanning zero. Before reusing its candidate
patches, resolve/exclude the deferred-guard conditional replay difference and
audit nearby-group span lifetimes. [Report and rejected ideas](../charybdis-fuelD/README.md).
Confirmation seeds 4711110–4711117 remain unused.


Latest census: fuel-campaign-3 [NOTES.md](fuel-campaign-3/NOTES.md) "Where late run-outs go now" (strike search in
88% of fight-set first run-outs, Heart of Ruin 60% of them; on a late set farm 45%). The 2026-10-29 profiles behind
items 2-7 (sim, search, want_home, prey, turn-order costs) are in [OPEN-ITEMS.md](fuel-campaign/OPEN-ITEMS.md);
later rounds in fuel-campaign-2's and -3's NOTES. Sub-1% cuts don't show in A/B out-of-fuel
counts (shared-gem maps swing by thousands): judge with `tools/fuel/oof_bot.py`, also without shared-gem maps, and on
the 100M bench's turns over 100k.

1. **Dash travel's out-of-fuel tail** (CHANGES 274): +26-28% out-of-fuel turns (mean fuel +2%), mostly hole-heavy
   maps (topo, mega-groups, huge), ~2/3 with the crossing logic. A logic pass (c00b84de) moved it 1 point. Next: the
   fuel census on those turns against the reference before more guessing.
2. **Cheaper fight sims**, needed before the step-guard and prey-cut-short gates can go: non-plain `act()` for
   non-plain kits and fights that run to the horizon. Ideas, each kept only at -0.3% total fuel or better with
   replays identical: incremental per-side sums for `their_cap` / `overwhelmed`, F2b (copy only fighters' mutable
   state), Ren in `play_quiet`. Not exact, A/B only: F7 for step_guard with links (Cassi and Issac); F3 (prey
   skipping a fight a lost one covers). Deferred: F5, a damage tape per roster per turn. By the rules, still
   single-target or simplified: ground AoE, Varg's splash, HoR's landing and Ren's reflection; HoR's passive at event
   turns; once we fall, camp hits go to our weakest, not the next-nearest; `walk_allies_in` ignores walls and the
   enemies' approach, and an unseen enemy cancels every delay.
3. **One danger model** (STRIKE-SEARCH phase 5, [DANGER-MODELS.md](DANGER-MODELS.md)): one danger pass per tile per
   turn across want_home, step_guard and the search's end tiles; the gain is folding them, not memoising. Fold in
   dash-landing `danger`, `shield_if_needed` and `breach` fire from `Safety::awake_members()`. Sharing want_home's
   lethal and stand with the search's: 2-4k on HoR heavy turns.
   Smaller: a start-tile-only or one-candidate price skip; a per-turn `viewers()` grid; kite's `make_way`
   `know_failure` (8.5k, ~30 turns a game).
4. **The farm loop**: CHANGES 175 and 226 stop it exactly once no group left can beat the best (banking too), but
   `farm-partial-evaluation` still fires (20k times on the heavy set, 2026-10-29). Next: pick_up's farm-loop gate,
   retested with an A/B (removing it before 226: +90%). The non-banking stop never fires on dense-camps in rounds 11-300
   (its bound omits clearing time; an exact clearing-aware stop cost 12.5k: needs per-map class tables and a world-kept
   hurt mask). farm.post (17-20k on out-of-fuel turns): `room()`'s reserve underestimates it on mazes, and farm's walk
   runs two route searches after a check that reserves one (fuel-campaign-2 NOTES "quill: run-out forensics"). P5 (a
   tighter steps bound), P6 (F4's drafted spawn steps), P7 (a round-1 draft certificate; split the pre-stage's cost
   first), P10 (175's stop with the true distance). `crow-flies-farm` fired 5224 -> 7192 in the P1+P4 A/B: look at why.
5. **Round 1**: world construction is still >200k on ~100-group maps (~145 instructions a member), so round 1 runs
   out there and finishes in round 2 (CHANGES 230); then `prices()`' first call 14.6k, the post-loop 40k.
6. **The remaining gates**, one at a time with an A/B ([FUEL-GATES.md](FUEL-GATES.md)): step-guard, prey-cut-short,
   siege-route-fuel, comms-stale-vision (its removal with farm-no-route raised rounds 1-10 out-of-fuel turns, CHANGES
   250), turn-order (251 skips champions out of strike reach; bound its offers first, costs before 251: `offer_escape`'s
   `threats_at` 9-14.5k, `offer_kills` up to 10k, `offer_heal` 5-11.5k, `may_escape`'s `strike_of` 2-4.7k). These gates
   are brakes until the sims are cheaper. `fuel_ok` could throw `StaleTurn` when fuel rose since its last read this
   turn, covering a stale tail.
7. **Bookkeeping outside `decide`** (~19k of a heavy turn): windowed dilation for track on 100x100 (2-4k there); one
   `board_awake_camp_occupancy` read a turn in `update_camps` (A2); exact sim memos across a stale turn (A3/A4: first
   measure how many keys match the abandoned turn's); a cheaper `StaleTurn` unwind (A6); `always_inline` on hot
   cross-file helpers and a recheck of the `[[gnu::flatten]]`s after the unity build.
8. **Warm-up follow-ups** (CHANGES 164-169): centre fields still finish late on big maps (dense-camps rounds 210-470),
   where farm steps cost 17.7k a call before round 300 against 5.5k after; where the queue never warms centres
   (gen-gem-centre) the loop rebuilds `from_here` (~34k) every turn. A capped `from_here` that grows its cap (W18) was
   mixed and its commits are gone; building centre fields nearest-first earlier is the alternative. Recount
   `crow-flies-farm`, `farm-partial-evaluation` and `ward-no-bushes-clusters` (`py tools/replay/debug_lines.py SHORTCUT
   -- <batch>`).
9. **Strike phase 4a/4b** ([STRIKE-SEARCH.md](STRIKE-SEARCH.md)): the retreat search's fuel (40.8% real, 52.6% at
   100M); the partial-fix branches are gone.
10. **Tools**: `tools/ab.py` fuel per side; `tools/fuel/bench.py --release` and `--no-queue`, so fuel-only work is
    judged on ladder codegen.
