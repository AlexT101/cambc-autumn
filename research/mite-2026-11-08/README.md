# Mite: draft, priority and policies (2026-11-08)

The ladder team **Mite**, studied with the data and tools of the Fish study
([FISH_MODEL.md](../fish-2026-11-05/FISH_MODEL.md)). Nothing in a bot changed. Rules are imitation rules measured on
replays, not Mite's source.

## Data

- **Decoded ladder games** in `/home/ubuntu/tmp-offload/gaps/analysis/` (the [behaviour-gaps](../ideas-2026-11-07/behaviour-gaps.md)
  set; engine 3.0.0 / cambc 5.0.0): 4,328 Mite sides. 2,810 are from 11-05 (big-arm's archive) and 1,518 from 11-06 21:00
  to 11-07 14:39 (capture.db). Raw replays are in `../repl/{a1105,cap}/<match>.repl26a`. `scripts/index.py` lists them.
- **Own-view data**: 450 games from 11-07 05:00 to 14:59 UTC (Mite's latest stable draft), decoded by the Fish scorecard
  pipeline into `replays/fish-scorecard/mite-1107/` (gitignored). Steps: `scripts/make_manifest.py`, then
  `tools/fish/scorecard/build.py local mite-1107 --batch none`, `metrics.py`, `compare.py`. Its `{A,B}/actor/` caches hold every
  Mite turn from the actor's own view: the start of the turn, the state before every action, and the end. `actor-all/` links
  both halves for the `tools/fish` scripts that take one cache directory.
- Submission versions are not in the metadata. The draft changes (below) show at least 3-4 Mite submissions in the window.
- The scripts in `scripts/` were run from a scratch directory: the pickles they read (`allturns.pkl`, `rich.pkl`, `cfull.pkl`)
  are made by `allturns.py`, `actor_rows.py`/`cfull.py` from the actor caches.

## Priority: recovered exactly for 97.3% of turns

Scored on every Mite turn of the 450 games, 2,071,235 in all (`scripts/mite_prio.py`, scored by `final_eval.py`). The target is
the value written that turn, or the value kept when Mite writes nothing (it writes only on change). Higher values act first.

```text
dead                                                     1050
channel (recall, tribute or teleport) with 1 turn left   18965
contact: an enemy within 4, or within 6 if either side   100 - d  (+ offsets, below)
         is ranged
alert:   an enemy within 8 at the start of this turn     0
         or of the previous one
quiet                                                    1000 + floor(20 * hp/maxHp)
         Heart of Ruin, Marcella                         1025 + floor(24 * hp/maxHp)
           unless below 50% health with an ally within 2 at 65%+ health: 1000 + floor(20 * hp/maxHp)
```

- **Contact** uses the enemies seen at the start of the turn, at the positions seen then. Distances are measured from the
  writer's tile when it writes (after its move), and d is the nearest of those enemies.
- **Alert** measures each start-of-turn sighting from the writer's tile at that turn's start. Team memory and older sightings
  make it worse.
- Mite writes mid-turn, usually after its move and attack and before its recall feint.

| actual mode | turns | exact |
| --- | ---: | ---: |
| quiet | 1,347,751 | 99.70% |
| dead | 241,526 | 99.99% |
| contact | 257,246 | 84.23% |
| alert (0) | 190,393 | 96.32% |
| channel (18965) | 29,538 | 99.72% |
| other | 4,781 | 0% |
| **all** | 2,071,235 | **97.27%** (98.16% ignoring the contact offsets) |

The two halves of the games (by replay hash) read 97.05% and 97.51%. The quiet formulas also hold in Mite's 11-05 submissions:
97.2% for tanks and 98.9% for the rest, on observer data with end-of-round health.

**Contact offsets** (approximate, `offset()`): exact on 76.5% of contact writes, against 60.2% for `100 - d` alone.
- **+2000, retreat**: an enemy within 5 while carrying 10+ gems or at health ≤ 40%. It fires on about 73% of such turns. A single
  weak enemy at 4-5 often leaves it off, and no simple rule on danger or strength explains the rest (`f2000*.py`, depth-6 trees
  87%). It looks like Mite's own fight evaluation.
- **+6460, kill chance**: an enemy at health ≤ 35% within 5, unless retreating at health ≤ 25%. With retreat as well, the retreat
  part adds +1000 instead of +2000 (7460).
- **+3000, rich target**: an enemy carrying 500+ gems within 3 (5000 = 2000 + 3000, 9460 = 6460 + 3000).

**Unexplained**: -1 is written just before a real recall home, only below 35% health, so it follows the go-home decision.
21054, 21158 and 21262 are steps of 104, with no distance pattern; they make up 0.5% of writes.

**What the order does.**
- **Quiet**: healthier acts first. HoR and Marcella act before the others at equal health, so they take the camp hits that tie
  (ties go to the first actor). A hurt one beside a healthy ally steps back.
- **Contact** values (94-99) and alert (0) sit below every quiet value. A champion near an enemy acts after its quiet teammates,
  and the closest of those acts first.
- **Offsets** move a retreating, killing or rich-target champion to the front of its team.
- **Channel**: a champion whose recall, tribute or teleport completes this turn acts first next round.

**Exploitable**: a visible champion's priority can be read (`cambc-rules.yaml` vision.visible_champions). It tells us:
- whether the champion is in contact, and `100 - d`, its distance to the nearest enemy it saw at its turn start;
- whether it saw an enemy within 8 (0);
- its retreat or kill flag;
- whether a channel finishes this turn (18965);
- whether a real recall home has started (-1).

Comparing the contact distance with our own positions shows which of our champions it has spotted, for example whether a bush
ambusher is seen.

## Draft: a fixed function of the map, like Fish's

Within each stable window, the map alone fixes every pick (`scripts/draft3.py`). The share of picks equal to their cell's modal
pick:

| window (UTC) | games | map | map + opponent's earlier picks | map + opponent team |
| --- | ---: | ---: | ---: | ---: |
| 11-05 00-03 | 355 | 100% | 100% | 100% |
| 11-05 08-14 | 820 | 100% | 100% | 100% |
| 11-05 17-23 | 932 | 96.9% | 98.8% | 99.4% |
| 11-06 21 - 11-07 04 | 1,068 | 97.4% | 97.5% | 97.6% |
| 11-07 05-14 | 450 | 99.8% | 99.8% | 99.8% |

- Order changes on a map cluster in hours (11-05 04-07 and 15-23, 11-07 00-04), which looks like resubmissions rather than
  reactions to the opponent. Around 11-05 15-17, Tavi replaced Marcella as the 5th pick.
- Latest orders (11-07 05-14, 450 games): Vesper, Vendetta, HoR, C&I, Tavi (231); Marcella, Vendetta, HoR, C&I, Tavi (75);
  Vendetta, Marcella, C&I (38, 3-pick); Marcella, Tavi, HoR, C&I (33).
- Pool: HoR, C&I, Vendetta, Vesper, Marcella, Tavi, rarely Prism. Mite never picks Willow, Ren, Varg, Ryth or Stellar. Fish takes
  Willow where Mite takes Tavi.
- **First pick by map** (123 maps, `draftmap.py`, `draftfit.py`). A tendency, not a recovered rule: two splits get 81%.
  - Marcella: at most 4 wolves and at most 4 gold clusters (her maps average 19 gem clusters to 4 gold).
  - Vendetta: more than 4 wolves on maps under 30 tall (the 3-pick Vendetta, Marcella, C&I).
  - Vesper otherwise.
  Every 4- and 5-pick draft includes Tavi; 3-pick drafts never do.

## Emblems and shards: one family at a time, chosen per game

Each champion stacks its own main stat: Vesper, Vendetta and Tavi Strength; HoR, Marcella and Cassi Focus; Issac Health. Fish has
one build order per champion, but Mite's family varies by game (`emb.py`, and `shards.py` on the 11-07 window).
- **First shard**:
  - Vendetta: Jungle, Prospector, Monster or Treasure.
  - Vesper: Jungle or Monster.
  - HoR: Jungle or Prospector.
  - Issac: Prospector-H (283 of 391).
  - Cassi: Prospector-F or Jungle-F.
- Shards are bought one family at a time, 2-3 families in the first 10, with Durability-Health shards mixed in. It is not
  parallel buying. What picks the family is not recovered.
- `shards.py` double-counts the 4 shards that form an emblem, so its run lengths are too long.

## Fish's frozen rules applied to Mite

**Camp choice.** Fish's FARM-CHOICE / FARM3 logit, frozen and unchanged, was run through `scripts/farm_mite.py` with the Fish
pipeline (`farm_pipeline.sh`, then the farm3 memory and evaluate steps). Output: [farm3-mite.json](farm3-mite.json). The next
camp of 20,911 episodes:

| model | Mite (11-07) | Fish, seventh cohort |
| --- | ---: | ---: |
| farm3 (team memory, `farm3-fit-all`) | **60.65%** (payout 66.1, spawn 56.1) | 63.53% |
| farm2 (own memory) | 57.66% | 60.69% |
| wait baseline | 49.25% | 48.73% |

Fish's camp scoring predicts Mite's choices almost as well as Fish's own: 11.4 points over waiting, against 14.8 for Fish. Team
memory adds 3.0 points for Mite too (bootstrap +2.5 to +3.5, 449 games). Either Mite shares camp state through its 8 bytes, or
teammates' sightings stand in for its own.

The wrapper avoids adding a Mite manifest to `research/fish-2026-11-05`: `pin_cohort.py` excludes every manifest there, so it
would drop Fish-vs-Mite games from future Fish cohorts. Data: `replays/fish-farm3/mite1107/`.

**Scorecard** (`replays/fish-scorecard/mite-1107/scorecard.md`): 107 metrics; Fish = cohorts 5-7, control =
astraeus-37e1eb6. **Fidelity: Mite 71.1, astraeus 70.1**. Overall, Mite is no more Fish-like than our own bot.

| close to Fish | Fish | Mite |
| --- | ---: | ---: |
| payouts per 1,000 rounds: Marcella, Vesper, Vendetta | 18.6 / 23.3 / 18.1 | 17.4 / 25.1 / 16.9 |
| nearest ally, median | 3 | 3 |
| payouts on own side | 79.9% | 81.2% |
| chase rule (10.3) | 73.9% | 72.5% |
| positioning rule (10.1), ranged | 73.3% | 72.6% |
| hits when an enemy is within 3 | 53.8% | 54.2% |
| gems at tribute start, median | 26 | 29 |

| far from Fish | Fish | Mite |
| --- | ---: | ---: |
| priority encoding | see FISH_MODEL 5 | 0% of Fish's values |
| recall kept at timer 1 | 45% | 99.6% (feints are cancelled earlier) |
| home gate (h ≤ 0.63 or gold ≥ 30) | 98.3% | 84.5% |
| Cassi stuns when her damage spell is on cooldown | 99.3% | 75.8% |
| HoR shields iff threatened | 93.1% | 66.4% |
| basic attacks the lowest-EHP enemy | 94.0% | 82.1% |
| takes an available kill | 98.4% | 90.4% |
| keeps hitting camps, enemy at 5 / at 7-8 | 67% / 83-84% | 39% / 92% |
| steps onto bush among equal steps | 75-89% | 43-52% |
| wards on a bush; wards with no enemy visible | 83%; 3.0% | 59%; 7.4% |
| solo golem clears | 2.3% | 14.0% |
| deaths per game (bodies) | 5.2 | 9.4 |

## Next steps

1. **The retreat decision** behind +2000, and -1 (go home). Both look like Mite's combat and economy choices. Fit them against
   the turn's own action: does it step away, does it recall.
2. **Route, holder and economy models** (`routes_*`, `holders.py`, `econ_*`): their inputs are built in `replays/fish-farm3/mite1107/`.
3. **A Mite sparring partner**: `mite_prio.py` plus Fish's camp logit is a start.
4. **Exploit check**: read enemy priorities in ocean, to detect being spotted and Mite's retreat and kill states. A/B it against
   Mite-like opponents.
