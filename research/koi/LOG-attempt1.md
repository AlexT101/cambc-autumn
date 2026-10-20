# koi change log

koi starts as a copy of hecate at 110e338 (frozen as `bots/baselines/hecate-v1`). Every A/B is koi (or a
single-change variant in `bots/variants/koi-*`, gitignored) against `baselines/hecate-v1` on the ladder maps (34
games), `maps/gen` (264) and `maps/gen-central` (92), both sides, real fuel budget. Win rates are koi's; noise is
about ±2.5 points on all 390. Results land in `replays/koi-ab/<label>-<suite>/`.

## Reference: hecate-v1 against the older bots

| opponent | ladder | gen | central | all 390 |
|---|---|---|---|---|
| rival | 79.4 | 65.5 | 75.0 | 69.0 |
| morgana | 76.5 | 72.3 | 81.5 | 74.9 |
| nemesis | 70.6 | 59.1 | 65.2 | 61.5 |
| aphelios | 79.4 | 90.5 | 93.5 | 90.3 |

## Single Fish behaviours on hecate (2026-10-19)

Each is hecate-v1 plus one change.

| label | change | ladder | gen | central | all | kept |
|---|---|---|---|---|---|---|
| k01-builds | Fish's fixed builds (Focus casters, Bruiser/Durability Health front line, Home second) | 52.9 | 43.9 | 52.2 | 46.7 | no |
| camp | basic attacks on the lowest-hp camp in range | 47.1 | 48.5 | 44.6 | 47.4 | no |
| recall30 | low-health recall at 30% instead of 35% | 44.1 | 47.3 | 58.7 | 49.7 | no |
| shop150 | capture recall / shop trip whenever the next emblem is affordable (no gain pricing); a carrier within 5 steps of an altar banks first | 64.7 | 47.3 | 55.4 | 50.8 | no |
| holders1 | one holder on every capture (Monoliths and big groups too) | 44.1 | 48.9 | 48.9 | 48.5 | no |
| wait15 | wait up to 15 rounds (not 5) for a respawning group | 50.0 | 42.0 | 50.0 | 44.6 | no |
| prio | out of fights, healthy empty-handed bodies act first (camps hit the first tied actor) | 50.0 | 48.5 | 44.6 | 47.7 | no |
| hurt30 | hurt line 30% instead of 50% (pack retreat ratio, pursuit check) | 44.1 | 53.0 | 56.5 | 53.1 | no |
| chase | chase off our ground without the intercept test (any healthy-or-hurt enemy, carriers) | 58.8 | 50.8 | 48.9 | 51.0 | no |
| draftsp | hecate's reverted shared-gem caster draft (Stellar, Ryth, Prism, Ren, Cassi, Varg) | 52.9 | 50.0 | 51.1 | 50.5 | no |
| draftfish | Fish's shared-gem draft (Stellar, Tavi, Prism, Cassi, Ren) | 50.0 | 49.6 | 50.0 | 49.7 | no |
| bold | the fight simulation lets us strike first (`trade(..., they_first = false)`) | 47.1 | 51.9 | 46.7 | 50.3 | no |
| lat25 / lat50 / lat100 / lat200 | farm value worth / (cycle (1 + cycle / L)) instead of worth / cycle | 61.8 / 64.7 / 61.8 / 58.8 | 52.3 / 51.1 / 53.8 / 50.8 | 47.8 / 52.2 / 52.2 / 54.3 | 52.1 / 52.6 / 54.1 / 52.3 | lat100 |
| crewcast | a ranged crew member counts no camp damage when a melee claimer tanks | 58.8 | 47.7 | 48.9 | 49.0 | no |
| c1-c4 | lat100 + hurt30 (+ chase, + shop150, + builds) | 52.9 / 47.1 / 61.8 / 50.0 | 51.5 / 49.2 / 52.3 / 47.0 | 46.7 / 46.7 / 48.9 / 47.8 | 50.5 / 48.5 / 52.3 / 47.4 | no: the gains do not add |

## On koi = hecate + lat100 (1010 games: the 390 plus two fresh gen suites and a fresh central suite)

Extra suites, built with `node tools/mapgen/mapgen.mjs suite gen|central --out ... --seed S` into `replays/koi-maps/`:
x1 = gen seed 7101 (264 games), x2 = central seed 7102 (92), x3 = gen seed 7103 (264). Noise on 1010 games is about
±1.6 points.

| label | change | ladder | gen | central | x1 | x2 | x3 | std 390 | all 1010 | kept |
|---|---|---|---|---|---|---|---|---|---|---|
| lat100 (koi) | worth / (cycle (1 + cycle / 100)) | 61.8 | 53.8 | 52.2 | 51.9 | 52.2 | 53.0 | 54.1 | 53.1 | yes |
| latsize | horizon 100 × max(1, map side / 50) | 64.7 | 57.2 | 50.0 | 50.8 | 53.3 | 54.9 | 56.2 | 54.2 | no (level) |
| guard | allies strike the enemy nearest a visible ally's winning tribute, at any risk | 64.7 | 53.4 | 44.6 | 53.0 | 50.0 | 54.2 | 52.3 | 52.8 | no |
| endrisk | with the enemy on 800+, a bag that completes the team's win goes in at any risk | 61.8 | 53.8 | 53.3 | 51.9 | 53.3 | 53.0 | 54.4 | 53.3 | no (level) |
| sweep | camp_risk 0.25 / 0.5, home_power 1 / 3, max_wait 2 / 8 | | | | | | | | 52.3 / 53.8 / 50.3 / 51.4 / 50.1 / 50.1 | no |
| lazy | bank only once the bag is 5 gems a step to the altar; no capture recall just because home is nearer an altar | 61.8 | 49.2 | 52.2 | 53.4 | 54.3 | 51.1 | 51.0 | 52.0 | no |
| gfw1 | Cassi's gold weight 1 instead of 4 | 58.8 | 54.9 | 54.3 | 50.8 | 48.9 | 51.9 | 55.1 | 52.6 | no |
| opener | the whole team opens on the group with the most gems / (spawn steps + hp / team output + 7) on our side | 64.7 | 47.7 | 41.3 | 51.9 | 57.6 | 53.0 | 47.7 | 51.1 | no |
| opener2 | opener capped at 5000 hp | 67.6 | 47.3 | 42.4 | 51.5 | 54.3 | 53.4 | 47.9 | 50.9 | no |

## Later runs (attempt 1, stopped 2026-10-20 00:00; tabulated from `replays/koi-ab/*/results.json`)

koi itself ended as hecate-v1 plus `lat100`: farm-cycle values divided by `rounds * (1 + rounds / 100)` instead of `rounds` (bot.cpp `rate`). Each variant below is a single change in `bots/variants/koi-<label>/` (gitignored); diff it against `bots/baselines/hecate-v1/src` to see it. x1-x3 are fresh-seed suites (`replays/koi-maps/gen-7101`, `central-7102`, `gen-7103`).

| label | ladder | gen | central | x1 | x2 | x3 | all |
|---|---|---|---|---|---|---|---|
| lat100 (kept) | 21/34 | 142/264 | 48/92 | 137/264 | 48/92 | 140/264 | 53.1 |
| lat200 | 20/34 | 134/264 | 50/92 | | | | 52.3 |
| lat50 | 22/34 | 135/264 | 48/92 | | | | 52.6 |
| lat25 | 21/34 | 138/264 | 44/92 | | | | 52.1 |
| latsize (horizon grows with map size) | 22/34 | 151/264 | 46/92 | 134/264 | 49/92 | 145/264 | 54.2 |
| bold | 16/34 | 137/264 | 43/92 | | | | 50.3 |
| crewcast | 20/34 | 126/264 | 45/92 | | | | 49.0 |
| c1 | 18/34 | 136/264 | 43/92 | | | | 50.5 |
| c2 | 16/34 | 130/264 | 43/92 | | | | 48.5 |
| c3 | 21/34 | 138/264 | 45/92 | | | | 52.3 |
| c4 (bundle incl. fixed builds) | 17/34 | 124/264 | 44/92 | | | | 47.4 |
| guard | 22/34 | 141/264 | 41/92 | 140/264 | 46/92 | 143/264 | 52.8 |
| endrisk | 21/34 | 142/264 | 49/92 | 137/264 | 49/92 | 140/264 | 53.3 |
| cr25 | 17/34 | 142/264 | 44/92 | 129/264 | 47/92 | 149/264 | 52.3 |
| cr50 | 15/34 | 141/264 | 49/92 | 143/264 | 51/92 | 144/263 | 53.8 |
| hp1 | 16/34 | 134/264 | 42/92 | 142/264 | 43/92 | 131/264 | 50.3 |
| hp3 | 17/34 | 137/264 | 47/92 | 132/264 | 46/92 | 140/264 | 51.4 |
| mw2 | 15/34 | 131/264 | 49/92 | 138/264 | 41/92 | 132/264 | 50.1 |
| mw8 | 16/34 | 132/264 | 41/92 | 148/264 | 44/92 | 125/264 | 50.1 |
| lazy (bank at ~5 gems a step) | 21/34 | 130/264 | 48/92 | 141/264 | 50/92 | 135/264 | 52.0 |
| cb50 (partial) | 21/34 | 57/91 | | | | | 62.4 |
| cb130 | 21/34 | 136/264 | 46/92 | 138/264 | 50/92 | 139/264 | 52.5 |
| opener | 22/34 | 126/264 | 38/92 | 137/264 | 53/92 | 140/264 | 51.1 |
| opener2 | 23/34 | 125/264 | 39/92 | 136/264 | 50/92 | 141/264 | 50.9 |
| gfw1 | 20/34 | 145/264 | 50/92 | 134/264 | 45/92 | 137/264 | 52.6 |
| cs30 | 21/34 | 141/264 | 48/92 | 136/264 | 45/92 | 132/264 | 51.8 |
| cs08 | 19/34 | 142/264 | 43/92 | 136/264 | 42/92 | 131/264 | 50.8 |
| st14 (partial) | 18/34 | 131/264 | 47/92 | 30/58 | | | 50.4 |

Lesson: Fish behaviours bolted one at a time onto hecate's planner, and parameter sweeps around them, all landed at 47-54%. Attempt 2 restarts koi from hecate and rebuilds subsystems around Fish's play as a whole.
