# A ward plan in the draft (DRAFT-COMPUTE #4)

2026-10-26, branch `worktree-agent-a74cc070daf7ee73f`, on 80db5f72 (CHANGES 157); merged as CHANGES 159. Plan v5:
v4's header with `distances_at` repurposed as `wards_at`, and a ward section. Champions place the draft's ward tile for
their work, else fall back to the greedy bush ward.

## What wards do today

`ward_bushes` (bot.cpp) is the only placement rule. Once the cooldown is ready, at the turn start, before a tribute
and at the turn end, a champion with a bush within 2 picks the bush cluster with the most tiles within ability range
(4) of here plus of its work tile (claimed group or waited-at altar). It moves its ward only for strictly more. Off
bushes it never wards, so on bushless maps (00expanse, the gen chambers, labyrinth, classic, long-thin, open-field
and 01boss-battle on the bench) our champions place no ward all game.

Measured from replays (scripts in the session scratchpad: per-ward events, `sees` per champion and round, map bush
clusters). Proxy for ward-only sight: the enemy is beyond Chebyshev 8 of the viewer, or on a bush outside the viewer's
own cluster.

| Team (games) | Wards a champion a game | On bushes | Own half | Within 4 of a camp | First ward (median round) | Sightings ward-only |
|---|---|---|---|---|---|---|
| astraeus vs astraeus (140, `walk-final` ladder batch) | 18.5 | 100% | 75% | 65% | 22 | 22% |
| Intercontinental Fish (ladder, last 700) | 29.4 | 76% | 62% | 66% | 21 | 29% |
| procless | 23.4 | 100% | 75% | 65% | 32 | 28% |
| Trzy Kwaterki | 33.5 | 100% | 72% | 61% | 65 | 36% |
| NEETCoders | 24.6 | 30% | 58% | 77% | 66 | 34% |
| hello | 36.7 | 67% | 71% | 78% | 11 | 26% |
| Pantheon | 70.3 | 50% | 77% | 70% | 20 | 17% |

- Top teams ward more often but in the same places: mostly bushes, ~70% on their own half, ~65% near a camp.
- Hits on enemies seen only through a ward: ~5% of our hits (1128-1324 of 24-25k), 4-7% for the top teams.
- **Surprise deaths** (killer not in the victim's sight at any turn start of the 3 rounds before): 10-12% of our
  deaths, ~0.13 a champion a game. Top teams: 4% (procless) to 21% (Intercontinental Fish). Of our 161: half had the
  killer in a bush the round before. In 34 of those 80 a teammate's ward already watched that cluster, and only 17 were
  the victim's own: ward sight is personal (`vision.personal`).

So the ceiling is small. Wards change a few percent of decisions, and the deaths a ward could have warned of are about
one champion in eight games. The personal-vision point settles the model. A team-wide coverage plan adds nothing,
because a teammate's ward lends no sight. The useful plan is one ward tile per place a champion works, for that
champion's own ward. The greedy rule already wards near the work, so a plan can beat it only by choosing better tiles:
off bushes as well as on, scored by the whole neighbourhood rather than cluster size.

## The coverage model (draft side)

Sites: every camp group, then every altar. Stand tiles: a group's camp tiles (where it captures), an altar's tribute
tiles. For each site:

- `own`: what a champion at the site's centre (group centre, altar) sees, a radius-8 shadow cast under
  `vision.occlusion` (from a bush, its own cluster too).
- `near` = enemy-standable tiles (`open_for_them`) within 4 of the stand tiles, minus `own`; `far` the same within 8.
- Candidates: tiles within ward placement range (2) of a stand tile, minus walls, holes, altars and their spawn
  (`open_for_us`, the `wards.placement` errors). So a champion on a camp or tribute tile can always place it.
- Each candidate: one radius-6 shadow cast (`walls_and_bushes`, or with its own cluster removed when on a bush:
  `wards.vision`). Score = 2·|sight ∩ near| + |sight ∩ far|, popcounts over the chunks of its 13x13 window.
  Best score wins; ties go to the tile nearest the centre. Score 0 is no ward.
- Resumable per site, priced at 5000 + 2000 per box tile before each; it runs after the attack tiles, and
  `draft_reserve` and the write-before-pick order are unchanged.

## Encoding (plan v5)

Header: v4's 76 bits, with `distances_at` (always 0 since CHANGES 157) renamed `wards_at` (13): the section's first
bit, 0 absent. The branch added `wards_at` as a 14th field (89 bits); the merge reused `distances_at` instead, with
bench replays byte-identical. Version 5 so the check rejects v4 plans.

Section, read lazily on the first ward decision:

| Field | Bits |
|---|---|
| w, the code width | 4 (`ward_width_bits`) |
| per site (groups by index, then altars) | w: 0 none, else 1 + the tile's row-major index in the site's `ward_box` |

- `ward_box`: the members' bounding box (or the altar's 3x3) widened by 2, clipped to the map. Champions compute it
  from the members they already have, so a lookup is one fixed-width read at `wards_at + 4 + w·site`. No table.
- w is the bit width of the largest box: 6 on most maps, 7 with a Monolith or a big shared group.
- The section takes whatever is left after the attack tiles. Entries that do not fit are cut, and a site past the end
  of the stream reads 0 (none). If w does not fit, or the writer's round-trip check fails, there is no section.
- The writer checks that every site decodes back to the tile it searched (or none if cut), as the steps and attack
  tile writers do.
- I tried and rejected a variable-width code per site (box-sized, ~5 bits for single camps) or Rice-coded candidate
  ranks. They save ~20-30% of a small section, but a lookup would need a prefix sum or a decode pass over all sites.

Bits on the 26 wide-set maps (section only): min 52, median 157, max 418 (7 / 20 / 53 bytes). Sites: 8 / 25.5 / 69.
A planned tile exists for 22-100% of sites (median 92%); 105 of 616 planned tiles are bushes.

## Play side

`place_ward` first asks `ward_planned`. Our work site is the claimed group, else the waited-at altar. If its planned
tile is already our ward, the ward is kept and the greedy rule is skipped. Otherwise we place it on the planned tile
once we are within ward placement range (2), skipping a tile with a visible allied ward (an error under
`wards.placement`). The 10-round cooldown is already checked by `place_ward`. In every other case, including no plan,
no work, out of reach or an unseen ally's ward blocking the tile, the greedy rule runs as before. No new fuel gate.

## Fuel

`tools/fuel/bench.py --set wide` (52 games, release, 100M budget) against astraeus-80db5f7:

| | min | median | max |
|---|---|---|---|
| Draft round 0, before | 140k | 0.56M | 1.07M |
| Draft round 0, after (final build, code check) | 375k | 1.38M | 2.97M |
| The ward search alone | 238k | 0.85M | 2.24M (00lanes, 60 sites) |

- About 30-40k a site: ~25-40 candidates at ~1k each (cast, cluster opaque on bushes, window popcounts).
- Later draft turns are unchanged (max 42.7k).
- At the real budget on the many-group generated maps (gen-tiny-groups, gen-dense-camps), round 0 peaks at 5.0M of its
  10M. Later turns stay at 13-35k, and no A/B game drafted at random.
- A map whose search outruns round 0 (~250 groups) carries on in the 100k turns, a few sites a turn under the per-site
  estimate (5000 + 2000 a box tile) and `draft_reserve`. The round-trip check compares codes with one sequential reader
  (~20 fuel a site), not tiles (~300 a site, which would eat the reserve). That change left the bench byte-identical
  (52/52).
- Merged (b268494f): each site's bush clusters are grown under the draft's floor before its search (`bush_cluster()`
  grows with no limit, and the attack tiles found only clusters near the groups they reached); only the sites whose
  codes fit after the attack tiles are searched; the section is rewritten only when more sites are done. Wide bench
  replays byte-identical. With the whole search forced into the 100k turns (a debug variant on gen-dense-camps,
  gen-tiny-groups, 00lanes, 00monolith), every draft turn picked with at least 35k left. Such turns get through 0-1
  sites: the per-site estimate plus `draft_reserve` exceeds a 100k turn for any box over ~27 tiles, so the search
  stalls there, safely.
- Champions: round 1 +0.5k on average (-0.2k to +0.7k), almost all of it the first lookup (~250-350 fuel, ~780 at
  w = 7). Later lookups of the same site ~7 (cached). Play turns: the bench's `all` mean 47.9k.
- Out-of-fuel turns at the real budget: main A/B 4658 vs 4637 (+0.5%); fresh suite 2090 vs 1952 (+7%). Probably more
  wards placed at the turn start, each followed by `see_again`, and more enemies in sight for the fight code. Not
  traced.

## A/B

`py tools/ab.py variants/astraeus-wardplan1 variants/astraeus-80db5f7 --no-test-draft --threads 7` (both on their own
drafts, `test_draft` off in both):

| Suite | Games | Win % | 95% CI |
|---|---|---|---|
| ladder | 140 | 50.7 | 42.5-58.9 |
| gen | 512 | 53.7 | 49.4-58.0 |
| fresh/gen-s1 | 512 | 50.8 | 46.5-55.1 |
| **all** | **1164** | **52.1** | 49.2-54.9 |
| unused suite (`mapgen suite --seed 61026`) | 512 | 52.5 | 48.2-56.8 |

The A/B ran `wardplan1`. The committed code differs only in the fuel-only round-trip check and the per-site estimate,
and its bench replays are byte-identical (52/52).

By map type (main A/B): bushes on ≥3% of tiles 52.8% (648), under 3% 50.3% (356), no bushes 53.1% (160).

In those games (1164, both sides; the same metrics as the analysis above):

| | ward plan | base |
|---|---|---|
| Wards a champion a game | 28.2 | 18.0 |
| On bushes | 73% | 100% |
| Champions with no ward all game | 2% | 18% |
| First ward, median round | 15 | 19 |
| Sightings ward-only | 21% | 18% |
| Deaths a champion a game | 0.91 | 0.99 |
| Surprise deaths (share; a champion a game) | 9%; 0.082 | 11%; 0.109 |
| Hits on enemies seen only through a ward | 4805 | 5025 |

The plan is used as meant, and it moves the team towards the top teams' warding: more wards, a quarter off bushes,
wards on bushless maps. A quarter fewer surprise deaths is the plausible mechanism. Slightly fewer hits on ward-only
targets fits fewer bush wards, which are what reveal enemies standing in range.

## What didn't work, and what to try next

- No A/B lost, so nothing was ablated. Rejected before building:
  - a team-wide coverage plan (an ordered list of ward tiles for the team): sight is personal, so a teammate's ward
    does not cover me (34 of our 80 bush-ambush deaths happened under a teammate's ward);
  - variable-width or Rice-coded entries: see Encoding;
  - the tile-by-tile round-trip check: see Fuel.
- The old off-bush experiments (a periodic off-bush ward, 48.7%, deleted in CHANGES 33) put wards on a timer, not on
  tiles chosen for a work site. This plan's off-bush wards sit where the site's own sight is blocked.
- Known limits:
  - One tile per site: a second champion on the same group finds a visible allied ward there and falls back to the
    greedy rule. A second-best tile per site would cost w bits more a site.
  - The ward is kept while the claim lasts, even if the champion strays from the group.
  - No approach weighting: tiles towards the enemy spawn count the same as the rest. A capped field per site from the
    enemy side would add ~5-25k a site.
- Play side, likely the cheaper next gain: what champions do with ward sight. A ward that sees an enemy approach is
  read only by the ordinary threat and fight code. Two ideas:
  - leave a camp early when the ward shows an enemy closing;
  - delay a tribute while the altar ward shows an enemy within reach.
- Out-of-fuel turns +7% on the fresh suite (above): worth a trace before a bigger ward change.
