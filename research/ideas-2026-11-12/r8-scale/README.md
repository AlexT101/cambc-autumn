# The scaling problem against Fish r8: arms on charybdis 524 (2026-11-12)

Branch `r8-scale-20261112` (from main b4985e544), worktree `/home/ubuntu/wt/r8-scale`. The reference is
`variants/r8s-base`, a frozen copy of bots/charybdis 524 (= the primary checkout's `variants/chy-emb6-524`, source
identical). Every arm is a copy of it under `bots/variants/r8s-*` (gitignored); its diff is in `patches/`.

It follows the two studies of v118's 345 live games against Fish r8 ([v118-fish](../v118-fish/README.md),
[v118-fish-b](../v118-fish-b/README.md)) and takes up what they left unbuilt on the scaling side: the Prism is
out-scaled by one gold-fed enemy and dies with its hoard. The conversion side (parallel banking, the lock, the
escort, gold-aware holds) is the sibling programme r8-convert (branch `r8-convert-20261112`, worktree
`/home/ubuntu/wt/r8-convert`, `research/ideas-2026-11-12/r8-convert/`); it is not repeated here.

## Result

**Nothing here gains against the Fish r8 body, so nothing passed the brief's test and `bots/charybdis` is unchanged.**
What came out is a general gain that is level against that body:

| candidate | head-to-head against 524 | fr8 read (fr8-g25 + Mt3q) | the Fish r8 body alone | the Mite body | std read (Flp4 + Mt3q) | Flp4 alone | fork |
|---|---|---|---|---|---|---|---|
| `r8s-c2` = bf3 + ar | **51.1% (50.6-51.6)** of 40,800 | +0.36 ±0.29 | **-0.14 ±0.44** | +0.85 ±0.38 | +0.64 ±0.26 | +0.44 ±0.35 | -0.39 ±1.62 |
| `r8s-c3` = c2 + phs | **51.3% (50.8-51.8)** of 40,800 | +0.37 ±0.30 | **-0.04 ±0.45** | +0.78 ±0.39 | +0.60 ±0.27 | +0.43 ±0.36 | +0.34 ±1.55 |

The gate reads are pool v4 batches 26-33, which no gate had played: 20,480 fresh maps, 163,840 games a read (81,920
a body). Against a second Fish r8 body, `fr8-g25f` (fishr8 README section 3), c2 reads -0.95 ±0.89 on batches 24-25
and +0.01 ±0.88 on 14-15 for the Fish half (20,480 games each): -0.47 ±0.63 together, level. Out-of-fuel turns in
the head-to-head: c2 +2.5% (260,077 against 253,675), c3 +1.8%. No failed game, broken draft or early loss.

The two pieces that gain (section 3): the fight simulation aims the enemy's turns at our richest bag, and any
carrier of a bag worth a life leaves a stand it falls in (bf3); a winning channel's last turns are kept only while
we outlive them (ar). Neither is an answer to the gold funnel. The answers to it that were built lose or are level:
forcing the Prism's gold into Greed-Health loses 1.2 to 4.0 points and its Prism dies more, not less; pricing the
hoard's position loses 9.4; pricing a retreat's walk by the blow it spares, and fleeing off the home line when no
way home is clean, lose or are level; the Health goal with its shop trip (phs) is level again.

## 1. How the arms were read

- **fr8 / std**: `tools/fgate.py ARM variants/r8s-base --pool v4 --ci 0` (fixed reads, 100k fuel, release builds, own
  drafts; `gate.sh`). fr8 is `--fish-body fr8-g25` with the Mite body Mt3q; std is the standard bodies Flp4 and Mt3q.
  The two reads share the candidate's Mite half, so they are not independent. A batch is 2,560 fresh ladder-v4 maps,
  both sides, both bodies: 20,480 fresh games, the reference's half cached. Figures are candidate minus reference in
  points with the 95% half-width over map units. Screens are pool v4 batches 8-13; the confirmation is batches 26-33,
  which no gate had played (v4 batches 0-7 and 16-23 were other programmes'); batches 14-15 and 24-25 took the
  `fr8-g25f` robustness read. The reference wins about 73% against fr8-g25, 86% against Flp4 and 81% against Mt3q.
- **fork**: `lfork.py`, Study A's `livefork_arms.py` run from this worktree (private builds in
  `~/tmp-offload/r8-scale/lfws`): 337 live v118 games against Fish r8 forked at rounds 300, 450, 600 and 750 with the
  live engine state, the arm and the reference each taking our side against fr8-g25 (two seeds), 2,054 paired
  continuations, standard error clustered by game. The figure is the 95% half-width.
- **profile**: `prof.sh ARM`: the arm against fr8-g25 on parts p0-p1 of v4 batch 0 (1,280 games, the gate's seeds, the
  same games for every arm), every replay kept and extracted; `prismprof.py` (the Prism's build, gold, deaths),
  `lossclass.py` (Study A's classes), `hoarddeaths.py`, `homeside.py`, `runmoves.py`, `groundhazard.py`.
  `dprof.sh` is the same with debug builds, for the bot's `D` lines (`dtrace.py`).
- **h2h**: `h2h.sh`: `tools/ab.py ARM variants/r8s-base --no-test-draft` on fresh `--mix ladder-v4` maps made for this
  programme: seeds 8840000-8840059 (20,400 maps in `~/tmp-offload/r8-scale/suites/h2h-m0..3`, 15 seeds each; used
  once, by c2 and c3). SUITES.md is the primary checkout's and is not edited from here: these seeds are not in it.

## 2. What the local games say (reference against fr8-g25, 1,280 games)

- **The loss classes are the live ones.** 336 losses: hoard-killed 120 (36%; live 52%), unbanked 86 (26%; live 11%),
  overrun 68 (20%; live 24%), outfarmed 55 (16%), hoard lost to a camp 7. We win 20% of the games where a 100+ bag is
  killed. So the body does contain the hoard kill, at 0.126 such Prism deaths a Prism game against 0.282 live.
- **The Prism's build** (median, local / live): max health 1,805 / 1,675 at r400, 2,390 / 2,260 at r600; earned gold
  1,009 / 845 and 1,604 / 1,200; unspent gold 90 / 65 and 186 / 26; its first emblem is Prospector-Health in 86% / 82%
  of games; by r600 it owns 9.1 / 8.1 emblems, 1.3 of them Bruiser-Focus. It holds 46% / 41% of our gold at r400 (our
  Vesper 38% / 41% when drafted). The enemy's strongest champion has 170 / 185 Strength at r400 and 275 / 298 at r600.
- **Who kills the hoard, and when.** Local: 128 deaths with 100+ gems to champions, Vesper 67; before r500 the killer's
  Strength gives a median 14-20 hits for the Prism's health, from r500 on 6.5-7.7. Live: 75 deaths, Vesper 56, 5.4-5.7
  hits from r300 on. In both, one attacker in over half (63 of 128; 44 of 75), and the Prism at a median 97% health
  before the first hit.
- **The fatal run** (first hit to death, a median 5 rounds): the Prism ends a median 1-2 tiles from where it started
  (live: not moved at all in 23 of 75) and is no nearer home. Of its turns in runs that end in a Vesper kill, live /
  local: moved away from the killer 43% / 39%, moved level with it or toward it 25% / 26%, stood and cast 17% / 25%,
  channelling 7% / 0%, stunned 4% / 5%. The killer stood nearer our spawn than the Prism in 23% / 22%.
- **The decision, from debug traces** (123 local deaths from r300): on the turn before the killer's first hit the
  Prism's branch was retreat in 71, farm in 20. Over the 8 turns before it, with the killer within 9: farm 29%,
  retreat steps away 19%, a retreat turn spent standing on a cast 11.5%. In the run itself a fifth of its turns
  (21%) are retreat turns spent standing on a cast.
- **Hazard by ground** (a 100+ bag Prism's deaths to champions a carrying round, off spawn; ground by the bot's own
  bands on d_enemy / (d_ally + d_enemy)): live 1.5e-4 on our ground against 8.2e-4 in the middle band (71% of the
  carrying time); local 0.7e-4 against 3.2e-4. Five times lower at home in both.

## 3. The arms

Mechanism, code, and every read. "b8" etc. are pool v4 batches. A dash means not run.

| arm | mechanism | code | fr8 | std | fork | verdict |
|---|---|---|---|---|---|---|
| phs | Study B's arm on 524: the Prism's shards are Health until 6 basic attacks of the strongest enemy Strength seen fit its max health, and its shop trip is taken when it is under that and its gold buys one such hit of Health | `shop.cc` `current_emblem`, `wants_shop` | +0.32 ±0.48 (b8) | +0.02 ±0.40 (b8) | +0.24 ±1.00 | level |
| gh | Greed-Health offered to the Prism at its true rate (25 shards count as 40: five shards priced as eight while its gold income completes it), chosen by the shop's own pricing, its shards not "begun" so other emblems may come between | `shop.cc` `greed_step`, `begun_emblem`, the buy loops | +0.05 ±0.61 (b8) | -0.08 ±0.58 (b8) | - | level: the shop's price (farm upkeep plus the fight share) almost never picks it; the build is unchanged |
| g0 | the Prism's gold goes into one Greed-Health emblem from its first purchase | `shop.cc` `best_emblem` | -4.00 ±0.97 (b8) | -3.01 ±0.89 (b8) | - | loses |
| g1 | the same after its first emblem (Prospector in 86% of games) | as g0 | -1.90 ±0.86 (b8) | -1.62 ±0.78 (b8) | -1.27 ±1.57 | loses |
| g3 | the same after three emblems | as g0 | -1.32 ±0.81 (b8) | -1.18 ±0.73 (b8) | -1.12 ±1.49 | loses |
| bf | a kill hands the killer the victim's gems, so in the fight simulation the enemy's turns aim at our own fighter while it carries our side's richest bag, worth a life or more (`gem_value` a gem against `life_value`: 16 gems); before, they hit our weakest member first | `model/safety.cc` `fill`, `aim_at`, `aims_elsewhere`, `act` | +0.38 ±0.80 (b8), +0.47 ±0.47 (b9-11) | +0.45 ±0.71 (b8), +0.59 ±0.42 (b9-11) | -0.63 ±1.61 | gains |
| bf2 | bf for every member: the enemy's turns aim at our side's richest bag whoever carries it, also in the allies' own verdicts | as bf | +0.52 ±0.88 (b8), -0.05 ±0.48 (b9-11) | +0.24 ±0.77 (b8), +0.36 ±0.45 (b9-11) | - | no better than bf, worse against the Fish r8 body (-0.70 on b9-11) |
| bf3 | bf, and any carrier of a bag worth a life or more counts its own fall as the Prism and the linked pair do: it leaves a stand, and keeps off a tile, where it falls even if the team wins there | bf + `fight.cc` `stand_lost_at`, `guard.cc` `step_guard` | +0.61 ±0.81 (b8), +0.67 ±0.47 (b9-11) | +0.80 ±0.71 (b8), +0.75 ±0.42 (b9-11) | -0.63 ±1.64 | gains; in c2 |
| rw | a retreat's walk, to a cast that excludes it, is worth the blows the best step spares, priced as their dealers price them (the fall in `kill_distance` on us, bag and all), in place of a flat 210 | `fight.cc` `retreat_walk_value`, `retreat` | -0.71 ±0.75 (b8) | -0.83 ±0.73 (b8) | - | loses: the casts made while retreating pay |
| rf | when every first move of a retreat takes two hits or more on the way home, the escape plan's race is run again with any tile as its goal (a ranged pursuer's walk spends its attack), and steps away from home join the choice | `model/escape.cc` `want_free`, `fight.cc` `retreat_step` | +0.18 ±0.70 (b8) | -0.18 ±0.63 (b8) | - | level, and in the profile the Prism's 100+ bag deaths rise from 142 to 171 (Vesper's from 67 to 94) |
| cmg | Study A's cm (a carrier keeps two more camp phases of health in hand) plus the altar guard's steps: carrying a bag it takes no step that only leads through an awake camp's reach | `fight.cc` `want_home`, `altar_guard.cc` `guard_turn` | -0.13 ±0.52 (b8-9) | +0.10 ±0.47 (b8-9) | - | level, as cm was; not in a candidate (it changes 15% of games for a case seen in a handful of live games) |
| hp | a keeping Prism's farm prices each group off our own ground by the bag it risks there: weight x (1 - hazard x swing x bag / its income a round), from the measured hazard by ground (section 2) and `bank.cc`'s order-quantity terms | `farm.cc` `hoard`, the carry picks | -9.41 ±1.02 (b8) | -9.34 ±0.95 (b8) | - | loses heavily |
| ar | a winning bag's channel within `tribute_window` turns of its end was kept at any risk; now only while nothing in reach kills us before it ends (`tribute_safe`), the round limit's last chance apart | `bank.cc` `tribute_ok` | +0.04 ±0.17 (b8), +0.24 ±0.10 (b9-11) | +0.23 ±0.17 (b8), +0.23 ±0.10 (b9-11) | +0.19 ±0.47 | gains: 65-82 games differ a batch, and it wins most of them; in c2 |
| c1 | bf + phs | | +0.08 ±0.58 (b12-13) | +0.65 ±0.52 (b12-13) | - | superseded by c3 |
| c2 | bf3 + ar | | **+0.36 ±0.29 (b26-33)**: Fish r8 body -0.14 ±0.44, Mite +0.85 ±0.38 | **+0.64 ±0.26 (b26-33)**: Flp4 +0.44 ±0.35 | -0.39 ±1.62 | head-to-head 51.1% (50.6-51.6) of 40,800 |
| c3 | bf3 + ar + phs | | **+0.37 ±0.30 (b26-33)**: Fish r8 body -0.04 ±0.45, Mite +0.78 ±0.39 | **+0.60 ±0.27 (b26-33)**: Flp4 +0.43 ±0.36 | +0.34 ±1.55 | head-to-head 51.3% (50.8-51.8) of 40,800 |

Notes on single arms:

- **Greed-Health does what it was built to do and loses anyway.** g1's Prism has 2,260 max health at r400 (reference
  1,805), 3,625 at r600 (2,390) and 3,950 at r800 (2,845), with 0.62 Greed emblems by r600. Its 100+ bag deaths rise
  from 0.126 to 0.168 a Prism game (the deaths come at a median 2,000 max health, before the emblem completes), and
  it wins 69.1% of the profile games against 73.8%. It gives up the passives (Monster, Capture, Jungle) and the
  Focus shards the Prism's clears and duels run on. From live positions, where Fish's Vesper has her real items, it
  reads -1.3 ±1.6 too (-0.6 ±3.9 from the live hoard-killed losses). More Health alone does not keep the hoard.
- **bf's gain is spread thin, not a fix of the hoard kill.** In the profile our deaths fall from 5.01 to 4.88 a game
  and the gems lost to kills from 76.4 to 72.3; the Prism's 100+ bag deaths are 143 against 142. The gain shows
  against the Mite body (+0.79 on b9-11, +0.85 in c2's confirmation) and Flp4, not against the Fish r8 body.
- **hp** follows from a real gradient (hazard five times lower on our ground) and still loses 9 points: the middle
  band is where the Prism spends 71% of its carrying time because that is where its gems are. This is the same
  result as every hoard caution arm of the two studies, at its largest.
- **Not built.** Gold routing (who holds a gold-heavy capture) and the escort are r8-convert's `rc-gh` and `rc-esc`.
  Early cohesion: neither study isolated a decision, the local traces here add none, and the earlier blind arms
  (LOSSES.md 6, the follow and presence arms in EXPERIMENTS) were level; a new blind arm would repeat them. Early
  pressure on the enemy carry is fishr8's `fr8x-vff` (level from live positions).

## 4. Verified, inferred, and what the gates can price

**Verified**

| finding | by |
|---|---|
| c2 and c3 beat 524 head-to-head | `ab.py`, 40,800 fresh ladder-v4 games each (seeds 8840000-8840059) |
| c2 and c3 gain against the Mite body and Flp4 and are level against fr8-g25 | fgate, pool v4 batches 26-33, unplayed, 163,840 games a read |
| bf, bf3 and ar each gain alone | fgate screens, batches 8-11 (81,920 games a read); ar from 65-82 differing games a batch |
| Greed-Health raises the Prism's health as intended and loses | fgate, the profile, and the fork |
| hp, rw lose; rf, cmg, phs, gh are level | fgate screens, one or two batches each (a screen: ±0.5 to ±1.0) |
| the fatal run's shape (median 1-2 tiles moved, 43% of turns moving away, 17-25% standing on a cast), live and local | replay counts, `homeside.py`, `runmoves.py` |
| the branch before those deaths (retreat 71 of 123, farm 20) | debug-build `D` lines, local games only |
| hazard five times lower on our own ground | replay counts, live (74 deaths) and local (128) |

**Inferred**

- Why bf gains against Mite and Flp4 and not against the Fish r8 body: not traced. The fork read of bf and bf3 is
  -0.63 ±1.6 from live Fish positions, which is noise at that resolution but not a sign of a live gain against Fish.
- That phs helps live: the local reads are level each time (Study B's screen; here alone on b8, and c3 against c2
  on the confirmation batches). Its case is still the live deaths with gold unspent (a median 200-255) and games
  like `05savanna`, where a 632-gem Prism at 1,480 max health died in its tribute channel to five rounds of shots
  from a 285-Strength Vesper, four allies within 4 tiles.
- That ar's small local gain carries over: 7% of the Prism's turns in live fatal runs are spent channelling.

**What the local gates can price.** c2's pieces are ordinary play changes: the gates price them, and they say +1.1
head-to-head and nothing against Fish's stand-in. phs cannot be priced locally (the body kills the hoard at under
half the live rate, and at 8.6 hits where Fish needs 5.7). A live test of c3 against Fish r8 would therefore test
phs, with c2's pieces expected to show against Mite and the rest of the ladder rather than against Fish.

**The rules file.** Nothing seen here contradicts `cambc-rules.yaml`.

## 5. Files

| file | what |
|---|---|
| `gate.sh`, `h2h.sh` | the fr8 and std fgate reads of an arm, and its head-to-head (logs in `~/tmp-offload/r8-scale/gates/`) |
| `prof.sh`, `dprof.sh` | an arm's 1,280 profile games against fr8-g25, release or debug, extracted |
| `prismprof.py` | the Prism's build, gold, deaths, the team's gold shares, channels by length |
| `lossclass.py` | Study A's loss classes on an extract |
| `hoarddeaths.py`, `episode.py` | the Prism's 100+ bag deaths: when, to whom, with whom near; rounds before one, printed |
| `homeside.py`, `runmoves.py` | the killer's side at the fatal run's start; what the Prism did with each turn of the run |
| `dtrace.py` | the bot's branch (D lines) in the rounds before those deaths |
| `groundhazard.py` | hoard hazard by ground |
| `lfork.py` | arms from live positions (Study A's livefork with this worktree's builds) |
| `patches/` | each arm's diff against `variants/r8s-base` |

Data (not in git): `~/tmp-offload/r8-scale/` holds the gate logs (`gates/`), the profiles (`prof/`), the livefork
runs (`lf/`), its build workspace (`lfws/`) and the head-to-head suites (`suites/`).
