# Macro and altar fixes for the Fish/Mite losses (2026-11-06)

LOSSES.md's candidates 1 (channel interrupt), 5 (lock war), 7 (separate-altar maps) and 8 (endgame) as
off-by-default knobs in `bots/variants/oc-fixm-dev` (from `variants/oc-retest-clean` = `bots/ocean` = live v78),
namespace `params::fixm::`. The combat candidates (2-4) are fix-combat.md's.

## Method

Puppet re-runs: `tools/replay/harness/inputs.mjs` + `gen_puppet.mjs` turn a scrim replay's opponent inputs into a
bot, and our bot plays it on the map (`cambc run`). A release build of oc-retest-clean reproduces the ladder game
exactly (03homonoliths-a: Fish wins at r729 with 1,200 gems; 03colosseum-a: r1999, 1003-0). A debug build with
`debug_block` traces reproduces it in some games (03homonoliths-a/b, 00reverse_spiral-a, 04wheel-a, 04plaza-b,
00quarry-b) and diverges early through fuel in the others. After our first changed decision the puppet's inputs
no longer fit the game, so a re-run shows what we decide, not who wins.

## 1. Channel interrupt

### What happens now

- `game_ender` (fight.cc) already sends a body that sees a game-winning enemy bag into lock or stun reach
  (`stop_game_ender`, decision `E`), whatever the risk. Nothing reacts to a long channel that does not win.
- **03homonoliths-a (the 1,200-gem channel, r609-729).** Our Vesper respawned at r650 and was in `E` from r655
  to r721, but it stood still: from r663 it alternated (8,12) and (7,13) for 60 rounds. Trace
  (`STF` lines in `step_towards_funded`):
  - at (7,13) the travel dash is allowed and the route crosses the hole line by a dash: 8 steps, first step (8,12);
  - at (8,12) Fish's Vesper is within `travel_dash_clearance` (vision + dash = 10, by terrain), so
    `travel_dash()` withholds the dash, the route is on foot (21 steps), and its first step is back to (7,13).
  The other three bodies (Cassi, Issac, Prism) were sieging the home Monolith at spawn and never saw the
  channel (vision is personal).
- 03homonoliths-b (r597-610): Fish's Vesper channelled 600 gems at (18,18), not a winning bag (0 + 600).
  Our champion 6 watched it from 2-4 tiles for 14 rounds and did nothing; two lock carriers were 8 tiles away.
- 04plaza-b r398: a 221-gem channel, our lock carriers 6-8 tiles away, no reaction.
- `altar_guard.cc` runs only when the map has exactly one altar tile (`guarded_altar`, `escorting`).
  00quarry, 03homonoliths and 04plaza have 2 adjacent tiles; 03the_front a vertical line of 34 tiles linked
  within 3 of each other.

### Changes

- **`fixm::ender_route`** (bool). While `stop_game_ender` walks (and the deny walk below), `travel_dash()`
  never withholds the dash: the route is the same from every tile, so it cannot alternate. A dash is part of
  the "whatever the risk" walk.
- **`fixm::deny_gems`** (int, 0 = off; tried at 100). A visible enemy tribute channel of at least this many
  gems that does not end the game is stopped like a game ender when:
  - we carry a hard stop: a lock (and our team has no lock on that altar), or a ready stun on a stunnable
    channeller;
  - `intercept_steps` says we stop it before it lands (the same Chebyshev estimate `game_ender` uses);
  - what our death would hand over (`bag_at_stake`) is under `max(fixm::deny_own_bag, its bag / 3)`
    (`deny_own_bag` 40): a Prism hoard or a big carrier does not walk into their pack for it;
  - we are not retreating: it runs after `want_home`'s retreat, not before it as `game_ender` does.
  It takes the nearest such channel, and reuses `stop_game_ender`'s walk and acts (lock, stun, attacks).
  A lock cancels every channel at that altar, so one arrival is enough.
- **`fixm::site_guard`** (bool). altar_guard's one-altar test becomes one *site*: all altars linked by
  Chebyshev distance 3 or less. The guarded altar is the site's altar nearest the enemy spawn by walk (its
  tributes go to their nearest altar), ties by our walk; stands and the leash are around it, and
  `keep_guard_lock` holds for every site altar within 3 of it, so guards with locks lock both of 2-tile sites.
  This turns on the cooked guard and the escort on 00quarry, 03homonoliths, 04plaza and 03the_front.

## 2. Lock war (`fixm::lock_break`, `fixm::lock_seek`)

### Evidence

`fixm/lockprox.py` (scratchpad) over the 1-9 games and 00quarry: rounds a Fish lock stood on an altar, and rounds
one of ours stood within 3 of it with no Fish champion within 4 ("free"):

| game | lock rounds | ours within 3 | of those free | ours within 8, free | Fish locks we broke / placed |
|---|---|---|---|---|---|
| 04sunburst-a | 847 | 105 | 55 | 125 | 1 / 2 |
| 04sunburst-b | 925 | 262 | 150 | 366 | 8 / 9 |
| 04wheel-a | 2,663 | 390 | 341 | 1,375 | 1 / 4 |
| 04bowls-a | 1,003 | 102 | 68 | 230 | 3 / 6 |
| 04courtyard-a | 1,255 | 118 | 70 | 282 | 5 / 8 |
| 01boss_battle-b | 984 | 245 | 68 | 266 | 5 / 6 |
| 00quarry-a | 1,319 | 310 | 217 | 702 | 2 / 4 |

Five hits remove a lock. We stand within reach of Fish's lock for tens to hundreds of free rounds and break it
only when a carrier banks there (`bank_gems`' `break_lock` on the altar it aims for).

### Changes

- **`fixm::lock_break`** (bool): at the turn's end, before `place_lock`, a body with its basic attack unspent hits
  a visible enemy lock in attack range on an altar on our side (`our_side`: our walk at most 2 longer than
  theirs, which includes shared middle altars). A ranged body has the attack only if it did not walk. Then
  `place_lock` re-locks there as now.
- **`fixm::lock_seek`** (int steps, 0 = off; tried at 8): a body without a bag (none at stake), not holding a
  capture, with no visible enemy champion within 6 of it or of the altar and no visible ally already within
  attack range of that lock, goes to break a believed enemy lock on an our-side altar within this many steps, and
  hits it from a tile within its attack range (within 2 when it carries a lock, so the re-lock lands on arrival).
  It runs where the farm would, after the chase and contest branches.

## 3. Separate-altar maps (`fixm::funnel_power`, `fixm::sep_chain_bag`)

Separate-altar map: the altar nearest our spawn (walk to a tile beside it) is more than `fixm::sep_gap` (4)
steps further from the enemy spawn than from ours: Fish's lock rule's complement, computed once per game.

- **`fixm::funnel_power`** (float, 1 = off; tried at 2): there, `relative_efficiency` (CHANGES 414's
  efficiency over the team mean, used by farm's gold price and capture holder choice) is raised to this power,
  so the richest body takes more of the gold. Fish's top earner takes 0.55-0.57 of team gold, ours 0.39-0.45.
- **`fixm::sep_chain_bag`** (int, 0 = off; tried at 45): there, `may_chain`'s bag limit (`chain_bag_limit`, 26)
  is this, so a carrier chains more captures before banking. Fish banks 35 gems a tribute there, we 21.

## 4. Endgame finish (`fixm::finish_wait`)

### 03colosseum-a

Release puppet re-run (exact) and a release trace build (diverges after ~r510, so read only up to there):
- From r499 we had 996 tributed. Prism carried 146 (a winning bag, a 15-turn channel) at (24,26) beside the one
  altar (25,25) and waited (`W`) until r1983. `tribute_safe` refused every turn: Fish's 6 bodies stood ~6 tiles
  away for 1,500 rounds and could have killed it within the 10-turn window. With one altar, `carry_bag`'s wait has
  no other altar to give up for, so it waits forever. The escort (CHANGES 408) held Ryth, Marcella and Willow on
  stand tiles.
- The capture-reset loop is Issac on group 23, a lone gem cluster at (25,23): farm (`F`) steps onto it, the next
  turn retreats (`R`) off it, 565 times; Cassi did the same on group 25 (27,25). Ryth and Willow, guards within
  leash of Fish's pack, ran out of fuel on about every other turn (709 and 652 rollovers): `guard_turn` runs
  `chase` every turn while any enemy is within 6.

### Change

- **`fixm::finish_wait`** (rounds, 0 = off; tried at 20): a winning bag that has waited at an altar this many
  rounds starts its tribute there when it took no damage last round and `Safety::threatened` is false on its
  tile, instead of needing no possible kill within the window. `continue_tribute` already keeps a channel while
  no damage comes and `want_home` stays false, and cancels it otherwise, so the start risks only standing still
  while nothing hits. This ends the game the loop above otherwise runs to r2000; the loop itself (a
  farm/retreat oscillation under fuel exhaustion) is left alone.

## 5. Big bags (the user's A, B1-B4 and C)

### Why ocean's bags reach 2-3k

`fixm/bags.py` and `fixm/cancels.py` (scratchpad) over the 160 scrim games, our bodies whose bag reached 500+ in a
loss: 13 bodies made **35 tribute starts with 500+ gems, and none finished**. 31 of the 38 cancels were our own
(`manual`), 4 were stuns and 3 locks. 14 deaths handed over 14,532 gems.
- **Who decides.** A carrier tributes when `carry_bag` finds `can_tribute_safely`:
  - not `retaining_gems`: Prism keeps its bag for Focus until it wins or the game is closing;
  - then `tribute_ok`: `tribute_safe` asks only that no enemy could kill us within `min(turns, tribute_window = 10)`
    turns.
  - `continue_tribute` judges the channel again each turn. Once that 10-turn test fails it cancels on damage,
    `want_home`, a target in range or prey.
  - So a 200-turn channel needs about 200 turns in a row with no enemy within ~10 turns of striking. It starts
    whenever the next 10 look clear, and is cancelled when someone comes.
- **Where the gems come from.** Kills: a kill takes the victim's whole bag. The 13 bodies took 16,741 gems by kills.
  On **01boss_battle (one altar, (25,20))** both teams fight at the altar and the bags pass back and forth:
  - vs Mite (a): our lock cancelled Mite's Vesper's 1,844 at r587, and we killed it carrying 1,893 at r634. Our
    Vesper then held 2,559, a 172-turn channel. We cancelled it at r709 with Mite at 3, and it died with 2,618 at r745.
  - vs Mite (b): Vesper's bag went 361 → 761 → 1,818 → 1,882 → 2,384 → 2,656 → 3,056 over 9 starts. It ran 1-72
    turns of channels of 25-206 turns, cancelled with Mite within 2-9 (7 by us, 2 by stuns), until the 3,056 death.
- **The Prism hoard** (02the_pond-a, two altars): 627-767 gems from captures, kept for Focus, then 9 starts of
  63-77-turn channels, cancelled with Mite within 1-8 (7 by us, 1 stun, 1 lock). It died with 639 and 767.
  - 03homonoliths-a: its 600 from the r280 capture was kept until a lock cancelled its first channel at r584. It
    made 4 more starts under fire and died at r604, and that bag became Fish's 1,200.

So the long channel is unwinnable where the enemy stays near the altar. Each restart only stands a carrier still
while a pack gathers. The levers are a smaller bag (A), another altar (B1), cover (B2), and removing the pack (B3/C).

### Changes (all off by default)

Enemy arrival at a tile is `strike_eta`: the fewest turns after which a credible enemy could strike it
(`Safety::may_reach_within`, binary search, up to `eta_cap` 120).
- **A, `finish_margin`** (-1 off; tried 5), `finish_growth` (50): Prism keeps its bag for Focus only while a bag 50
  gems bigger would still finish at the nearest altar `finish_margin` turns before arrival. Otherwise it banks now
  (`note_finish` at the turn start; `retaining_gems` reads it). This is threat-relative: with no one near it keeps
  hoarding, up to the 120-turn horizon (about 1,100 gems minus the walk).
- **B1, `safe_bag`** (0 off; tried 150), with `safe_min_turns` 10:
  - For a bag that size, `bank_gems` aims for the altar with the best score:
    arrival − channel − (1 + `safe_walk_w`)·walk + `safe_cover_w`·(allies seen within 3) + `safe_home` (the home altar).
  - It switches only if that beats the nearest altar's score by `safe_switch` (4).
  - `carry_bag` stops waiting at an altar when another scores better.
  - Tried: walk weight 0.5, cover 4 per ally, home bonus 6 (with the escort).
- **Escort base**: `site_guard`; `escort_bag` 300 (the 408 escort also for any team bag of 300+, as seen or posted,
  not only a winning one); `escort_multi` (multi-altar maps escort at the *home altar*: the most our side's, their
  walk less ours). Comms has no room for a carrier's altar, so the team derives the same static one, and B1's
  `safe_home` pulls the carrier there.
- **B2, `cover_n`** (0 off; tried 2), `cover_r` (5): while escorting, the first `cover_n` guards do not use the stands
  by the altar. They stand on the ring `cover_r` from it, on tiles nearest the enemy spawn (their way in), bushes
  first, at least 3 apart: they meet whoever would come into sight of the channel.
- **B3, `clear_leash`** (0 = `altar_leash` 6; tried 8), **`clear_aggr`** (0/1): escorts fight enemies within the leash
  of the held altar. With `clear_aggr`, an escort whose `chase` declined walks at the nearest such enemy (no step
  guard), casts and attacks.
- **C, `clear_carrier`**: the winning carrier under escort fights (`chase`) an enemy within the leash beside an ally,
  rather than wait (Prism's Focus burst).

Variants (`mkvar.py`): `bankfin` (A), `b1`, `esc` (escort base), `b2` (esc + cover), `b3` (esc + clear), `c` (b3 +
carrier), `b12`, `b13`, `b123` (B1 + home bonus + the others).

## Tests

- Identity: with every knob off, `tools/fuel/bench.py` replays at 100M equal oc-retest-clean's, default and wide sets.
- Behaviour: puppet re-runs and local games on the problem maps, with debug lines on the new branches.
- No harm: each knob against oc-retest-clean on fresh ladder-mix suites 538000-538039 (20,480 games), and the 128
  ladder maps both sides against astraeus-now-1106. Bar: CI upper bound at least 50, point at least ~49.5.

## Results

**Identity.** With every knob off, oc-fixm-dev's `tools/fuel/bench.py` replays at 100M equal oc-retest-clean's:
16/16 default and 52/52 wide (`--set wide --test-draft`), after the last code change.

**Behaviour (puppet re-runs).**
- 03homonoliths-a with `ender_route`: the lock lands at r668 ((18,17)), cancels Fish's 1,200-gem channel, and we
  take the game (r805). It took the reorder: under the knob, a body holding a hard stop walks to the lock or stun
  tiles before it acts, since a ranged attack spends the walk.
- DENY fired on 04plaza-b (r398) and 04wheel-a (r901). In the 03homonoliths-b re-run the game had diverged, and our
  bodies were 8-13 away and banking.
- The site guard's `U` fired on 00quarry, 03homonoliths and 04plaza.
- All big-bag knobs on (6 games): CLEAR, FINISH and SAFEALT fire, and `U` takes 900-1,500 turns on 01boss_battle.

**Screens** (SPRT H0 48.5 vs H1 50.5, both stops, against oc-retest-clean, `--no-test-draft`, fresh ladder-mix
538000-538009, 5,120 games at most; out-of-fuel turns CAND/REF):

| variant | knobs | win % (games) | 95% CI | SPRT | OOF |
|---|---|---|---|---|---|
| lockwar | lock_break, lock_seek 8 | 51.0 (2,278) | 48.9-53.0 | H1 | 16,466 / 16,121 |
| funnel | funnel_power 2, sep_chain_bag 45 | 50.7 (2,405) | 48.7-52.7 | H1 | 17,619 / 16,700 |
| finish | finish_wait 20 | 50.1 (2,367) | 48.1-52.2 | H1 | 16,278 / 16,270 |
| b1 | safe_bag 150, walk_w 0.5, cover_w 4 | 50.0 (2,100) | 47.8-52.1 | H1 | 14,299 / 14,009 |
| site | site_guard | 50.0 (2,021) | 47.8-52.2 | H1 | 14,269 / 13,912 |
| escw | site_guard, escort_multi | 50.2 (4,907) | 48.8-51.6 | H1 | 39,604 / 36,078 |
| b3w | site_guard, clear_leash 8, clear_aggr 1 | 50.0 (2,298) | 47.9-52.0 | H1 | 16,662 / 16,250 |
| b2w | site_guard, cover_n 2 | 50.1 (2,005) | 47.9-52.3 | H1 | 14,408 / 13,869 |
| interrupt | ender_route, deny_gems 100, site_guard | 49.1 (5,120) | 47.7-50.5 | undecided | 38,580 / 37,401 |
| deny | ender_route, deny_gems 100 | 49.2 (5,120) | 47.9-50.6 | undecided | 37,801 / 37,294 |
| route | ender_route | 49.1 (5,069) | 47.7-50.5 | H0 | 36,698 / 36,405 |
| esc2 | site, escort_bag 300 (not Prism's), multi | 49.6 (5,120) | 48.2-50.9 | undecided | 40,771 / 37,129 |
| bankfin2 | finish_margin 5, finish_min 200 | 46.3 (2,097) | 44.1-48.4 | H0 | 14,196 / 14,169 |
| bankfin | finish_margin 5 | 39.5 (2,033) | 37.4-41.6 | H0 | 14,201 / 14,585 |
| esc | site, escort_bag 300 (any), multi | 41.5 (2,307) | 39.5-43.5 | H0 | 18,761 / 16,764 |
| b2, b3, c, b12, b13, b123 | esc + cover / clear / carrier / B1 | 41.0-42.0 | | H0 | +10-17% |

- The escort for any 300+ bag is what sank esc and all its combinations: it counted Prism's Focus hoard, so the
  three strongest bodies stood at the altar for most of the game. Counting only non-Prism bags (esc2) brings it to
  49.6. The winning-bag escort with the extensions (escw, b2w, b3w) passes.
- A (bankfin) costs Prism its Focus hoard. From r76 on, nearly every bag fails the finish test (an unseen enemy's
  credible tiles are near). Even limited to bags of 200+ it costs 3.7 points.
- At the real budget a quarter of map pairs change even for route, which fires only against a winning channel.
  That is fuel divergence, so route's 49.1 is checked at 10M below.

**Full runs** (20,480 games on 538000-538039 at the real budget; 128 ladder maps both sides against
astraeus-now-1106, where oc-retest-clean itself reads 56.2%; the 10-seed suite at 10M and at 2x fuel, the latter
200k a turn and 400k the first):

| variant | real 20,480 | ladder 256 | 10M 5,120 | 2x 5,120 | OOF real CAND / REF |
|---|---|---|---|---|---|
| b1 | 50.1 (49.4-50.8) | 55.5 | 50.1 | 50.0 | 153,862 / 152,209 |
| finish | 50.0 (49.3-50.7) | 56.6 | 50.0 | 50.0 (identical games) | 152,783 / 152,583 |
| funnel | 49.8 (49.1-50.5) | 53.1 | 49.1 | 48.8 | 160,012 / 153,499 |
| lockwar | 49.6 (48.9-50.3) | 55.9 | 49.2 | 49.5 | 158,372 / 154,324 |
| interrupt | 49.9 (49.3-50.6) | 53.9 | 50.1 (screen) | 50.1 | 158,116 / 154,451 |
| bankfin3 | 50.0 (49.3-50.7) | 57.4 | | 50.1 | 153,319 / 153,326 |
| b3w | 50.3 (49.6-50.9) | 53.1 | | 50.3 | 156,280 / 153,199 |
| escw | 49.9 (49.2-50.5) | 54.3 | | 49.5 | 169,153 / 155,089 |
| combo1 (lockwar, funnel, finish, b1) | 49.1 (48.4-49.8) | 54.3 | | 48.7 | 164,925 / 152,054 |
| combo3 (interrupt, lockwar, finish, bankfin3) | 49.7 (49.0-50.3) | 51.2 | | 49.8 | 163,140 / 155,034 |

None is significant locally (the bar for the live gate). The 10M and 2x columns say the same: these are level in
logic, not hurt by fuel.

### Self-play forensics

`fixm/sp.py` over 800 games of the b1 full run (b1 rarely fires: self-play):
- **Big channels fail at home too:** 1,260 tribute starts of 500+ gems, 11.9% finished (518 cancelled by the
  tributer, 336 stunned, 206 locked); 200-499: 53% finished.
- **Prism's hoard** lost 123k gems in bags over 800 games (154 a game; no other body above 25). Its deaths spread over
  bag sizes (100-299: 41k, 300-599: 37k, 600+: 19k), so there is no narrow cut. A (banking it) costs the Focus.
- **Winning channels:** of 784 games won by a tribute, in 148 a losing lock carrier came within 6 of the altar during
  the channel and in 1 within 2. 86 of these were 20+ turn channels.

Those 86 games re-run (debug traces, `SEEWIN` lines: a body that sees a winning enemy channel) with our bot in the
loser's seat: knobs off 1 win, `ender_route` 10, `deny_gems` + `site_guard` 21, all three (interrupt) 23,
interrupt + `ender_leave` 22. In them:
- lock carriers do walk in (`E`) and lock. Each lock cancels the channel; the carrier dies on the spot (60 rounds of
  `-`), the enemy breaks the lock and restarts, and the next carrier repeats it until none is left;
- without the route reorder, a ranged carrier closes 8 → 3 tiles in 11 rounds, attacking as it goes.
- `ender_leave` (a body with no hard stop and no kill in 3 hits leaves the channel alone) changes nothing there.

**Why interrupt is level anyway** (2x fuel, where a debug build replays the release game): interrupt changed 223 of
2,560 map pairs, 115 won both and 108 lost both. Re-running 40 of each with traces, the first decision that differs
was a DENY in 27 of the 40 lost seats and 23 of the 40 won ones. The DENYs look alike (median 330-340 gems, 22-29
rounds left, 4 steps). In self-play, stopping a non-winning channel is a coin flip: it delays their gems and costs
our body's time or life. The race-priced deny (`race_deny_gain`, below) is the attempt to tell them apart.

### Race-gated variants and the 2x screens

The race-gated versions of (A), #1 and (C) are built in addition to the plain ones (`FIXM_RACE`, model/race.{h,cc}
from `variants/oc-race`). The knobs are in params.h:
- `race_bank_k`: Prism stops waiting for Focus once `race::current().danger(k)` holds.
- `race_deny_gain`: an enemy channel is denied when `if_enemy_cancelled` flips the projected winner to us, or moves
  their win that many rounds later.
- `race_escort_k`: the escort holds for a non-Prism bag of 100+ while the race margin is within ±k.

With the knobs off and without `FIXM_RACE`, the bench is still identical at 100M (16/16 default, 52/52 wide; re-run
after `ender_leave` and the race code). These are 2x-fuel screens against oc-retest-clean on 538000-538009 with
`--no-test-draft`:
- The first eight ran under the no-harm SPRT (48.5 vs 50.5), so their "H1" means no harm, not a gain.
- esc3 and b2w ran under the gain SPRT (50 vs 52).

| variant | knobs | 2x win % (games) | 95% CI | SPRT |
|---|---|---|---|---|
| race0 | race model compiled in, all off | 50.0 (2,011) | 47.8-52.2 | no-harm H1 |
| rbank | race_bank_k 100 | 50.0 (2,097) | 47.9-52.2 | no-harm H1 |
| rdeny | ender_route, race_deny_gain 50 | 49.7 (2,101) | 47.6-51.9 | no-harm H1 |
| resc | site_guard, escort_multi, race_escort_k 150 | 50.0 (2,003) | 47.8-52.2 | no-harm H1 |
| rsite | ender_route, site_guard | 49.9 (2,026) | 47.7-52.0 | no-harm H1 |
| rall | rdeny + rbank + resc | 49.8 (2,914) | 48.0-51.6 | no-harm H1 |
| deny | ender_route, deny_gems 100 | 50.0 (2,026) | 47.8-52.2 | no-harm H1 |
| site | site_guard | 50.0 (2,060) | 47.8-52.2 | no-harm H1 |
| esc3 | site_guard, escort_bag 500 (not Prism's), multi | 49.9 (2,113) | 47.8-52.0 | gain H0 |
| b2w | site_guard, cover_n 2 | 49.9 (2,148) | 47.8-52.0 | gain H0 |

The race gates neither help nor hurt. Pricing the deny by the race does not separate the good DENYs from the bad
ones in self-play, any more than the gem threshold did.

## Conclusion (round 1; round 2 below found one)

- No macro variant is significant locally, plain or race-gated, at the real budget or at 2x. None goes to the live
  gate.
- The no-harm passes are frozen with READY: oc-fixm-b3w, b1, finish, bankfin3, interrupt, lockwar and combo3.
  The other variants were deleted; they are oc-fixm-dev with the knobs in the tables above. In order of the local
  evidence:
  - b3w is the only point above 50 on every column (50.3 real, 50.3 2x);
  - b1 and finish are flat everywhere (finish's 2x games are identical: it never fires there);
  - bankfin3 (finish_margin 5, finish_min 500) reads 57.4 on the ladder 256 against 56.2 for the base, which is
    within noise;
  - interrupt is the one that wins the scrim losses it was made for (03homonoliths-a) and 23 of 86 lost
    winning-channel games in self-play, against 1 for the base. It is level overall because its DENYs are a coin
    flip.
- Self-play is a poor judge here. The problem it fixes (an opponent that channels 1-2k gems unguarded) is rare
  between two oceans, and between them a cancelled channel just restarts.
- **What to strengthen next:**
  - a lock carrier that survives: it locks from the edge of the radius-2 ring away from the channeller's allies, or
    with an escort, and re-locks after a break;
  - a team rule that sends the next carrier as the lock breaks, not one at a time;
  - a gate on ladder-style opponents (a Fish-like puppet set), not on self-play.

## Round 2: Fish-like opponents and a stronger interrupt

### Paired against fixed opponents

CAND and oc-retest-clean each play a fixed opponent on the same maps and sides, at 2x fuel, with own drafts.
`fixm/pair.py` pairs them per game: net flips, and the paired difference with a 95% CI clustered by map. Map
classes come from `lock-tools/sites.mjs` (altar tiles within 3 merged):
- one-tile;
- one-site (2+ tiles);
- multi.

The base on 538000-538009 (5,120 games):

| opponent | base wins |
|---|---|
| bots/fish | 79.4% |
| bots/fish_farm | 87.1% |
| astraeus-now-1106 | 55.1% |
| proteus | 60.5% |

The round-1 finalists, paired against the base (points; 95% CI):

| variant | fish | fish_farm | astraeus | proteus / hoard |
|---|---|---|---|---|
| interrupt | +0.27 (-0.33, +0.88) | +0.57 (+0.01, +1.12) | -0.29 (-0.99, +0.41) | hoard -0.62 (-1.29, +0.04) |
| b3w | +0.37 (+0.04, +0.70) | +0.06 | +0.21 | hoard -0.12 |
| b1 | -0.08 | +0.16 | +0.06 | hoard +0.06 |
| finish | +0.02 | -0.02 | +0.02 | hoard +0.04 |
| bankfin3 | -0.18 | -0.21 (-0.40, -0.03) | | hoard -0.25 |

Held out (538010-538039, 15,360 games each) against bots/fish:
- b3w: +0.10 (-0.05, +0.26). The s10 reading shrank, as SPRT readings on a shared map order do.
- interrupt: +0.04 (-0.27, +0.35).

### Does bots/fish make long unguarded channels?

Rarely. `fixm/oppcen.py` over the base's 5,120 games against bots/fish:
- per game, the opponent starts 0.34 channels of 200-499 gems, 0.09 of 500-999 and 0.03 of 1,000+;
- 500+ channels finish 11.3% of the time, and 1,000+ channels never;
- 188 of our 1,055 losses end with a tribute of 200+ gems (158 of them 200-499); 72 of those channels were
  unguarded (no Fish ally within 3 of the altar at the start).

bots/fish is too weak to grow a big bag: its carriers die first, and its tributes are cancelled by our locks
and stuns. It also cancels its own channels when threatened, through ocean's `continue_tribute`, while live Fish
completes 3,180 of 3,490 (FISH_MODEL 8.3).

**`bots/variants/fixm-hoard`** is a Fish-like puppet that does make them. It is bots/fish plus:
- Prism drafted second on every map (Prism banks only a winning bag);
- channels that are never cancelled by choice.

Against the base, 600 games of `fixm-538h300`:
- per game, 0.21 channels of 500-999 and 0.06 of 1,000+, two to three times bots/fish's rate;
- 500-999 channels finish 15%, and 1,000+ channels 3%. The base already stops most of them: 85-97% are
  locked or stunned;
- 42 of 151 losses end with a 200+ tribute.

The headroom for any interrupt is a few points of the games against such an opponent, at most.

### Strengthening the interrupt

First, the knobs that change what the carrier does around its lock:
- **`lock_flee`**: after its lock, the carrier attacks no more and walks out of reach. It fired once in 86
  near-set games: the lock is placed at the end of the walk to the ring, so no walk is left.
- **`ender_leave_walk`**: `ender_futile` also covers a winning bag out of a channel, which the ender used to chase
  into its guards. It made no difference on the near set (22 of 86).
- **perma-lock holders**: `variants/oc-lock-dev`'s machinery, merged unchanged into oc-fixm-dev (perma_lock.cc,
  `params::plock`, knobs off), with gwin's hold gate (winbank), one timed holder and seek 6. Variants: i2g, and
  i2a with all hands. They read 22 and 25 of 86, and level at 2x (H0). Against the hoarder:
  - i2: -0.47;
  - i2g: -0.55;
  - i2a: -0.78 (-1.48, -0.08);
  - interrupt: -0.62.

Forensics on the near set: a carrier with a lock locked at once, cancelling a channel with 70 turns still to
run, and died the next turn. The enemy then broke the lock in a turn or two and restarted. Each lock cost them
only the turns the channel had run.

**`lock_wait` / `lock_stage`** (fight.cc `lock_plan`, `lock_plan_wait`, `lock_plan_turn`):
- A carrier holding a lock for a winning or denied channel waits lock_stage to lock_stage + 3 steps from the
  altar's lock tiles (plock's `lock_field`). It stands out of every visible enemy's reach, attack range + 3 if it
  can, else + 1.
- It walks in so as to lock `lock_wait` turns before our last turn before the channel lands. The enemy then
  loses the whole channel.
- The plan (altar and last round) is kept while the channeller is out of sight.

Waiting 4 tiles from the altar, the guards came out and killed the carrier in 181 of 348 plans (stage 5). At
stage 8, 99 of 298 died. Near set (real budget, so noisy):

| variant | near-set wins |
|---|---|
| base | 1 |
| interrupt | 23 |
| iw (stage 5) | 26 |
| iw3 | 28 |
| iw8 | 28 |
| iw12 | 29 |

At 2x fuel against oc-retest-clean, gain SPRT 50/52, each screen with its own `--sprt-seed`:

| variant | 2x reading | SPRT |
|---|---|---|
| iw | 50.6 | H0 |
| iw8 | 51.3 (3,158 games) | **H1** |
| iw12 | 50.7 | H0 |
| dw (deny + wait, no site guard) | 50.7 | H0 |
| iw2 (+ ender_leave) | 50.1 | H0 |

The earlier round's 2x and real-budget screens all shared seed 0 on 538s10, so their H1s are correlated.

**`variants/oc-fixm-iw8`** (ender_route, deny_gems 100, site_guard, lock_wait 1, lock_stage 8), held out on
538010-538039 at 2x fuel (15,360 games each):
- against oc-retest-clean: **51.0% (50.2-51.8)**. By class: one-tile 50.9, one-site 51.5, multi 51.0;
- against oc-fixm-interrupt: 50.7 (49.9-51.5), so lock_wait is most of it;
- paired against bots/fish: +0.20 (-0.14, +0.53);
- paired against fixm-hoard: **+0.44 (+0.04, +0.84)**, and multi +0.59 (+0.18, +1.01).
- The rest of 538000-538009 at 2x: 51.0 of 5,120. With the held-out runs, that makes 2x 51.0 over 20,480 games.
- **Real budget**, 538000-538039: **50.8% of 20,480 (50.1-51.5)**.
  - On the held-out 538010-538039 part: 51.3 of 15,360 (±0.8).
  - On 538000-538009: 49.1 of 5,120 (±1.4).
  - Out-of-fuel turns: 166k against 156k (+7%).
- 128 ladder maps against astraeus-now-1106: 54.3, against 56.2 for the base (±6).

The other lock_wait variants, paired at 2x on 538000-538009, are all positive and none is significant alone:

| variant | fish | hoard |
|---|---|---|
| iw3 | +0.45 | +0.25 |
| iw | +0.53 | +0.51 |
| iw12 | +0.37 | +0.04 |
| dw | +0.31 | +0.51 |
| iwg (+ gwin holder) | +0.47 | +0.66 |

### Round 2 result

**`variants/oc-fixm-iw8` is READY**: the first locally significant variant of this note. It passed the SPRT at 2x
with its own seed, and it holds out at 2x (51.0 of 15,360) and at the real budget (50.8 of 20,480; 51.3 on the
held-out part). Its gain comes from timing the lock, not from more locks: a lock costs the enemy the whole
channel. It is positive but small against bots/fish and the hoarding puppet.

Other READY variants:
- oc-fixm-b3w and the round-1 finalists stay READY as level, no-harm variants;
- b3w's s10 gain against bots/fish did not hold out.

Deleted:
- i2, i2f, i2w, i2g, i2a, g (flee, leave and holders);
- iw, iw0, iw2, iw3, iw12, iwg, dw.

Each is oc-fixm-dev with the knobs above (`fixm/mkvar.py`, which takes `plock.` keys too).
`bots/variants/fixm-hoard` is kept as the hoarding opponent.

### Merge checks (real budget, against oc-retest-clean)

- **Unused seeds**, `maps/suites/merged/ptw-c` (543080-543119): 50.5% (49.9-51.2) of 20,480. That is positive, not
  significant alone. Pooled with 538000-538039: 50.65% (50.2-51.1) of 40,960. Out-of-fuel turns 172k against 163k.
- **`--mix varied`**, `maps/suites/merged/fixm-varied-538060` (fresh-varied-538060..538069): 50.3% (48.9-51.6) of
  5,120.
- **The panel**, on panel-check-514510, 5,120 games each. Mean +0.72; no member is below its bound.

| member | iw8 | oc-retest-clean | bound |
|---|---|---|---|
| astraeus-now-1106 | 54.6 | 53.1 | |
| proteus | 64.4 | 63.3 | |
| demeter | 67.1 | 66.0 | |
| ocean-td | 81.7 | 82.1 | 80.6 |
| v67 | 77.5 | 77.2 | |

- **`bots/variants/oc-iw8-clean`** (READY) is oc-retest-clean plus iw8's behaviour as plain code: the timed lock
  with stage 8, the 100-gem deny, the route fix and the site guard. It has no knobs and no perma-lock or race
  code; `lock_field` is its own six lines.
  - Its bench replays at 100M are identical to oc-fixm-iw8's (16/16, 52/52), at 0.15% less fuel.
  - Drafted as CHANGES 429.

## Live gate (2026-11-06)

`variants/oc-fixm-iw8` was submitted as **v80** at 11:02 UTC (`cambc submit` of the directory itself: source tree
hash d9e9a8d061c4; a scratch copy built with `cambc build --release`). It was live and pinned from 11:11, and played
the core set against Fish and Mite pinned to refs r1 (160 games, 11:11-12:08). No v78 group was in flight across
the switch. v80 stays active.

`pair 78 80`, split by fix-lock.md's site definition (altar tiles within 3, at most 2 tiles; 17 of the 40 core maps
are one-site):

| opponent | v78 | v80 | flips for v80 / v78 | one-site (34 games) | multi-site (46) |
|---|---|---|---|---|---|
| Fish | 40 | 39 | 6 / 7 | 19 → 18 (2 / 3) | 21 → 21 (4 / 4) |
| Mite | 47 | 47 | 9 / 9 | 20 → 23 (5 / 2) | 27 → 24 (4 / 7) |
| total | 87 | 86 | 15 / 16 (net -1) | +2 | -3 |

**Level.** The net is -1, so the ext set was not run (the bar was net ≥ 0). The one-site +2 (Mite +3, Fish -1) comes
with a multi-site -3.

### Flip forensics

Tools: `gate-tools/` (`flipgames.py` extracts both versions' replays, `flipsum.py`, `aftercut.py`, `pairsplit.py`;
set `GATE_DIR` to a scratch directory holding `mapclass.json` and `lock-tools/sites.mjs maps/` output as
`ladder_sites.jsonl`). A "timed" lock is one of ours that cancels an enemy channel with at most 2 turns left.
Release builds print no debug lines, so the timed lock is inferred from the replay.

- **The timed lock fires live.**
  - On all 160 games, v80 made 53 such cuts of 50+ gem channels (13,655 gems), against v78's 6 incidental ones
    (538). v80's earlier cuts were 63 (20,383 gems), against v78's 54 (33,793).
  - It does not stop the enemy banking:
    - enemy tributes of 100+ that landed: 177 (31.4k gems) against 180 (33.0k);
    - our deaths 1,800 against 1,707, theirs 1,838 against 1,795.
- **The live opponents undo it.** After a timed cut:
  - our lock was broken within 10 rounds in 21 of 53 (median 13 rounds);
  - the enemy re-banked ≥ 80% of the bag within 60 rounds in 15 of 53;
  - the carrier died within 15 rounds in 14 of 53.
  - So against Fish and Mite the whole channel costs them about 15-20 rounds, not the bag. They break locks at
    once (LOSSES.md mode 5) and their guards kill the carrier.
- **Most flips are not the lock.** 24 of the 31 flips diverge before round 100, and 18 of them in rounds 1-7, long
  before any channel worth locking. iw8 also changes pathing.cc and capture.cc, and the fuel layout, so the turn-1
  play differs. The drafts are identical in all 160 games.
- **Flips with a timed cut:** 5 of the 15 v80 wins and 6 of the 16 v80 losses.

  Wins:
  - **02treasure_box-a (Fish).** Timed cuts of a 302-gem channel at r580 (Stellar) and r617 (Willow); both carriers
    died. v78 let 419 and 338 land and lost 404-1026; v80 won 1007-231. The lock decided it.
  - **02guardians-a (Mite).** Timed cuts at r1024 (Marcella, 316 gems) and twice of a 1,585-gem channel, at r1860
    and r1969 (Issac, who died after the second). v80 won 246-212 on the round-2000 tiebreak; v78 lost 22-1335.
    The lock decided it.
  - **04two_kingdoms-b (Mite):** three timed cuts (109, 66 and 109 gems), and every carrier lived.
  - **04spiral_moat-a and 04passageway-b (Mite):** small cuts (29 and 40 gems), not decisive.

  Losses:
  - **00collision-b (Mite).** It diverges only at r630.
    - At r731 Cassi locked on the last turn and cancelled a 222-gem channel with 1 turn left.
    - C&I died the next turn (23 gems fed), and Mite broke the lock at r736.
    - Mite re-channelled 245 gems, which landed at r753. v80 lost 582-1003, where v78 won 1007-970.
  - **02harvest-b (Mite).** Issac's timed cut at r822 (164 gems); the carrier lived. The same 164 landed at r840.
  - **02treasure_box-b (Mite).** Timed cuts at r481 (Stellar, 220 gems, who died) and r512 (Marcella, 232). Then
    278 landed at r586. Lost 136-1006 with 17 deaths.
  - **04terraces-a (Fish).** Vendetta's timed cut at r1379 (110 gems); 110 landed at r1395.
  - **00eight-b (Fish).** Two timed cuts of 104 gems, both carriers alive, but 25 deaths against 1: this one was
    lost in the fights.
  - **00ambush-b (Mite):** a 27-gem cut.
- **Flips without one.** 03homonoliths-a (Fish), LOSSES.md's 1,200-gem case, flips to a win, but not through the
  lock.
  - It diverges at r551 (our Vesper's recall), and our Prism's 600-gem channel lands at r655 before Fish's
    re-started 600 can.
  - In v78, Prism cancelled its own channel four times under pressure and died with the bag at r604.
  - 01boss_battle-b (Mite) flips from v78's Prism hoard loop (two lock cuts of 6,912 gems in all, 47 deaths) to a
    856-0 win with 12 deaths.

**Verdict:** level live, with no evidence of a gain. The timed lock works mechanically. But Fish and Mite break a
lock in about 13 rounds and re-bank, and the carrier often dies, so a cut buys tens of rounds, not the channel.
Its two clear wins (02treasure_box-a, 02guardians-a) are offset by re-banked or fought-out losses.

### Merged (2026-11-06)

- Live gate (v80): net -1 of 160 paired games (15/16 flips), level. The lock fires live (53 late cuts), but Fish
  and Mite break it in a median of 13 rounds and bank again.
- On the local evidence, `bots/ocean` is now `variants/oc-iw8-clean`, as CHANGES 429. The frozen base is
  `variants/oc-base5`; `variants/oc-retest-clean` is ocean before it.

### Ext set (v80, 12:12-14:17 UTC) and pooled

The ext set was run anyway, for data, after iw8 was merged on the local evidence. It was queued at the default ext
priority (30), which keeps the job's reserve. v78's ext set was already complete. There are 352 paired ext games:
fillers repeat core maps and are counted once.

| | ext: v78 / v80 wins | ext flips v80 / v78 | pooled 512: v78 / v80 wins | pooled flips v80 / v78 |
|---|---|---|---|---|
| Fish | 86 / 86 | 22 / 22 | 126 / 125 | 28 / 29 (-1) |
| Mite | 111 / 107 | 16 / 20 | 158 / 154 | 25 / 29 (-4) |
| one-site | 67 / 64 | 17 / 20 | 106 / 105 | 24 / 25 (-1; Fish -6, Mite +5) |
| multi-site | 130 / 129 | 21 / 22 | 178 / 174 | 29 / 33 (-4; Fish +5, Mite -9) |
| total | 197 / 193 | 38 / 42 (-4) | 284 / 279 | **53 / 58 (net -5, z -0.47)** |

Lock cuts and what follows (`aftercut.py`):

| timed cuts (≤ 2 turns left, 50+ gems) | core | ext | pooled |
|---|---|---|---|
| v80 cuts (gems) | 53 (13.7k) | 88 (16.1k) | 141 (29.8k) |
| v78 cuts (gems) | 6 (0.5k) | 13 (1.6k) | 19 (2.2k) |
| v80: lock broken within 10 rounds | 21 (median 13) | 38 (median 12) | 59 (42%) |
| v80: enemy re-banked ≥ 80% within 60 rounds | 15 (28%) | 40 (45%) | 55 (39%) |
| v80: carrier died within 15 rounds | 14 (26%) | 28 (32%) | 42 (30%) |

- Enemy tributes of 100+ that landed: ext 412 (68.8k gems) for v80 against 397 (65.6k) for v78. Pooled, 589
  against 577: the timed lock does not reduce what Fish and Mite bank.
- Our deaths: ext 3,474 against 3,154, and pooled 5,274 against 4,861 (+8%). Theirs: 4,899 against 4,805.
- 57 of the 80 ext flips diverge before round 100. Flips with a v80 timed cut: 12 won, 14 lost.
- The ext set strengthens the core reading. The re-bank rate after a timed cut rises from 28% to 45%, and the
  carrier dies a third of the time. A cut buys rounds, not gems, against these opponents.

**Pooled verdict:** level to slightly negative live (-5 of 512 paired, n.s.), with more of our deaths and no fewer
enemy gems banked.
