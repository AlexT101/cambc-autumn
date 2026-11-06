# Perma-lock when ahead (2026-11-06)

The user's idea: on a one-altar map, while we lead in tributed gems, keep our lock on the altar, so the enemy
scores only by breaking it (5 basic attacks). Re-lock whenever they break it, ideally just before their channel
lands. At round 2000 more tributed gems wins, and our own lock never blocks our tributes.

Dev copy `bots/variants/oc-lock-dev` (from `variants/oc-retest-clean` = `bots/ocean` = live v78), namespace
`params::plock::`, code in `src/economy/perma_lock.cc` with hooks in `bank.cc` (place_lock, continue_recall),
`bot.cc` (decide, shop) and `unity.cpp`.
- With every knob off, bench.py's replays are byte-identical to oc-retest-clean at 100M: 16/16 default and
  52/52 wide, with the same fuel (re-checked on the final source).
- Tools are in `lock-tools/`:
  - `sites.mjs`: altar sites per map;
  - `mkvar.py`: a variant with knobs set;
  - `plstats.py`: the PL* debug lines per game;
  - `gates.py`: each gate's firing, after the fact;
  - `split_sites.py`: win % by altar make-up.
  - Results are in `lock-tools/results/`.

## The site

- Altar tiles within Chebyshev 3 are merged into one site (`merge`), of at most `max_tiles` (2) tiles.
- Ladder: 32 one-tile maps, plus 15 one-site 2-tile maps (00quarry, 03homonoliths, 04plaza, ...). 03the-front's
  34 tiles are left out.
- Fresh 541100-541119: 1,094 one-tile maps and 508 two-tile one-site maps of 5,120. These 1,602 maps are the dev
  subset `maps/suites/merged/lock-one-dev` (3,204 games).
- On a 2-tile site, each tile needs its own lock, and a body carries one (carry 1).

## Knobs (`params::plock`)

- **Gates.** `gate` is the keep gate: our lock is kept on the site when passing. `hold_gate` gates the costly
  parts (seeking, holders, stun walks); 0 means it uses `gate`. Each is a bitmask whose conditions must all hold,
  with `from_round` and team gold ≥ `gold_reserve` (10):
  - `g_lead`: ours − theirs ≥ `lead`;
  - `g_bag` (G1/G2): an enemy's last-seen bag ≥ `bag_min`;
  - `g_sum`: their bags together ≥ `bag_min`;
  - `g_flip` (G3): their tributed + bags > ours;
  - `g_winbank`: their tributed + bags ≥ 1000.

  The enemy bags are the world's beliefs: last seen, emptied on death or on an inferred tribute.
- **L1.** `seek_steps`: a lock carrier within this walk of a site tile seen without our lock goes to lock it.
- **L2/L3.**
  - `holders` bodies by `holder_pick` (0 strongest, 1 a stunner first, 2 weakest; one body always farms) hold
    stand tiles within `hold_radius` (2) of the site. Stand tiles are off the tribute tiles, out of camp reach,
    bushes first.
  - A holder re-locks a missing tile, attacks an enemy lock on the site, and recalls or walks home to restock.
    The recall is kept for it. It heals at spawn through the usual mend and retreat.
  - With `timed`, its lock waits on an enemy channel at the site until our last turn before it lands
    (`last_round_before_channel_ends`, which uses our turn order) less `margin` turns. A winning tribute is never
    waited on.
  - `hold_near` / `hold_bag` / `hold_recent`: the holder holds only while an enemy carrying at least `hold_bag`
    gems was seen within `hold_near` of the site in the last `hold_recent` rounds, or a channel shows there.
    Otherwise it farms.
- **Extras.**
  - `stun_cancel`: the holder walks into stun reach of a stunnable channeller near its end.
  - `tavi_sell`: Tavi, short of a lock's price on spawn, sells a shard. Team gold counts a Tavi's shard.
  - `willow_holder`: Willow takes the stand next to the holder, where the turn end's heal reaches it.
  - `multi` (L4): every altar tile is the site.
- **Interactions.**
  - 408's guard runs when the enemy leads, or while we carry a winning bag (escort). In decide it runs before
    `plock_turn`, so a body both want is a guard.
  - Ocean already places a lock whenever a body with one passes within 2 of an on-side altar, which a one-tile
    site always is by symmetry. So the keep gate alone (L0) is a no-op on one-tile maps.

## Results

Everything is against `variants/oc-retest-clean`, own drafts, fast runner. Dev means the 3,204 games of
lock-one-dev. SPRT stops losers (`--sprt-stop low`).

### Wave 1: the user's gate (lead ≥ 1)

| Variant | Win % | Games | 95% CI |
|---|---|---|---|
| l0 keep only | 51.3 | 3204 | 49.6-53.1 |
| l1 + seek 12 | 48.6 | 1314 | 45.9-51.3 (H0) |
| h1 + 1 holder, immediate | 44.3 | 637 | 40.5-48.2 (H0) |
| h1t + 1 holder, timed (margin 1) | 44.3 | 601 | 40.3-48.3 (H0) |

How often it fires:
- The gate holds in 92% of one-site games, from a median round of 92 (lead 21, enemy bag 4), for 420-460
  rounds a game.
- The h1t holder places 1.5 locks a game and cancels about 0.2 more channels a game than l0/l1 (0.5 against
  0.3). A whole body for ~400 rounds buys almost nothing. altar.md's always-on guard read 44.0 the same way.

### When the gates hold: the observation run

`obs`: the keep gate always on, nothing else; 51.1% of 3,204. It logs every round's lead, bags and the enemy
tributes landing. (`results/gates-obs-dev.md`)

| gate | games fired | rounds a firing game | first round (median) | obs won when fired | enemy tributes landing while it held, a game (gems) | of which with our lock believed |
|---|---|---|---|---|---|---|
| lead ≥ 1 | 92% | 457 | 92 | 55% | 11.31 (316) | 2.55 (66) |
| lead ≥ 50 | 76% | 385 | 235 | 64% | 6.54 (191) | 1.56 (43) |
| bag ≥ 100 | 79% | 264 | 392 | 44% | 13.19 (459) | 2.82 (95) |
| bag ≥ 200 | 65% | 218 | 507 | 38% | 9.33 (325) | 1.91 (65) |
| bag ≥ 500 (G2) | 25% | 225 | 629 | 24% | 3.53 (115) | 0.69 (23) |
| sum ≥ 500 (G2) | 33% | 183 | 607 | 26% | 3.77 (124) | 0.75 (25) |
| lead ∧ bag ≥ 100 | 52% | 156 | 411 | 55% | 3.35 (100) | 0.78 (23) |
| lead ∧ bag ≥ 200 | 38% | 141 | 512 | 51% | 2.31 (70) | 0.51 (15) |
| lead ∧ bag ≥ 500 | 14% | 126 | 650 | 35% | 0.84 (25) | 0.16 (5) |
| lead ∧ flip (G3) | 84% | 141 | 134 | 53% | 4.91 (135) | 1.15 (30) |
| winbank (G3b) | 51% | 115 | 716 | 14% | 4.48 (199) | 0.93 (41) |
| lead ∧ winbank | 13% | 106 | 731 | 30% | 0.80 (24) | 0.16 (5) |

- The enemy lands 40.5 tributes a game (1,379 gems).
- While we lead it lands 11.3 a game, 8.8 of them with no lock of ours believed on the site.
- The big-bag gates fire mostly in games we go on to lose (G2 24%, winbank 14%). The small-lead gates fire in
  games that are open.

### Waves 2-4: narrower hold gates, timing, holders, tether, extras

The keep gate is lead ≥ 1 throughout. Holders are 1, timed with margin 1, seek 6, unless stated.

| Variant | Hold gate / change | Win % | Games | 95% CI |
|---|---|---|---|---|
| g1b100 | lead ∧ bag ≥ 100 | 48.9 | 1394 | 46.2-51.5 (H0) |
| g1b200 | lead ∧ bag ≥ 200 | 50.5 | 3204 | 48.8-52.3 |
| g3flip | lead ∧ flip | 48.7 | 1693 | 46.3-51.1 (H0) |
| sflip | lead ∧ flip, seek 8 only, no holder | 49.2 | 1823 | 46.9-51.5 (H0) |
| g2b500 | bag ≥ 500 alone | 51.1 | 3204 | 49.3-52.8 |
| g2s500 | sum ≥ 500 alone | 50.9 | 3204 | 49.2-52.7 |
| gwin | winbank alone | 51.2 | 3204 | 49.4-52.9 |
| gwin-imm | gwin, re-lock at once | 51.1 | 3204 | 49.4-52.9 |
| gwin-m0 / m3 | gwin, margin 0 / 3 | 51.1 / 51.2 | 3204 | |
| gwin-s0 | gwin, no seek | 51.2 | 3204 | |
| gwin-h2 | gwin, 2 holders | 50.7 | 3204 | 49.0-52.5 |
| gwin-weak | gwin, weakest holder | 51.0 | 3204 | |
| gwin-stun | gwin, stun_cancel, stunner holder | 50.9 | 3204 | |
| gwin-wil | gwin, willow_holder | 51.1 | 3204 | |
| gwin-tavi | gwin, tavi_sell | 50.6 | 3204 | |
| n8 | lead ≥ 1, holder tethered (hold_near 8, bag ≥ 20), seek 0 | 49.5 | 2171 | 47.4-51.6 (H0) |
| n8b50 | n8, bag ≥ 50 | 50.7 | 3204 | 48.9-52.4 |
| n12 | n8, hold_near 12 | 49.5 | 2172 | (H0) |
| n8imm | n8, immediate | 49.6 | 2164 | (H0) |
| n8stun | n8, stun_cancel, stunner holder | 48.7 | 1573 | (H0) |
| n8h2 | n8, 2 holders | 47.4 | 940 | 44.3-50.6 (H0) |
| n8l50 | n8, lead ≥ 50 | 51.4 | 3204 | 49.7-53.1 |

How often the hold gate fires: g1b200 38% of games (182 rounds each), g2b500 25% (269), g2s500 34% (222),
gwin 53% (135). The gwin variants differ from each other in a handful of winners: gwin-imm against gwin-m0 6,
m3 6, gwin 7, willow 20, no-seek 44, 2 holders 78.

### The ~51% readings are fuel noise

- Every oc-lock build, the no-op `l0` and `obs` included, read 50.6-51.4 at the real budget. The variants are one
  correlated draw: they share the code layout and most of their games.
- At 10M fuel a turn (both sides; no out-of-fuel turns at all, but every fuel check passes) and at 2x the
  budget (200k a turn, the engine's doubled first turn 400k; both sides; out-of-fuel turns ~270 a run against
  ~28k at the real budget). Dev, 10M:

  | Finalist | Win % | 95% CI | one-tile | 2-tile |
  |---|---|---|---|---|
  | gwin | 50.2 | 48.5-51.9 | 50.4 | 49.8 |
  | g2b500 | 49.9 | 48.2-51.7 | 49.9 | 50.0 |
  | n8l50 | 48.2 | 46.5-49.9 | 47.7 | 49.3 |

- 2x, dev: gwin 50.0 (48.3-51.8), g2b500 49.8 (48.1-51.5), n8l50 48.8 (47.1-50.6); one-tile 50.2 / 49.8 / 48.4.
- So the logic is level (gwin, g2b500) or a loss (n8l50).

### Firing of the extras

These are from dev runs.
- **Timed waits** (PLWAIT): 0.0-0.3 rounds a game. A holder rarely has a lock in hand while it sees a channel
  under way. When it does, the late lock lands:
  - 03membrane: held rounds 377-380 and placed at 381, against a last safe round of 382, cancelling 103 gems;
  - 00quarry: placed at 592 of 593;
  - one 03fan case waited and never placed.
- **Stun walks** (PLSTUN): 0.6 a game in n8stun.
- **Tavi sales** (PLSELL): 0. Team gold for a lock was never short.
- **Willow beside the holder**: changed 20 winners of 3,204 against gwin-imm.
- Locks placed while the gate held: 2.4-3.0 a game. Enemy gems in channels they cancelled: 100-500 a game. The
  Prism hoard restart loop dominates the totals: 00the-line cancelled 1,041-1,540-gem bags 5 times.

### Why it does not pay locally

- A lock costs the enemy 5 attacks. Each re-lock costs us a spawn trip, since a body carries one lock.
- A holder that keeps up costs a farmer:
  - under the lead gate it holds ~400 rounds a game, and the enemy lands nearly as many tributes (10.6 a game
    with the tethered holder, against 11.3);
  - under the big-bag gates, the game is usually decided when the gate fires (obs wins 14-24% there).
- The two sides of a mirror game both already lock on-side altars in passing, and both break locks on arrival.

## Confirm (held-out: fresh 541000-541039, ladder mix, 20,480 games; 128 ladder maps vs astraeus-now-1106)

Against `variants/oc-retest-clean` at the real budget, `maps/suites/merged/fresh-541000-541039`, both sides:

| Finalist | All | 95% CI | one-tile (4,554) | one-site 2-tile (1,946) | multi-altar (13,942) | OOF cand / ref |
|---|---|---|---|---|---|---|
| gwin | 49.9 | 49.2-50.6 | 49.6 | 49.2 | 50.1 | 160.8k / 159.7k |
| g2b500 | 49.9 | 49.2-50.5 | 49.7 | 48.9 | 50.1 | 161.1k / 159.7k |
| n8l50 | 49.7 | 49.0-50.4 | 48.7 | 48.0 | 50.2 | 162.0k / 161.9k |

The one-site splits are ±1.5 (one-tile) and ±2.2 (2-tile).

How often the hold gate fired:
- gwin: 3,491 of 20,480 games, 23 rounds a game;
- g2b500: 1,582 games, 21 rounds a game;
- n8l50: 4,893 games, 94 rounds a game.

The 128 ladder maps against `variants/astraeus-now-1106` (256 games):
- base 56.2 (50.1-62.2);
- g2b500 55.9;
- gwin 53.5;
- n8l50 52.7.

That is ±6, so no difference.

**No finalist passes the bar of a gain on one-altar maps with no loss on the full suite.**
- gwin and g2b500 show no significant loss anywhere (full suite, ladder against astraeus, 10M, 2x).
- n8l50 loses at 10M and 2x and reads 48.0-48.7 on held-out one-site maps.

L4 (`oc-lock-l4`: `multi`, keep our lock on every altar tile of maps with up to 8, keep gate only) on
`lock-multi-dev`: 49.8% of 2,022 (47.6-51.9), stopped by SPRT (H0). Not taken further.

Race-model gate (margin = P_them − P_us < k): not run, because `variants/oc-race` was not READY when this
round ended. It slots in as one more `gate_holds` bit beside G1-G3.

## Finalists

Frozen READY for the live gate against Fish and Mite, in priority order. Neither is a local gain; both are level
locally. They are worth the live gate only because Fish and Mite tribute and lock differently from our mirror
(LOSSES.md modes 4-5).
1. **`variants/oc-lock-gwin`**. Hold gate: winbank (their tributed plus known bags ≥ 1000). One holder, the
   strongest by type, timed with margin 1, seek 6. The keep gate is lead ≥ 1.
2. **`variants/oc-lock-g2b500`**. Hold gate: G2 (an enemy's last-seen bag ≥ 500), otherwise as gwin.

Dropped:
- every lead-gated holder or seeker (44-49.6);
- n8l50;
- holders 2;
- stun-first holders;
- the Tavi, Willow and stun extras (level or below, and rare).

The user's plain lead ≥ 1 gate with a dedicated holder (h1t) is the clearest loss: 44.3 on dev.

## Live gate

Not run: on 2026-11-06 the user ruled out live tests of the lock finalists until a variant is significant locally.
What happened before that ruling arrived:
- `variants/oc-lock-gwin` was submitted as **v79** at 08:12 UTC (`cambc submit`, the directory exactly: 52 `src/`
  files, source tree hash 82a9f752a758; a scratch copy built with `cambc build --release`). g2b500 (e111084a4764)
  was not submitted.
- 32 core tasks (`v79-v1core-*`, priority 100) were planned. All were dropped at 08:16:12 (`dropped` events in
  `events.jsonl`).
- To keep v79 off the ladder, v78 was pinned (`cambc submissions activate 78`). The team is now in "pinned
  version" mode, not "follow newest". v79 was live from about 08:15 to 08:16:17 UTC.
- One group was created anyway: `v79-v1core-fish-01` (01a1afee), at 08:16:15. The job had read its state before
  the drop. Its five games are byte-identical to v78's `v78-v1core-fish-01`: the same replays, our `.fuel`
  profiles and seeds. So **v78 played them**, though `games.jsonl` labels them version 79. Ignore them: `pair 78
  79` shows 5 paired games and 0 flips, which is no evidence about gwin.
- The v78 groups in flight over the switch were `v78-v1ext-fish-36`, `v78-v1ext-mite-36`,
  `v78-v1core-1s-neet-01` and `v78-v1core-1sf-vvvvv-01` (created 08:10-08:15). They are probably v78, given the
  case above, but they are not checked.
- For a later gate, the core set's one-site maps (this note's definition) are 17 of 40: 04sunburst, 03homonoliths,
  02treasure_box, 01boss_battle, 03ultrastarvation, 04spiral_moat, 03showdown, 02guardians, adgato_gemcombat5,
  04two_kingdoms, 03colosseum, 00quarry, 00eight, 02the_pack, 04plaza, 04compass and 00breadcrumbs. On these, v78
  went Fish 19/34 and Mite 20/34; on the other 23 maps, 21/46 and 27/46.

## Round 2: forensics (before designing)

The user's reading of round 1: the gate was too weak, not the idea. Before new designs, what broke in the games we
led and lost. Self-play on `maps/suites/merged/lock-one-fx` (401 one-site maps, every fourth of lock-one-dev, both
sides: 802 games), real budget, extracted with `tools/replay/extract.mjs` and classified by `lock-tools/fx.py`.
Two runs against oc-retest-clean:
- `oc-lock-obs`: the gate logs, nothing acts (= normal play): 50.0%.
- `oc-lock-h1t`: the user's lead ≥ 1 gate, one timed holder, seek 12: 46.1%.

Every enemy tribute that landed while we led (at the channel's start), classed by the first that applies:
- `short`: a channel of at most 1 turn end (no lock can be timed into it);
- `in_reach`: one of our lock carriers within 3 of the altar during the channel;
- `late`: a carrier within 4-8 (on its way);
- `no_lock`: a body of ours within 8, none carrying a lock (the spawn trip);
- `away`: none of ours within 8.

And the lock's history on that tile: `broken` (ours there within the 10 rounds before), `absent` (none for 10+
rounds), `other_tile` (a 2-tile site, ours on the other tile). "Flippable" is the enemy's carried gems at the
start already exceeding our lead.

**obs** (normal play): 6,069 landings while we led, 207,411 gems.

| class | lock history | tributes | gems | flipped the lead | flippable at start | in games we lost |
|---|---|---|---|---|---|---|
| late | broken | 1230 | 54571 | 309 | 892 | 528 |
| away | broken | 911 | 38496 | 223 | 770 | 447 |
| short | broken | 654 | 3676 | 42 | 432 | 271 |
| no_lock | absent | 522 | 18687 | 208 | 476 | 253 |
| away | absent | 506 | 21266 | 157 | 463 | 305 |
| no_lock | broken | 464 | 15936 | 124 | 381 | 217 |
| late | absent | 458 | 18999 | 142 | 377 | 236 |
| short | absent | 392 | 2435 | 31 | 324 | 206 |
| late | other_tile | 257 | 11791 | 69 | 200 | 130 |
| away | other_tile | 210 | 7846 | 60 | 181 | 100 |
| short | other_tile | 146 | 848 | 10 | 108 | 74 |
| no_lock | other_tile | 146 | 5093 | 47 | 121 | 55 |
| in_reach | broken | 121 | 5352 | 24 | 80 | 47 |
| in_reach | absent | 28 | 1562 | 10 | 25 | 15 |
| in_reach | other_tile | 24 | 853 | 7 | 21 | 14 |

- 2+ of ours dead at the channel's start: 1,431. Channels of 10+ turns: 187.
- 324 games led at some point and lost; the enemy reached 1000 in 311 of them. The last round led: median 482.
  Only 41 lost games led after round 1000, 5 after 1500.
- Lead-flipping landings in lost games: 833 (late 299, away 277, no_lock 187, short 48, in_reach 22).

**h1t** (a holder): 5,643 landings while we led, 194,193 gems.

| class | lock history | tributes | gems | flipped the lead | flippable at start | in games we lost |
|---|---|---|---|---|---|---|
| late | broken | 1575 | 67576 | 436 | 1218 | 812 |
| away | broken | 720 | 28043 | 247 | 638 | 440 |
| short | broken | 713 | 4091 | 48 | 469 | 354 |
| no_lock | broken | 473 | 18109 | 165 | 399 | 269 |
| no_lock | absent | 401 | 14774 | 161 | 366 | 226 |
| away | absent | 337 | 12088 | 130 | 305 | 214 |
| in_reach | broken | 315 | 11856 | 77 | 233 | 145 |
| late | absent | 307 | 17921 | 102 | 256 | 191 |
| short | absent | 293 | 1865 | 34 | 243 | 177 |
| late | other_tile | 174 | 7552 | 65 | 153 | 120 |
| away | other_tile | 131 | 5278 | 49 | 125 | 81 |
| short | other_tile | 85 | 481 | 8 | 59 | 53 |
| no_lock | other_tile | 82 | 2825 | 33 | 76 | 47 |
| in_reach | absent | 27 | 1473 | 11 | 24 | 15 |
| in_reach | other_tile | 10 | 261 | 2 | 7 | 8 |

- 374 games led and lost (enemy at 1000 in 357); last led median 485; 47 led after round 1000, 10 after 1500.
- Lead-flipping landings in lost games: 942 (late 381, away 275, no_lock 186, in_reach 51, short 49).

What broke:
- **The lock was broken with nobody close enough to re-lock** (late, away and no_lock after `broken`): the
  dominant class in both runs. One holder moves landings from `absent` to `broken`: the holder locks, the enemy
  breaks it (they come in a group), the holder is beaten or late. Landings fell 7% and the gems 6%, but flips in
  lost games rose 13%.
- **The spawn trip** (`no_lock`): a body by the site with no lock: 1,132 (obs), 956 (h1t).
- **The holder dead or away**: `away` with 2+ of ours dead is most of the 1,386-1,431.
- **In reach and still landed** (`in_reach`): rare (173 obs, 352 h1t): the holder there but beaten or held off.
- **Short channels**: 1-turn tributes cannot be timed at all; only a standing lock blocks them.
- **Flippable at the start**: 80% of the landings while we led came from a carried total already above our
  lead: a gate on "the lead is safe from their bags" excludes most of the games these losses come from.
- **Leads are lost early.** The median last round led in a lost game is ~480, and the enemy wins by reaching 1000,
  not at round 2000. A "hold to 2000" gate reaches few of these games.

Leader win rate in normal play (obs, the leading side by tributed gems at the round):

| round | games reaching it | lead 1-49 | lead 50-199 | lead 200+ |
|---|---|---|---|---|
| 250 | 802 | 53% of 354 | 58% of 361 | 86% of 49 |
| 500 | 762 | 56% of 188 | 66% of 354 | 81% of 194 |
| 750 | 540 | 66% of 87 | 67% of 205 | 85% of 224 |
| 1000 | 296 | 38% of 39 | 73% of 74 | 92% of 169 |
| 1250 | 154 | 33% of 15 | 64% of 39 | 97% of 89 |
| 1500 | 81 | 67% of 6 | 83% of 18 | 96% of 53 |
| 1700 | 47 | 60% of 5 | 89% of 9 | 93% of 29 |
| 1850 | 37 | 100% of 2 | 100% of 5 | 96% of 26 |

A late "guaranteed hold" gate (T = 1500-1850) can reach at most 5-10% of one-site games, and the leader there
already wins 93-96%. The room is in rounds 500-1250 with leads under 200.

### The win models (P(win | state))

`lock-tools/states.py` writes a state every 25 rounds from extracted replays: round, lead, carried gems (ours,
theirs, their biggest bag), gold, earned gold, alive, hp, strength, kills, locks carried, distances to the site,
whose lock is on it, the outcome and whether the enemy landed any more gems. `lock-tools/fit.py` fits a logistic
(game-grouped 5-fold CV).
- Normal play (obs, both sides: 56,200 states from round 100): CV log loss 0.463 (constant 0.693), AUC 0.864.
  The lead counts by the round (L × t, +1.04 per 100 gems at t = 1), their carried gems by −0.25 + 0.43 t, earned
  gold, kills and hp each about +0.9.
- h1t's leading states (13,437): it won 66.4% of them, where the normal model predicts 68.9% (−2.4 points). It is
  below normal play in almost every round and lead cell, including late big leads (round 1000-1500, lead 200+:
  −4 to −6 points): the holder's lost farm costs more than the lock saves. By enemy champion it is worst against
  Tavi (−37 points, 363 states), Vendetta and Varg (−6).

## Round 2: holds at 2x fuel (screens on lock-one-dev, 3,204 games each)

From 2026-11-06 every idea is screened at 2x fuel first (200k a turn, 400k on the first, both sides), against
oc-retest-clean on `maps/suites/merged/lock-one-dev` (1,602 one-site maps, both sides). Knobs added to
oc-lock-dev for round 2 (all off by default; bench.py 16/16 and 52/52 identical at 100M with them off):
- `allhands` 1/2/3 (all hands always; while an enemy was seen within `defend_d` of the site; a holder plus
  the rest as 2), `fight_leash` (holders chase visible enemies within it), `bank_first` (a holder banks its own
  bag at the site first);
- `tail`/`tail_bag` (the last-ranked holder shadows their biggest bag); `rotate_k`/`rotate_d` (recall
  rotation: a holder leaves for a lock only while every other ally is near the site, at least k of them);
- gate bits `g_safe` (lead > their bags), `g_rscale` with `rscale_c`/`rscale_p` (lead − bags ≥ c × 2000 ×
  (rounds left / 2000)^p: convex for p > 1), `g_race`/`g_race_late` (the race model, `model/race.{h,cc}` from
  `variants/oc-race`, behind `race`), `g_noburst` (veto while their bags flip the lead and their burst kills our
  group before a break plus the flipping channel), `g_fight` (veto while their burst kills us sooner than ours
  kills them), `g_model` (a learned linear score ≥ `model_z` with weights `model_w`).

**Paired reading.** A gate changes nothing before it first fires, and local games are deterministic, so a
variant's game and normal play's game on the same map and side are identical up to the first firing.
`lock-tools/paired.py` pairs a variant's batch with `oc-lock-obs2` (normal play with the race model's trace,
50.1% of 3,204) and counts, among the games where the hold fired, the wins it gained and lost. In the games
where the gate never fired the two agree 98.6-98.8% (fuel noise flips the rest), so it reads far finer than a
win rate.

All-hands variants hold with `seek_steps` 12 and `fight_leash` 6 unless noted. "Net" is gained − lost among
the games where the hold fired (paired against obs2); "fired" is those games.

| variant | behaviour | gate | win % (3,204) | fired | normal won / variant won | net |
|---|---|---|---|---|---|---|
| obs2 | normal play (race trace) | - | 50.1 | - | - | - |
| ah1 | all hands | lead ≥ 1 | 20.1 | | | |
| ah1n | all hands, no chase | lead ≥ 1 | 17.2 | | | |
| ah1r | all hands | lead ∧ race `we_win` | 20.4 | | | |
| a1rl | all hands | lead ∧ their projected win past 2000 | 25.0 | | | |
| a1f0 | all hands | lead ∧ fight veto | 20.5 | | | |
| ah2 | all hands while an enemy within 10 | lead ≥ 1 | 36.8 | | | |
| a2f | as ah2 | lead ∧ fight veto | 38.2 | | | |
| ah3 | a holder, the rest as ah2 | lead ≥ 1 | 36.1 | | | |
| h1f | one holder (round 1's) | lead ∧ fight veto | 45.7 | | | |
| ah1t | all hands | lead, from round 1000 | 48.2 | 716 | 556 / 509 | −47 |
| a1f | all hands | as ah1t ∧ fight veto | 48.3 | 715 | 556 / 512 | −44 |
| a1nb | all hands | as ah1t ∧ burst veto | 47.8 | 714 | 555 / 495 | −60 |
| a1rt10 | all hands | lead ∧ race, from 1000 | 48.0 | | | |
| a1t15 | all hands | lead, from 1500 | 49.8 | 197 | 167 / 160 | −7 |
| a1t15b | as a1t15, banking first | lead, from 1500 | 49.9 | 197 | 167 / 163 | −4 |
| a2t15 | as ah2 | lead, from 1500 | 50.0 | 197 | 167 / 166 | −1 |
| a1t17 | all hands | lead, from 1700 | 50.0 | 126 | 111 / 112 | +1 |
| a1t185 | all hands | lead, from 1850 | 49.9 | 83 | 76 / 74 | −2 |
| a1c2 | all hands | convex: lead − bags ≥ 0.5 × 2000 (left/2000)² | 49.3 | 1152 | 1074 / 1061 | −13 |
| a1c2l | all hands | as a1c2, c = 0.25 | 47.6 | 1526 | 1340 / 1274 | −66 |
| a1c3 | all hands | lead − bags ≥ 2000 (left/2000)³ | 49.0 | 990 | 919 / 894 | −25 |
| h1c2 | one holder | as a1c2 | 49.8 | 1152 | 1074 / 1076 | +2 |
| a1ev | all hands | learned EV gate (below), z = 0 | 49.5 | 533 | 319 / 301 | −18 |
| a1ev5 | all hands | as a1ev, z = −0.5 | 47.1 | | | |

Round 1's finalists at 2x: gwin 50.0, g2b500 49.8, n8l50 48.8.

What the paired games show:
- **No state where holding gains.** With all hands from round 1000, the fired games lose in every cell of
  round × lead, by the enemy's tributed gems (0-800+), by ours, and whether their bags could flip the lead
  (bags ≤ lead: 455 won normally, 426 holding). Late gates (from 1500, 1700, 1850) fire in 3-6% of games, where
  normal play already wins 85-92%, and read level.
- **Why the hold breaks** (ah1t's 99 games lost that normal play won): 1,069 enemy landings, 729 with our lock
  believed off. In the 10 rounds before a landing our bodies' decisions were 42% none (dead or unable to act), 25%
  holding, 14% retreating. The enemy kills the group at the site, breaks the lock and lands. Holding stops our
  farm while theirs goes on, so the fight at the site gets worse the longer the hold lasts.
- **The fight and burst vetoes don't help.** The burst veto (their burst kills our group before 5 hits plus the
  flipping bag's channel) fired in about half the gated games, about evenly by enemy champion, Marcella no more
  than the others (a1nb):

  | enemy champion | games the veto fired in / gated games | veto rounds |
  |---|---|---|
  | Cassi & Issac | 313 / 614 | 42,990 |
  | Prism | 291 / 522 | 44,254 |
  | Vesper Vale | 227 / 432 | 27,267 |
  | Heart of Ruin | 205 / 398 | 25,349 |
  | Marcella | 139 / 335 | 19,975 |
  | Willow | 141 / 318 | 19,377 |
  | Ren | 83 / 149 | 10,721 |
  | Vendetta | 81 / 140 | 9,510 |
  | Ryth | 66 / 152 | 7,523 |
  | Varg, Tavi, Stellar | 29 / 59 | 3,966 |

  The fight veto (a1f) fires about as often.
- **The learned EV gate.** Logistics on what the bot can read (lead, lead × t, their bags and × t, biggest bag,
  our bags, both scores, alive difference, whose lock, t), fit by `lock-tools/fit.py --obs`:
  - P(win | normal), from obs2's 226,560 states (both sides): CV log loss 0.478, AUC 0.854.
  - P(win | all hands), from ah1's 65,137 leading states: AUC 0.872.
  - All hands beat normal play on 1.4% of all hands' states, all in the last ~250 rounds (t weight +2.97).
  - The EV gate (`g_model`, weights = the difference of the two logistics) fired in 533 games: −18.
- **Composition.** In the state model, all hands (ah1) against normal play is negative against every enemy
  champion: −19 to −37 points of win probability on its states. There is no composition where holding pays.

### Against bots/fish (paired with obs2 vs fish, 82.7% of 3,204 at 2x)

The live losses that motivated the idea were to Fish, which tributes and locks unlike our mirror. Against the
sparring copy (`bots/fish`, round 1):

| variant | win % | fired | normal won / variant won | net |
|---|---|---|---|---|
| gwin | 82.5 | 682 | 195 / 183 | −12 |
| n8l50 | 82.7 | | | |
| a1t15 | 82.6 | 170 | 157 / 157 | 0 |
| a1f | 81.5 | 720 | 654 / 620 | −34 |
| ah1t | 81.3 | 720 | 654 / 613 | −41 |
| a1c2 | 80.3 | 2014 | 1957 / 1889 | −68 |
| h1t | 77.9 | 3093 | 2622 / 2471 | −151 |

### The cooked mirror (guard when far behind)

`g_cooked`: they lead by `cook_gap` (200) with `cook_min` (600) tributed. That is cooked in 2,468 of obs2's 3,204
games, with a 9.4% comeback rate; at the median the cook comes at round 750 with 130 rounds left. The behaviour
is the same infrastructure on the hold gate only:
- every body at the site, on stands (bush first, out of camp reach);
- chasing within the leash;
- stun-cancelling channels;
- a timed lock.

`bait` keeps no standing lock: their channel is let start, then the channeller is struck in the open, stunned,
or cancelled by a lock at its last turn. Bait-and-snipe, the coordinator's idea, with all-hands cover.

| variant | behaviour | win % | fired | comebacks normal / variant | net |
|---|---|---|---|---|---|
| ck1 | all hands, standing lock | 49.6 | 1240 | 126 / 106 | −20 |
| ck1b | all hands, bait | 49.8 | 1245 | 133 / 113 | −20 |
| ck1bl | as ck1b, leash 10 | 49.8 | 1245 | 133 / 113 | −20 |
| ck2 | all hands while an enemy near, standing lock | 49.8 | 1240 | 126 / 111 | −15 |
| ck2b | as ck2, bait | 50.0 | 1245 | 133 / 119 | −14 |
| ck1e | as ck1, cooked at 150 behind with 400 | 48.7 | 1586 | 270 / 220 | −50 |

Guarding the site when cooked lowers the comeback rate. Comebacks come from kills on the leader's carriers away
from the site, and from farming (`research/ideas-2026-11-05/comeback.md`, a separate agent's programme). It was
not taken further here: that programme already covers hunting, ambush, snipes and carrier targeting.

### Verdict (round 2)

The grid is exhausted with no winner. At 2x fuel, no gate, holding behaviour or cooked mirror is positive on
paired games, in self-play or against bots/fish. Nothing reached SPRT significance, so nothing went to a
real-budget or held-out confirm. Round 2 ran no SPRT, so the shared `--sprt-seed` caveat does not apply. Round 1's
SPRTs all ended level or H0.

The reason is structural:
- A hold trades the farm for the site. The enemy keeps farming, then wins the fight at the site, kills the
  holders, breaks the lock and lands.
- The states where a hold is safe are late, big-lead states, which normal play already wins 85-97% of the time.

Variants under `bots/variants/oc-lock-*` (round 2: ah*, a1*, a2*, h1c2, h1f, ck*, obs2); oc-lock-dev keeps every
knob, off by default.
