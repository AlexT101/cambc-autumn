# Contested altars in astraeus: evidence and plan (2026-11-05)

## Evidence

Data:
- **ladder**: the 1,030 post-patch ladder games (top-20 teams) in `replays/bush-ladder/analysis`, 48,697 tribute starts.
- **self**: astraeus vs ocean, 256 local games in `replays/invade-ladder/analysis-self`.

Scripts are in `tools/`: `altar_study.py ANA --out X.jsonl`, then `tab.py`, `tab2.py X.jsonl NAMES.json`, `alt_cf.py`,
`winready.py` and `presence1z.py`. Team names for the ladder set come from `matches.tsv`, joined by draft.

Definitions:
- Altars are linked into one **zone** when they are within Chebyshev 10 of each other.
- **margin** = enemy spawn walk − our spawn walk to the altar's tribute tiles.
- **contested**: margin < 5.
- **long**: a channel of at least 9 turns (90+ gems).

Findings:
1. **Short channels are not the problem.** Channels of 8 turns or fewer complete 95-98% everywhere. Completion falls to 81% for
   9-20 turns and 35% for 21+ turns. Astraeus chains only bags under 45 (`chain_bag_limit`), so its long channels are
   Prism's retained hoard, bags taken by kills, and winning bags.
2. **Enemies near the altar at the start decide most of it.** On the ladder, long channels with no enemy within 8 at
   the start completed 91.6%; with one or more, 50.9%.
3. **Geometry adds risk on top of that.** With no enemy within 8 at the start, long channels completed:
   - 87% on one-zone maps;
   - 93% at contested altars;
   - 97% at safe altars (margin ≥ 5).

   One-zone maps are the bad class (9-20 turns: 74% against 88-94% on maps with 2+ zones). Centrality matters
   through the margin, not by itself.
4. **Escorts beside the carrier do not protect it.** With no enemy near at the start, allies within 4 changed nothing:
   0, 1 and 2 allies read 89, 89 and 80% on one-zone maps. With enemies near there is a small gain (0-13 points,
   noisy). Tributes are cancelled by stuns and locks from range 2-4+, so a bodyguard on the carrier's tile is too late.
   An escort has to stop the enemy before it gets in range.
5. **Redirecting to a safer altar has a small ceiling.** On multi-zone maps, 255 of 1,290 long channels started with
   an enemy within 8:
   - 108 of them had an enemy-free altar in another zone within 15 extra steps (median +10);
   - only 26 of those 108 failed.

   That is the most a perfect redirect could save in 1,025 games. Ocean's A3 safe-altar redirect read level
   (EXPERIMENTS "Altar control"), and this is why.
6. **Our own bots hoard and then can't cash in.** In self-play, long channels on one-zone maps carry about 445 gems
   (ladder: about 200), and 21+-turn ones complete 23%.
   - Astraeus's Prism made 153 starts of 21+ turns, with a mean bag of 540; 27% completed.
   - From the first round a bag would win to the actual win: astraeus took a median 20 rounds on one-zone maps, with
     35% of cases over 30 rounds. Ocean took 27.5; ladder teams 10-13.
   - The sides still win 94-96% from there, so the cost is mostly rounds, which the mirror opponent may not punish.
   - Ocean's winning channels over 30 turns: 3,200 starts, 285 completed. Cancels: 1,171 manual (ours, as
     `tribute_safe` re-judges every turn), 848 stun, 662 lock. Each restart starts the full channel again.
   - A Prism retain cap lost (46.7%): the hoard is strength. What to fix is how it is cashed.
7. **Presence on one-zone maps goes with winning.** On the ladder, the side with more champion-rounds within 8 of
   the altar (rounds 30-600) won 60.0% of 487 one-zone games.
   - This is correlational: stronger sides push in.
   - The share of the map's camp gems within 10 of the altar varies widely (median 36%, p25 11%, p75 68%). Farming
     near it is cheap on some maps and costly on others.
   - Ocean's guard that held the altar all game lost badly (1 guard 44.0%, 2 guards 32.1%). Presence has to come
     from productive work (farming), not from idling at the altar.

## What astraeus does now (code)

- **Altar choice.** `bank_gems` (economy/bank.cc) walks `to_any_altar()`, the nearest altar. It picks a specific one
  only to skip enemy locks or an altar it gave up on (`memory.avoid_altar`).
- **Waiting.** `carry_bag` waits at a watched altar as many rounds as the walk to the next unlocked altar, then leaves.
  No zone, margin or enemy-arrival estimate enters the choice.
- **Channel safety.** `tribute_safe` is local: nothing kills us within `min(turns, tribute_window = 8)` turns,
  re-judged each turn.
  - `any_risk` takes winning channels of 8 turns or fewer at any risk.
  - A longer channel waits for a window. Once inside it, any threat that comes within the window cancels it.
- **Farm pricing.** The farm loop prices the trip to the nearest altar (`to_any_altar`, `centre_to_altar`) and treats
  the channel as certain once started.
- **Prism.** `retaining_gems` keeps Prism's bag until it wins or `closing`.
- **Not in astraeus.** Ocean's CHANGES 408 (`economy/altar_guard.cc`, one-altar maps only): the 3 strongest bodies
  hold stand tiles within 2 of the altar while the enemy is cooked-ahead or while we carry a winning bag. It read
  51.1% of 20,500 one-altar games (+0.25 overall).

## Design: contest the zone as a team, don't flee from it

Short channels stay as they are (finding 1). Everything below applies to a **long** channel: `tribute_turns(bag)`
above `tribute_window`. Most turns are therefore unchanged, which keeps fuel and the A/B noise low.

### 1. Static zones (once a game)

- **Zones**: altars linked when the walk between their tribute tiles is at most `zone_link` (knob, about 10). Store
  `StaticMap::zones`, each altar's zone, and `one_zone` (which generalizes ocean's `altars.size() == 1`).
- **Per zone**:
  - our walk: `from_ally_spawn` at the tribute tiles;
  - their walk: `enemy_spawn_steps` (the mirror field);
  - the margin between the two;
  - the enemy's approach: the tiles a few steps out from the zone, along the descent of their spawn field. These are
    the screen tiles of step 4.

This uses existing fields and costs nothing per turn.

### 2. Enemy arrival at a zone (per turn, only while a long bag is carried)

- **T_arrive(z)** = the earliest round any enemy can stun or lock a tribute tile of z. Its inputs:
  - **visible enemies**: `enemy_reach::distance` from their position, with stun or lock reach (`act_range`; a lock
    is placed within 2);
  - **unseen enemies**: the nearest tile of `possible` (`possible_box`);
  - **dead enemies**: their respawn round plus the spawn walk.
- **Prior for unseen enemies.** On a one-zone map an enemy with a bag must come to the zone. Ladder teams tribute at
  their spawn-nearest altar 76% of the time (ocean's altar.md). Weight the unseen set towards that, not uniformly.
- **Cost.** This is the bulk of the new per-turn work: a few host distance queries per zone, cached while beliefs are
  unchanged (`BagKey`-style, as `gems_short` does).

### 3. Choosing where to cash a long bag

- **Score each zone** by the expected rounds to bank the bag:
  `walk(z) + n + (1 − p(z)) · retry`, where:
  - `n` = `tribute_turns`;
  - `p(z)` = P(the channel ends before `T_arrive(z)`, or the team holds z; step 4);
  - `retry` = one more channel plus the wait.
- **Where it plugs in.** This replaces `bank_gems`' nearest-altar default and `carry_bag`'s "wait for the walk to the
  next altar" rule, but only for long bags. The farm loop's banking trip for a long bag then uses `to_altar(chosen)`.
- **The hold counts as safety.** Your point 1: if every carrier flees to the safe altar, nobody contests the central
  one. So a zone the team is holding scores as safe as a safe one (`p` from the hold, not from T_arrive alone). A
  contested zone with the team there beats a safe zone reached alone and late. This makes it a team decision, not a
  per-carrier escape.
- **Deterministic team choice.** Every body computes the same zone from shared inputs:
  - static geometry, scores and the posted bag (`comms::bag_of`), not each body's own sight;
  - ocean's `guarding()` agrees without messages the same way;
  - no new comms bits needed. If it must react to sightings, the zone index fits in the free bits on most layouts.

### 4. The team hold (generalizes CHANGES 408)

- **When**: a long bag is carried and its zone is chosen. This covers ocean's escort case (a winning bag) and Prism's
  release, on every map, not only one-altar ones.
- **Who**: up to `hold_bodies` bodies by ocean's `guard_power` ranking, keeping at least one farmer.
  - The rest farm, with the bag's zone as their bank target.
  - On one-zone maps, also ocean's cooked trigger (enemy ≥ 600 and ≥ 200 ahead), since kept e3 needed it.
- **Where**: screen tiles on the enemy's approach (step 1), bushes first and out of camp reach, about 4-7 steps from
  the carrier. Not on it (finding 4): a stunner must be met before it is in range. Chase anything that enters the
  leash, as `guard_turn` does.
- **The carrier waits until the hold is up**, then starts. The channel cannot act, and a start before the screen is
  set wastes it.
- **Later knob: keep the channel while the hold wins the fight.** This is `tribute_safe` judged against threats that
  pass the screen. It attacks the manual-cancel loop (1,171 of 3,200). Ocean's `escort_keep` (e5/e6) read level or
  worse, so it comes last and is measured separately.

### 5. Presence on one-zone maps (your point 2)

- Ocean's permanent guard shows that standing still loses. So add presence as value inside the farm loop instead: on
  `one_zone` maps, groups whose centre is within R of the zone get extra value.
- That value scales with the contest's stakes, rising as either side's tributed score or carried bag nears the win.
  It is worth most when the enemy must come in to bank and we are already there.
- On maps where little value sits near the altar (p25 = 11% of gems), the weight should seldom change a pick. Start
  with a weight knob and a stakes curve, and sweep both.
- Idle turns (waiting on respawns) wait at the zone's screen tiles rather than wherever the bot is.

## Order of work and testing

Each step is an A/B against a frozen copy of the previous one:
- own drafts (`--no-test-draft`), the fast runner, real fuel;
- fresh ladder-mix suites; 20k games to ship;
- development on one-zone and multi-zone subsets filtered by `index.json` (ocean's `maps/suites/merged/altar-one-dev`
  and `altar-multi-dev` exist);
- every row recorded in EXPERIMENTS.

Steps:
0. **Port 408 into astraeus as is.** This is a known +0.25, and it gives the hold code a home.
1. **Zones.** Swap 408's `altars.size() == 1` for `one_zone`. Swap its stand tiles within 2 of the altar for screen
   tiles on the approach. Extend the escort trigger from a winning bag to any long bag.
2. **Zone choice for long bags** (steps 2-3), with the hold counting as safety. Expect most of any gain on maps with
   2+ zones from coordination, not redirection (finding 5's ceiling).
3. **One-zone presence weight** (step 5).
4. **Channel keep under the hold** (step 4's last knob).

Metrics per step, from `tools/`:
- long-channel completion by class;
- manual, stun and lock cancels;
- rounds from a winning bag to the win;
- bags lost to champion kills by distance from the altar;
- presence within 8.

They show whether a level win rate hides a real mechanism change. Self-play flatters exploits: confirm on the ocean
panel (`research/ideas-2026-11-05/PANEL.md`).

**Fuel.** Zones and screens are computed once. The arrival estimate runs only while a long bag is carried, a few
percent of turns. It adds no fuel gate: work is bounded by the zone count.
