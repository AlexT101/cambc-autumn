# koi log, attempt 2

Attempt 2 (2026-10-20, from 00:05 EDT) restarted koi from hecate at 110e338 (`bots/baselines/hecate-v1`) to rebuild
its subsystems around Fish's play. Attempt 1 is in [LOG-attempt1.md](LOG-attempt1.md). Variants are snapshots in
`bots/variants/koi2-<label>/` (gitignored), played against `baselines/hecate-v1` from both sides; results in
`replays/koi2-ab/<label>-vs-<opponent>-<suite>/`. Suites: ladder (34 games), gen (264), central (92), and the fresh
seeds x1 = `replays/koi-maps/gen-7101` (264), x2 = `central-7102` (92), x3 = `gen-7103` (264). Win rates are koi's.
Noise: about ±2.5 points on 390 games and ±1.6 on 1010 (one SD; maps come in side pairs, so a bit more).

Tools: `tools/koi/scorecard.py` (Fish-likeness scorecard, see [README.md](README.md)); scratch scripts used for the
analysis below (`totals.py`, `tl.py`, `dec.py`, `deaths.py`, `bagloss*.py`, `pair.py`) are in the session scratchpad
and not kept.

## Milestone 1: the Fish system on hecate (390 games each)

| label | what | ladder | gen | central | all |
|---|---|---|---|---|---|
| m1 | Fish builds, 150-gold shopping recall bag and all, lazy banking (5 gems a step), the fitted engage rule replacing want_home/step_guard/prey, lowest-hp camp first, 30% recall | 12/34 | 82/264 | 37/92 | 33.6 |
| m1fight | hecate + the engage rule only | 10/34 | 96/264 | 31/92 | 35.1 |
| m1econ | m1 without the engage rule | 24/34 | 122/264 | 41/92 | 47.9 |
| e-nobuild | m1econ with hecate's builds | 21/34 | 140/264 | 45/92 | 52.8 |
| e-noshop | ... and hecate's shopping | 24/34 | 137/264 | 46/92 | 53.1 |
| e-nolazy | m1econ with hecate's chaining | 23/34 | 124/264 | 44/92 | 49.0 |
| e-nocamp | m1econ with hecate's camp order | 24/34 | 120/264 | 43/92 | 47.9 |

- The engage rule (stay while hp after the visible burst is at least 300 and the local ratio is at least 1.5 or a hit
  is ready, else walk away) is a 71% fit to Fish's choices but loses as a decision rule: deaths 3.0 vs 2.4 a game and
  12% fewer gems (gen). It retreats from fights hecate's simulation would win and stays in ones it would leave.
- Fish's builds cost about 5 points everywhere. Mechanism: no Jungle, so 20-50% more camp damage taken (small-brawl:
  7.5k vs 5.3k a game), more heal trips, slower farming. Fish's builds pay for themselves in fights, and fights are
  rare in koi-vs-hecate games (about 2 kills a game against 7 for Fish on the ladder).

## Milestones 2-14 on hecate builds (390 games each)

Each adds to the previous one unless noted (`hb`: hecate's upkeep builds).

| label | adds | all |
|---|---|---|
| m2hb | carriers take the 150-gold shopping recall too; a bag that rode it home goes to an altar; range openers (spell from 4-5 before walking in); Cassi and other damage-free stuns on any monster hitting an ally | 51.8 |
| m3hb | Fish commit (no retreat while hp after burst is 300+ and ratio 1.5+), hurt line 30%, chase carriers of 40+ on their ground | 51.3 (1010: 50.0) |
| m4hb | crew share of a monster group counted twice | 46.7 |
| m5hb | m3hb + enemy race: bank straight in when the enemy could win within the trip + 40, no shopping when it could win within 100 | 48.7 |
| m6hb | the second of each pick pair joins its partner's monster group (crews) | 44.9 |
| m7hb | m5hb + late race: from 700 gems (either side, ours with posted bags) bank at once | 48.2 |
| m8hb | carriers bank before a shopping recall when home is 5+ steps farther from an altar | 48.2 |
| m8hbc | m8hb with hecate's camp order | 47.7 |
| m9hb | chaining needs no threat, 60% hp, bag under 120; heal bonus back; recall 35%; heal trips without gold | 40.3 |
| m10hb | m9hb without the gold-free heal trips | 46.7 |
| m11hb | casters chip Monoliths from range 4 on mixed maps | 43.6 (mixed-Monolith maps 33/78 -> 21/78: never finished in time) |
| m12hb | m10hb + a wide search when live camps block the static way (a body sat 90 rounds in a dead-end pocket on gen-classic-640102605) | 47.4 |
| m13hb | peel: a stun on an enemy that threatens a hurt ally is worth that ally's life | 47.2 (vs nemesis 56.7, hecate-v1 61.5) |
| m14hb | a chased body falls back on a healthy ally instead of home | 44.6 |

- Per-map effects are large and consistent across variants (gen-classic-640102605, gen-fortress-640202800 and
  gen-classic-640105320 lost both sides in every variant; gen-vaults, gen-maze, gen-huge, lanes won), but each
  change is level overall.
- Analysis of m2hb's losses (subagent): koi's chained bags die more (63 chain deaths vs 22), bodies farm hurt after the
  heal bonus was dropped, and it enters fights lower (0.763 vs 0.783 hp). Restoring hecate's safety (m9hb/m10hb) did
  not win the points back.
- End race: in 45 of m3hb's 189 losses koi had the win in hand (score + carried) when the enemy won, but hecate did
  too in 54 of its losses: both teams hold big bags when the race closes. The race rules did not change the count.

## Restart from attempt 1's latsize (1010 games each)

`latsize` (hecate + farm value worth / (cycle (1 + cycle / H)), H = 100 x max(1, side / 50)) scored 54.2% on the same
1010 games in attempt 1. Fish's pieces layered on it:

| label | adds to latsize | ladder | gen | central | x1 | x2 | x3 | all |
|---|---|---|---|---|---|---|---|---|
| p3 | camp stuns + openers + peel | 15/34 | 124/264 | 51/92 | 127/264 | 45/92 | 136/264 | 49.3 |
| p3a | camp stuns | 17/34 | 143/264 | 54/92 | 130/264 | 46/92 | 143/264 | 52.8 |
| p3b | range openers | 13/34 | 128/264 | 46/92 | 134/264 | 46/92 | 134/264 | 49.6 |
| p3c | peel | 20/34 | 152/264 | 45/92 | 133/264 | 48/92 | 150/264 | 54.3 |
| q0 | camp stuns + peel | 16/34 | 140/264 | 55/92 | 130/264 | 45/92 | 147/264 | 52.8 |
| q1 | q0 + openers only while an ally tanks the group | 18/34 | 147/264 | 47/92 | 129/264 | 41/92 | 139/264 | 51.6 |
| q2 | q0 + Fish's 150-gold shopping recall, bag and all (bank first within 5 steps or when home is farther from an altar), no gain pricing | 18/34 | 147/264 | 46/92 | 135/264 | 39/92 | 140/264 | 52.0 |
| q3 | q0 + enemy race and late race banking | 17/34 | 139/264 | 48/92 | 136/264 | 51/92 | 152/264 | 53.8 |
| r0 | q3 + q2 | 17/34 | 152/264 | 45/92 | 131/264 | 39/92 | 131/264 | 51.0 |
| s1 | r0 + Fish's turn priority (engaged band ordered by the share of the weakest nearby enemy our next turn takes) | 20/34 | 146/264 | 35/92 | 137/264 | 39/92 | 128/264 | 50.0 |
| t1 | r0 + basic attacks on the lowest-hp camp (clusters first) | 17/34 | 138/264 | 43/92 | 155/264 | 36/92 | 118/264 | 50.2 |
| t4 | r0 + max_wait 10 (respawn timing) | 19/34 | 138/264 | 41/92 | 138/264 | 42/92 | 134/264 | 50.7 |
| sq | r0 + pick-pair crews + no chase leash | 11/34 | 113/264 | 45/92 | 119/264 | 34/92 | 110/264 | 42.8 |
| fb | r0 + Fish's build table | 17/34 | 120/264 | 43/92 | 117/264 | 40/92 | 122/264 | 45.4 |
| fbc | r0 + Fish's builds for the ranged champions only | 19/34 | 130/264 | 44/92 | 121/264 | 41/92 | 137/264 | 48.7 |
| v1 | q3 + respawning groups worth 1.3x (Fish's logit) | 15/34 | 118/264 | 45/92 | 132/264 | 42/92 | 124/264 | 47.1 |
| v2 | v1 + damaged groups 1.15x | 17/34 | 127/264 | 44/92 | 127/264 | 47/92 | 113/264 | 47.0 |
| v3 / v4 | q3 with cycle horizon 70 / 140 | 20/34, 14/34 | 139, 137 | 52, 50 | 146, 145 | 51, 47 | 140, 148 | 54.3 / 53.6 |
| d1-d4 | r0 with Willow / Prism / Vesper / Tavi instead of Varg (390 games) | | | | | | | 51.3 / 49.5 / 46.9 / 53.3 |
| f1 | q3 + clusters first | 13/34 | 148/264 | 43/92 | 150/264 | 49/92 | 128/264 | 52.6 |
| f2 | f1 + openers while an ally tanks + horizon 140 | 17/34 | 138/264 | 49/92 | 142/264 | 44/92 | 146/264 | 53.1 |
| f4 | f2 + wide search round live camps (bug fix) | 16/34 | 134/264 | 48/92 | 141/264 | 46/92 | 142/264 | 52.2 |
| f5 | f4 + Fish commit + chase any carrier | 21/34 | 134/264 | 50/92 | 145/264 | 44/92 | 135/264 | 52.4 |
| f6 | f4 + wait for a returning group from a bush in reach (rarely triggers) | 18/34 | 134/264 | 48/92 | 141/264 | 46/92 | 142/264 | 52.4 |
| f7 | f5 + f6 + Fish's turn priority | 20/34 | 141/264 | 49/92 | 143/264 | 45/92 | 128/264 | 52.1 |
| f8 | f7 + Fish's 150-gold shopping recall, bag and all (bank first only within 5 steps) + lazy chaining up to 5 gems a step (cap 150, hecate's threat and 60% hp checks) | 21/34 | 140/264 | 45/92 | 136/264 | 43/92 | 143/264 | 52.3 |

| f9 | f8 + the shopping walk home ignores threats until the recall (then keeps it only when safe) | 19/34 | 147/264 | 40/92 | 128/264 | 44/92 | 133/264 | 51.1 |
| final | f8 with dead code removed | 19/34 | 141/264 | 46/92 | 134/264 | 43/92 | 142/264 | 52.0 |
| fp | final + Fish's camp-aggro priority out of fights (healthy empty-handed bodies act first: -1 - floor(10 x hurt), carriers -6 - floor(5 x hurt)) | 19/34 | 130/264 | 52/92 | 132/264 | 38/92 | 138/264 | 50.4 |
| fbp | fp + Fish's build table | 16/34 | 122/264 | 52/92 | 132/264 | 44/92 | 125/264 | 48.6 |
| final30 | final with the low-health line at 30% (Fish's cliff) | 20/34 | 135/264 | 47/92 | 130/264 | 45/92 | 132/264 | 50.4 |
| fbp30 | fbp with the 30% line | 17/34 | 120/264 | 56/92 | 125/264 | 52/92 | 130/264 | 49.5 |
| fb30 | fbp30 without the camp-aggro priority | 20/34 | 118/264 | 50/92 | 127/264 | 43/92 | 122/264 | 47.5 |
| fbr | fbp30 with healthy Ren first (tank) | 21/34 | 127/264 | 50/92 | 119/264 | 44/92 | 135/264 | 49.1 |
| kd | fbp30 + Fish's caster draft (Stellar, Tavi, Prism, Cassi & Issac, Ren) on Monolith-only and shared-gem maps | 18/34 | 122/264 | 51/92 | 125/264 | 52/92 | 127/264 | 49.0 |

- The landscape is flat: every variant that does not cost farming lands at 52-54% over 1010 games, the same as
  attempt 1's latsize. Fish's behaviours that cost farming lose 4-11 points: builds, crews, solo range openers,
  preferring respawning groups, the fitted engage rule.
- Who wins (r0, 390): the first champion death decides most games (koi dies first 133 times and wins 41%, hecate
  first 132 and koi wins 67%, no death 125 and koi wins 58%). Steals are small both ways (about 28 gems a game each).
- "Aimless" recalls (scorecard: no gems, under 120 gold, at least 30% hp) are almost all hecate's 35% low-health
  recalls after camp damage, not idle trips.
- Fish's builds with their companions: alone −5.6 (fb vs r0); with the camp-aggro priority −3.4 (fbp); with that and
  the 30% line −2.5 (fbp30). The companions recover about half the cost, as the camp-damage mechanism predicts.

## Fish builds, all suites

Fresh seeds x4 = `replays/koi-maps/gen-7104` (264), x5 = `gen-7105` (264), x6 = `central-7106` (92), x7 = `gen-7107`
(264), x8 = `central-7108` (92). Wins out of ladder 34, gen 264, central 92, x1 264, x2 92, x3 264, x4 264, x5 264,
x6 92, x7 264, x8 92.

| label | what | ladder | gen | central | x1 | x2 | x3 | x4 | x5 | x6 | x7 | x8 | all |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| latsize | attempt 1 (hecate + size-scaled cycle horizon) | 22 | 151 | 46 | 134 | 49 | 145 | 132 | | | | | 53.3 (1274) |
| q3 | latsize + camp stuns, peel, end-race banking | 17 | 139 | 48 | 136 | 51 | 152 | 136 | | | | | 53.3 (1274) |
| final | hecate builds, 35% line | 19 | 141 | 46 | 134 | 43 | 142 | 138 | 142 | 46 | 135 | 46 | 52.0 (1986) |
| fbp30 | Fish builds (new version: Home second), camp-aggro priority, 30% line | 17 | 120 | 56 | 125 | 52 | 130 | 125 | 126 | 43 | | | 48.7 (1630) |
| fbo | fbp30 with Fish's old-version builds (Durability second, no Home) | 19 | 131 | 51 | 119 | 49 | 146 | 127 | 135 | 43 | | | 50.3 (1630) |
| fbm | fbo + a Monster emblem first, then Power, on maps with 120+ gem groups or Monoliths beside ordinary camps | 20 | 127 | 52 | 128 | 46 | 145 | 121 | 128 | 43 | | | 49.7 (1630) |
| pre | fbo + a melee body that has attacked steps onto a freed camp tile still in reach of a live member (one per group): freed-tile share 41% -> 52% (Fish 70%) | 15 | 141 | 48 | 134 | 48 | 129 | 136 | 135 | 46 | 132 | 44 | 50.8 (1986) |
| vt | pre + the shopping recall blocked only by camps or visible enemies (payout recalls 16% -> 19%) | 14 | 140 | 49 | 131 | 48 | 131 | 136 | 134 | 45 | | | 50.8 (1630) |
| lazy2 | pre + chaining without hecate's from-altar comparison | 15 | 137 | 51 | 123 | 45 | 121 | 126 | 129 | 49 | | | 48.8 (1630) |
| op2 | pre + openers also when a melee crewmate claiming the group is a step from the monsters' reach (wakes from 4+ unchanged) | 17 | 140 | 48 | 130 | 49 | 130 | 135 | 136 | 48 | | | 51.1 (1630) |
| cr | pre + the second of each pick pair joins its partner's group while it holds a live elk (elk crew 2.53 -> 2.63) | 16 | 129 | 46 | 138 | 47 | 123 | 135 | 133 | 45 | | | 49.8 (1630) |
| lr850 | eng with the late-race line at 850 gems instead of 700 (payout recalls and bag age unchanged) | 12 | 133 | 49 | 135 | 48 | 140 | 135 | 140 | 50 | 122 | 49 | 51.0 (1986) |
| mw10 | eng with max_wait 10 (respawn arrival 39% -> 42%, Fish 86%) | 16 | 122 | 52 | 118 | 43 | 137 | 140 | 124 | 51 | 122 | 48 | 49.0 (1986) |
| stn | eng + a stun worth 80 + the target's Strength (Fish stuns the hardest hitter) | 17 | 134 | 45 | 133 | 50 | 132 | 136 | 131 | 46 | 120 | 52 | 50.2 (1986) |
| **eng (koi)** | pre + Fish's engage as an advance: where hp after the visible burst is 300+ and our local health is 1.5x theirs, `prey` takes the weakest visible enemy within 6, off its spawn | 14 | 133 | 47 | 137 | 47 | 135 | 134 | 139 | 47 | 121 | 47 | **50.4 (1986)** |

Against the older bots (390 each; hecate-v1: nemesis 61.5, rival 69.0, morgana 74.9, aphelios 90.3):

| label | nemesis | rival | morgana | aphelios |
|---|---|---|---|---|
| q3 | 63.6 | 70.5 | | |
| f4 | 59.7 | 71.3 | 74.9 | 91.0 |
| f8 | 55.6 | 73.3 | 74.1 | 89.2 |
| final | 56.4 | 72.8 | 73.6 | 90.0 |
| fbp30 | 60.0 | 65.6 | 73.6 | 91.0 |
| fbo | 60.3 | 69.5 | 74.4 | 90.8 |
| pre | 62.3 | 68.7 | 76.9 | 88.5 |
| **eng (koi)** | 59.0 | 66.7 | 74.9 | 89.5 |

Out-of-fuel turns over the 390 standard games: koi (eng) 175, hecate-v1 132; pre 166/142, fbo 174/165, final 171/162.

- eng fights more than pre (kills 2.9 vs 2.4 a game, deaths 3.4 vs 3.0, hecate's deaths 4.0 vs 3.4; follows a fleeing
  enemy 62%, Fish 59%) at the same win rate against hecate-v1. koi ships it for its Fish-like fighting; pre is about
  1.5 points better against the older bots.
- The 150-gold shopping recall stays rare (17% + 4% of payouts to 150+ gold, Fish 83%): the end-race rules stop
  shopping from 700 gems on either side and within 100 rounds of the enemy's win (a third of each game), and a carrier
  within 5 steps of an altar banks first, as Fish does; dropping the unseen-threat check (vt) changed little.

## Conclusions

- Against hecate, every Fish behaviour that does not cost farming is level, and every one that does costs 2-11 points.
  The best mix found scores 52-54% (hecate builds) or 50-51% (Fish builds); nothing reached the 60% target.
- Why: koi-vs-hecate games are farm races on each side's own groups, about 500 rounds long with 2-3 kills a game.
  Fish's play trades farming efficiency (no Jungle, crews, waiting for respawns, range openers) for fight power, and
  that power has little to act on here. Fish's ladder wins come from fights (6.9 kills a game) against teams that
  fight it.
- Fish's builds need companions: alone they cost 5-6 points (camp damage +16%, more heal trips); with Fish's
  camp-aggro priority and 30% recall line, 2-3; with the old-version table (Durability second instead of Home), about 2.
- Next: koi's shopping recall and banking are the least Fish-like parts left (payout recalls 21% vs 83%, bag age 14
  vs 40) because the end-race rules override them; crews and respawn timing are unchanged from hecate.

# Attempt 3 (2026-10-20, from 06:50 EDT)

Goal: close the gap between "looks like Fish" and "beats hecate the way Fish does", working from the 60 distinct
Fish-vs-hecate scrim games (`replays/scrims/20261018-231915`, `20261019-{074736,143241,152704,153559,154258}`).
Variants are `bots/variants/koi3-<label>/` (gitignored); results in `replays/koi3-ab/<label>-vs-<opponent>-<suite>/`.
Scratch scripts (ab.sh, res.sh and the analysis scripts named below) were in the session scratchpad and are not kept.

## How Fish kills hecate (`tools/koi/killcard.py`)

`py tools/koi/killcard.py --scrims [--skip-map contest]` against `py tools/koi/killcard.py <koi batches> --team koi`.
Ladder maps without contest (54 scrim games; koi 32 ladder games against hecate-v1):

| metric | Fish vs hecate | koi vs hecate-v1 (ladder) | koi vs hecate-v1 (390 standard) |
|---|---|---|---|
| hecate deaths per game (to champions) | 8.2 | 4.8 | 3.8 |
| killer's own deaths per game | 5.4 | 5.3 | 3.4 |
| kills per game (Cassi and Issac once) | 6.2 | 3.4 | 2.9 |
| champion damage dealt per game / per kill | 13.6k / 2.2k | 11.3k / 3.3k | |
| kills from >=90% hp in one round, per game | 0.50 | 0.09 | 0.05 |
| median damage to the victim in its death round | 244 | 163 | 115 |
| killer unseen by the victim in the 3 rounds before | 11% | 7% | 4% |
| killing blow from a bush | 18% | 19% | 8% |
| kills on 40+ carriers per game / gems taken by kills per game | 0.78 / 109 | 0.28 / 43 | 0.21 / 26 |
| hecate drops below 35% hp in combat per game / dies within 20 rounds | 10.0 / 44% | 8.4 / 35% | |
| steals per game, gems (killer / hecate) | 1.35, 81 / 0.70, 41 | 0.88, 57 / 1.19, 75 | 0.87, 46 / 0.78, 46 |
| kills by Stellar / Ren | 50% / 22% | 33% / 23% | 38% / 25% |

With contest (60 games) Fish kills 10.5 a game; hecate dies 14.0 times, Fish 6.8.

- **Conversion, not volume.** Fish deals only 20% more champion damage than koi, and its damaging casts per game and
  damage per cast are the same as koi's and hecate's (Stellar nuke 461 vs 401, 5 casts on champions a game). Fish
  needs 2.2k damage per kill, koi and hecate 3.3k: hecate's hurt bodies escape koi and not Fish.
- **Gold goes to the killers.** Fish's Stellar earns 34% of its team's capture gold and Ren 28% (koi: 19% and 23%). At
  round 400 Fish's Stellar has earned 1,050 gold (Focus 393, 1,418 hp), koi's 484 (Focus 226, 1,036 hp).

## First variants (390 standard games each unless noted; koi itself 194/390 = 49.7% on them)

| label | change | ladder | gen | central | all |
|---|---|---|---|---|---|
| carry | captures go to the burst casters: an ally of higher carry rank (Stellar, Tavi 3; Prism, Ren 2; others 0, ties by index) on a group's tiles makes us step off, and it steps onto a free tile of a cleared group an ally holds | 18/34 | 113/264 | 44/92 | 44.9 |
| tgt | Fish's targeting: basic attacks take a kill, else the lowest health; stuns add the target's threat (max of Strength and its next-turn strike; Strength for damage-free stuns); nukes that do not kill prefer the most hurt | 17/34 | 137/264 | 46/92 | 51.3 (1986 games: 49.7) |
| reach | a chasing caster with its excludes-walking unit nuke ready next turn closes only to the nuke's range (4), into a bush within 2 steps when one is in range | 17/34 | 133/264 | 52/92 | 51.8 |
| c1 | tgt + reach | 15/34 | 132/264 | 47/92 | 49.7 (x1 136/264, x2 52/92) |
| lurk | reach + a caster with its nuke ready next turn waits in a bush within nuke range of a visible enemy that is holding a capture, tributing or under an awake camp | 17/34 | 132/264 | 48/92 | 50.5 |

- carry works as intended (Stellar's share of capture gold 18% -> 32%, Fish 34%; Stellar lands 48% of kills, Fish 50%;
  kills 2.88 -> 3.04 a game, one-round bursts 0.05 -> 0.11) but loses 5 points: tributes are unchanged (893 vs 894 a
  game), and the funnel's walking and the carry's shopping trips cost the race.
- lurk almost never fires (0.01% of turns): on generated maps a busy enemy with a bush in nuke range rarely comes
  into view.
| cf | reach + a retreating caster casts any ready spell worth 40 unless its tile is lethal (was: only casts worth 250, the walk's price) | 16/34 | 143/264 | 41/92 | 51.3 |
| si | cf + Fish's step-in: right after a visible enemy acts, a caster with its nuke ready walks to nuke range when we act first next round (fires 0.14% of turns) | 17/34 | 133/264 | 46/92 | 50.3 |
| holder | reach + an enemy holding a cleared group counts its gems as a bag: chased on its own ground and worth more to kill | 17/34 | 143/264 | 46/92 | 52.8 (1010 games: 52.5, koi 50.8) |
| race | holder + any-risk tributes late in a tight race (changed 1 game) | 17/34 | 143/264 | 46/92 | 52.8 |
| rush | race + a winning or late bag within 12 steps of an altar, with the enemy on 850+ or near its win, ignores want_home and the hit-at-altar retreat | 17/34 | 138/264 | 48/92 | 52.1 |
| carry2 | holder + the carry funnel (Stellar, Tavi, Ren 2; Prism 1) | 18/34 | 119/264 | 52/92 | 48.5 |

## How Fish converts (scrim kill episodes, subagent; scripts not kept)

- Both teams start the same number of engagements (Fish 32.8 a game, hecate 33.9); Fish converts 19%, hecate 11%.
  Most of the extra kills are of healthy victims: from >=90% hp at the first hit Fish kills 16%, hecate 7%.
- **Stats decide.** Rescaling each Fish hit to hecate's Focus for that champion type, only 34% of Fish's kills still
  happen; giving the victim Fish's max hp, 43%; both, 17%. At r300 Fish's Stellar has Focus 300 and 1,500 hp, hecate's
  210 and 862; Stellar and Ren take 62% of Fish's gold (hecate 46%). Fish's team gold is only 11-17% higher.
- **Fish casts what is ready.** With a ready nuke and a visible enemy in range at turn start Fish casts 58% of the time;
  koi 41%, walking instead 44%, mostly in `retreat` (1,056 of 1,590 misses), whose keep-walk threshold (250) a nuke
  under ~300 never clears. cf brings koi to 60% with no win-rate change.
- Not distinctive: bush and unseen kills, priority and acting first, dealers per kill, stun-then-follow, chaser actions.
- Kills come at distance 4 at turn start (55%), rarely after a walk (12%); 41% after a step from >4 to <=5 the turn
  before, mostly right after the target acted (the two-action window).
- hecate (and so koi) ends 13.4 turns a game in lethal exposure (5.4 at >=50% hp), Fish 7.8 (2.2): Fish is harder to make
  lethal, not more careful.

## Where koi's games are decided

- Close races: half of all 390 games end with the loser on 800+ (131 on 900+). In 44 of koi's 196 losses koi had score +
  carried >= 1000 when hecate won (hecate: 36 of 194). Most of those carrier rounds are walks to an altar (638
  carrier-rounds 'B' away from an altar, 116 retreating, 154 tributing): the bags are far from altars, not refused.
  Instances: `b4204b6e548b8747` (rushbait-v2, 978 vs 856 at r644, the 22 gems needed are 30 steps out), `e46239fdb90ee046`,
  `b014e06fe5bc4883` (a 72-gem bag at the altar retreats from a visible enemy), `76eca4e9c2c2bec0`.
- koi's first deaths (113 games on gen and central): median round 105, two attackers, 1.4 allies within 6, 78% already
  under 60% hp five rounds before, 62% in koi's half.
- Early game: on ladder maps Fish leads hecate 141-107 in captured gems at r100 and 301-241 at r200; koi is level
  (115-114, 278-273).
| m1 | rush + cf + tgt + si (the Fish-like fight set) | 16/34 | 135/264 | 48/92 | 51.0 (1274 games: 49.8) |
| join | m1 + a healthy empty-handed body within 10 steps of a teammate's posted chase target walks to it (1.3% of turns) | 15/34 | 127/264 | 50/92 | 49.2 |
| passive | holder with chasing off (`prey` returns nothing) | 14/34 | 132/264 | 44/92 | 48.7 |
| aggro | holder with the engage rule at hp-after-burst 150 and ratio 1.0 | 14/34 | 122/264 | 43/92 | 45.9 |
| nogate | holder with every `fuel_ok` passing (64 out-of-fuel turns a game) | 17/34 | 133/264 | 46/92 | 50.3 |
| tavi | holder with Tavi drafted instead of Varg | 21/34 | 132/264 | 52/92 | 52.6 |
| pair | holder + a Cassi or Issac kill worth two lives | 17/34 | 140/264 | 48/92 | 52.6 |
| leash | holder + hurt targets chased onto their ground below 75% hp (was 50%) | 16/34 | 138/264 | 47/92 | 51.5 |
| e2 | holder with the engage ratio 2.0 (was 1.5) | 20/34 | 143/264 | 47/92 | 53.8 |
| hb | holder with hecate's upkeep builds for every champion (Fish's table off) | 21/34 | 149/264 | 48/92 | 55.9 |

- holder over all 1986 games: 1008/1986 = 50.8% (koi 50.4%): level.
- Chasing is worth about 4 points (passive), and more aggression costs 7 (aggro): koi sits near its best boldness.
| ds | holder with Stellar drafted before Ren (only the ids change: Stellar holds ties and takes tied camp hits) | 20/34 | 118/264 | 50/92 | 48.2 |
| sf | m1 + a stun on an enemy below half health is worth half a life more | 17/34 | 141/264 | 44/92 | 51.8 |
| guard | holder + with the enemy on 800+ and ahead in the race, the empty-handed body nearest the enemy-side altar waits by it with a lock | 17/34 | 139/264 | 46/92 | 51.8 |
| lbank | holder + late in the race an empty-handed body's farm value counts the walk to an altar | 19/34 | 124/264 | 43/92 | 47.7 |
| hbm | hb with Fish's table for Stellar, Prism and Tavi | 16/34 | 146/264 | 47/92 | 53.6 |
| h2 | hb + e2 | 20/34 | 143/264 | 35/92 | 50.8 |
| ag2 | hb with the out-of-fight priority by health left instead of its share | 18/34 | 138/264 | 53/92 | 53.6 |
| lowhold | hb + the holder is the ally with the lowest output (the reverse funnel) | 16/34 | 124/264 | 49/92 | 48.5 |

- hb over all 1986 games: 1049/1986 = 52.8% (fresh suites x1-x8 142, 37, 150, 131, 134, 47, 141, 49): hecate's upkeep
  builds are worth about 2 points over Fish's table, as in attempt 2. They keep Fish's principle on the casters (Stellar's
  upkeep build is Jungle or Power Focus: Focus 175 at r300 against 160 with Fish's table) and swap the front line's
  Bruiser and Durability Health for Jungle: 16% less camp damage taken by r300 (4.8k against 5.7k a game on gen).
- Who holds a capture matters a lot and the current rule (first body on a tile, ties to the lower id) is a local
  optimum: funnelling holds to Stellar (carry, carry2, ds) costs 4-5 points and to the lowest-output ally 7.
| hf | sf (the fight set) with hb's builds | 18/34 | 147/264 | 51/92 | 55.6; 1986 games: **54.0** (x1-x8 153, 43, 147, 140, 138, 43, 144, 48) |
| hfs | hf + stuns stack (a stun on an already stunned enemy keeps its value) | 21/34 | 144/264 | 53/92 | 918 games: 55.1 (hf 56.2 on the same) |
| hfp | hf + pair | 18/34 | 145/264 | 48/92 | 918 games: 55.8 |

**koi = hf from 09:05** (`bots/variants/koi3-final1`: hf with the dead Fish build table removed; plays identically).
Previous koi kept as `bots/variants/koi2-eng`.

- Engine check (corrected by `probe-stunstack`): stuns do not stack. Two stuns before the victim's next turn remove only
  that turn; the 28 scrim cases of `turn` 5 twice were one stun before the victim's turn and one after it.

## koi (hf) against the older bots (390 games each, 2026-10-20)

| opponent | ladder | gen | central | all | hecate-v1 |
|---|---|---|---|---|---|
| rival | 29/34 | 193/264 | 65/92 | 73.6 | 69.0 |
| morgana | 27/34 | 197/264 | 68/92 | 74.9 | 74.9 |
| nemesis | 26/34 | 165/264 | 56/92 | 63.3 | 61.5 |
| aphelios | 28/34 | 247/264 | 86/92 | 92.6 | 90.3 |
