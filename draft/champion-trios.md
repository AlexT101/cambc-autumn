# Best three-champion draft for aphelios

Tested 2026-10-14 on aphelios `0b6af4c` (main after the audit fixes).

**Result: Cassi & Issac + Stellar + Ryth.** It averaged 71.9% against the 10 teams from round 1 and won at least 59% against every team tested; the head-to-head with the runner-up, Cassi & Issac + Stellar + Ren, was 49-51. On 4- and 5-pick maps, picks 4 and 5 come from the order below, but these tests did not cover them.

Draft order now set in `draft_preference` of `bots/aphelios`, `bots/baselines/v8` and `bots/baselines/v8-aggro` (it only applies with `random_draft = false`):

| order | champion | evidence |
|---|---|---|
| 1 | Cassi & Issac | in every top team but one; teams without it fell to 47-48% |
| 2 | Stellar | in every top team |
| 3 | Ryth | best third pick with Cassi & Issac + Stellar (68.5%) |
| 4 | Ren | 67.75% as third pick, tied Ryth head to head |
| 5 | Prism | 65.75% |
| 6 | Tavi | 63.25% (Tavi + Stellar + Cassi & Issac co-led round 1) |
| 7 | Marcella | 62.75% |
| 8 | Varg | 62.25% |
| 9 | Vesper Vale | 61.5% |
| 10 | Vendetta | 61.25% |
| 11 | Willow | worst in round 1 by far (Varg + Vendetta + Willow 26%, Cassi & Issac + Varg + Willow 42%) |

The percentages for picks 3-10 are each champion's win rate as the third pick with Cassi & Issac + Stellar. They are measured against the same four opponents (Stellar + Tavi + Varg, Varg + Vendetta + Cassi & Issac, Cassi & Issac + Ryth + Vendetta, Vesper Vale + Varg + Tavi), 392 games each, so about ±2.5% (one standard error). Beyond Ren the order is within noise.

## Method

- Every team is aphelios with a forced draft (`tools/variants/make_variant.py`, padded to 5 picks), played with `tools/variants/matrix.py`. Mirror picks are allowed by the rules, so the question is which team to field, not what to deny.
- Maps: the 49 generated maps in `maps/gen/` with 3 picks, so only the three tested champions play. Every pairing played each map from both sides: 98 games per cell, about ±5% per cell.
- Round 1: round robin of 10 teams. The candidates were hypotheses from the ladder draft report (`replays/.analysis/reports/full-ladder/draft.md`): the meta core (Varg, Vendetta, Cassi & Issac), the Willow and Ren teams top players use, Stellar and Tavi teams, and our previous first three.
- Round 2: the round-1 leaders shared Cassi & Issac + Stellar. Eight new teams (Cassi & Issac + Stellar + each other candidate, plus two without Cassi & Issac) played six reference teams from round 1.
- Final: the two best (third pick Ryth or Ren) played each other and the rest of the round-1 field.

About 10,600 games in all, roughly 35 minutes on 22 threads.

## Results

Cells are the row team's win rate against the column team (98 games each).

### Round 1

| row \ col | varg-vend-cass | varg-vend-ryth | cass-stel-vend | varg-vend-will | cass-varg-will | ren-varg-vend | tavi-stel-cass | vesp-varg-tavi | cass-ryth-vend | stel-tavi-varg | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| varg-vend-cass |  | 61% | 36% | 74% | 56% | 58% | 31% | 56% | 43% | 47% | 51% |
| varg-vend-ryth | 39% |  | 28% | 68% | 54% | 55% | 28% | 51% | 52% | 33% | 45% |
| cass-stel-vend | 64% | 72% |  | 85% | 77% | 74% | 50% | 68% | 61% | 52% | **67%** |
| varg-vend-will | 26% | 32% | 15% |  | 31% | 35% | 19% | 31% | 24% | 21% | 26% |
| cass-varg-will | 44% | 46% | 23% | 69% |  | 51% | 22% | 43% | 40% | 36% | 42% |
| ren-varg-vend | 42% | 45% | 26% | 65% | 49% |  | 32% | 44% | 45% | 38% | 43% |
| tavi-stel-cass | 69% | 72% | 50% | 81% | 78% | 68% |  | 67% | 60% | 57% | **67%** |
| vesp-varg-tavi | 44% | 49% | 32% | 69% | 57% | 56% | 33% |  | 49% | 46% | 48% |
| cass-ryth-vend | 57% | 48% | 39% | 76% | 60% | 55% | 40% | 51% |  | 36% | 51% |
| stel-tavi-varg | 53% | 67% | 48% | 79% | 64% | 62% | 43% | 54% | 64% |  | 59% |

### Round 2

| row \ col | cass-stel-vend | tavi-stel-cass | stel-tavi-varg | varg-vend-cass | cass-ryth-vend | vesp-varg-tavi | mean |
|---|---|---|---|---|---|---|---|
| cass-stel-varg | 56% | 51% | 54% | 65% | 62% | 68% | 60% |
| cass-stel-ryth | 59% | 59% | 61% | 71% | 70% | 72% | **66%** |
| cass-stel-ren | 62% | 54% | 61% | 77% | 63% | 70% | 65% |
| cass-stel-pris | 44% | 46% | 59% | 62% | 70% | 72% | 59% |
| cass-stel-marc | 57% | 47% | 55% | 63% | 66% | 67% | 59% |
| cass-stel-vesp | 43% | 48% | 54% | 66% | 58% | 68% | 56% |
| stel-tavi-vend | 45% | 39% | 51% | 51% | 49% | 46% | 47% |
| stel-ryth-tavi | 42% | 31% | 45% | 52% | 59% | 58% | 48% |

### Final

| row \ col | cass-stel-ren | varg-vend-ryth | varg-vend-will | cass-varg-will | ren-varg-vend |
|---|---|---|---|---|---|
| cass-stel-ryth | 49% | 78% | 86% | 84% | 79% |
| cass-stel-ren |  | 73% | 81% | 74% | 64% |

Over all 10 round-1 teams, Cassi & Issac + Stellar + Ryth averages 71.9% (lowest 59%) and Cassi & Issac + Stellar + Ren 67.9% (lowest 54%).

## Caveats

- **Only aphelios played.** These results measure how well aphelios plays each champion, not how strong the champions are on the ladder. Ladder top teams almost never pick Stellar (1%) and mostly pick Varg and Vendetta (over 90%), which were mediocre here. Willow's low result probably reflects aphelios playing her badly, since she does little besides heal.
- **Only 3-pick maps.** Picks 4 and 5 were never tested together with the trio on 4- and 5-pick maps.
- **One version of the bot.** Changes to how aphelios plays a champion can change the ranking. Rerun after big behaviour changes.

## Reproducing

```
node tools/mapgen/mapgen.mjs check maps/gen     # the picks=3 maps went into a separate --maps-dir
py tools/variants/matrix.py varg,vendetta,cassi varg,vendetta,ryth cassi,stellar,vendetta varg,vendetta,willow cassi,varg,willow ren,varg,vendetta tavi,stellar,cassi vesper,varg,tavi cassi,ryth,vendetta stellar,tavi,varg --no-mirrors --maps-dir <picks-3 maps> --threads 22 --no-replays
py tools/variants/matrix.py cassi,stellar,varg cassi,stellar,ryth cassi,stellar,ren cassi,stellar,prism cassi,stellar,marcella cassi,stellar,vesper stellar,tavi,vendetta stellar,ryth,tavi --cols cassi,stellar,vendetta tavi,stellar,cassi stellar,tavi,varg varg,vendetta,cassi cassi,ryth,vendetta vesper,varg,tavi --maps-dir <picks-3 maps> --threads 22 --no-replays
py tools/variants/matrix.py cassi,stellar,ryth cassi,stellar,ren --cols cassi,stellar,ren varg,vendetta,ryth varg,vendetta,willow cassi,varg,willow ren,varg,vendetta --no-mirrors --maps-dir <picks-3 maps> --threads 22 --no-replays
```

Per-map tables: `replays/matrix-20261014-104734/` (round 1), `replays/matrix-20261014-110220/` (round 2), `replays/matrix-20261014-111809/` (final), which are local only.
