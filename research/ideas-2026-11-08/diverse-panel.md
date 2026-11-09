# Diverse panel: opponents that differ from us, calibrated against live (2026-11-08)

Follow-up to [spar.md](spar.md) and [big-levers.md](big-levers.md), from the user's overfit question (teammate
chat: "use different tunings from your tuning runs to opponent bots / maybe add randomness or slightly suboptimal
moves to past bots / and use more ladder drafts instead of ours"). Tools are in [diverse-tools/](diverse-tools/).
Bodies are in `bots/variants/`, which is gitignored; `diverse-tools/build.sh` rebuilds them. Logs and summaries are in
`~/tmp-offload/diverse/`. No ocean code changed.

**In one line:** an oc-base25 body whose knobs are redrawn at random every 100 rounds, seeded per game and playing
Fish's and Mite's live picks, is the best judge for its cost.
- Its per-map r with live is +0.37 with 8 seeds. That is level with the best design (spar +0.38, all pooled +0.40)
  and far above the current panel's +0.10.
- Its games are independent draws: the cell-clustered CI equals the per-game CI. So its precision grows with seeds,
  where spar's stops at the 512-cell floor of the deterministic ladder.
- **No design reproduces live's chain.** The merges v86 → v91 read +1.4 ±1.9 on 8 noise seeds, +2.6 on everything
  pooled and +6.6 on the current panel, against live's -4.3 ±5.0. The first 4 seeds' +0.2 did not replicate (seeds
  5-8: +2.6).
  - Every design passes a χ² test against live's five independent steps (p > 0.15), so live's noise (±4.6 a step)
    can't rank the designs on signs.
  - On the chain total, the live-draft designs sit z 2.1-2.5 above live and the current panel z 3.0.

## Designs

All play the 128 ladder maps, both sides, 256 games a run. The cand plays its own draft. The chain versions are
oc-base23/25/26/27/29 (v86/87/88/89/91) and oc-s2-soupk27 (v90, soup-k).

| design | members | what |
|---|---|---|
| cur | 2 | the current panel: astraeus-td and proteus-td, with the cand's -td copy (test drafts both) |
| spar | 26 | oc-base29 and 12 knob jitters (±3%), Fish's and Mite's live picks (existing runs) |
| tuneL | 10 | 5 oc-base25 bodies (oc-tune3) × F/M picks: |
| | | **oc6**: oc6's final SPSA iterate; **anti6**: default - 1.5 × oc6's move; |
| | | **agg**: life 0.6, hurt 0.75, retreat ratios 1.4-1.5, camp_risk 0.7, chip 1.4; |
| | | **pas**: the reverse; **greed**: efficiency_power 1.6, mid_gold 1.3, min_bank 40, camp_risk 0.8 |
| noiseL | 8 | 4 noise bodies × F/M (seeds 1310001-4) |
| noise8 | 16 | 8 noise bodies × F/M (seeds 1310001-8) |
| tuneTD | 5 | tuneL's 5 bodies on ladder compositions (test_draft, archive mix), not exact live picks |
| divL / all-L | 18 / 44 | tuneL + noiseL / plus spar |

**Noise body** (`bodies.py`, `dvp_noise.h`): oc-tune3 with oc6's 26 tuned knobs.
- Every 100 rounds, each knob (bar the two that are map-conditioned) is redrawn as default × exp(0.2 N(0,1)).
- The draw is seeded by the walls, the team, the epoch and the member seed, so teammates agree and games replay.
- Its strength is at spar's level: the chain versions win 70.8% against it (spar 68.8%, live 63.7%).

## Calibration

Per-map r: the pooled local win rate on each ladder map (chain versions, all members) against live v86-91 against Fish and r2
Mite (v90's 200 cells left out). Chain: paired by (member, map, side), the CI clustered by (map, side, opponent). Live:
paired by cell, from `cells-r2.tsv`.

| design | per-map r (95%) | v86→87 | v87→88 | v88→89 | v89→91 | v89→90 soup-k | **v86→91** | signs right | χ² vs live (5 df) | games per A/B |
|---|---|---|---|---|---|---|---|---|---|---|
| **live** | | -1.8 ±4.6 | -0.4 ±4.4 | -0.2 ±1.7 | -2.0 ±4.6 | -6.0 ±6.9 | **-4.3 ±5.0** | | | 512 per version |
| cur | +0.10 (-0.08..0.27) | -1.0 ±4.2 | +3.1 ±5.0 | +1.8 ±3.0 | +2.7 ±4.7 | +1.6 ±3.9 | +6.6 ±5.1 | 1/6 | 7.9 | 1,024 |
| spar | +0.38 (0.21..0.53) | +0.5 ±2.9 | +0.3 ±3.0 | +0.1 ±0.9 | +2.5 ±3.1 | +1.4 ±2.8 | +3.3 ±3.5 | 0/6 | 7.0 | 13,312 |
| tuneL | +0.35 (0.16..0.51) | +1.4 ±2.2 | -0.7 ±2.0 | +0.9 ±1.0 | +1.0 ±2.1 | -1.1 ±1.9 | +2.6 ±2.4 | 2/6 | 5.7 | 5,120 |
| noiseL | +0.38 (0.21..0.53) | +0.3 ±2.2 | -0.9 ±2.2 | +0.8 ±1.1 | +0.1 ±2.4 | +0.8 ±2.2 | +0.2 ±2.7 | 1/6 | 5.6 | 4,096 |
| noise5-8 | +0.34 (0.17..0.50) | +0.6 ±2.3 | +0.9 ±2.4 | -0.4 ±0.9 | +1.4 ±2.3 | +1.2 ±2.2 | +2.6 ±2.7 | 1/6 | 6.6 | 4,096 |
| **noise8** | **+0.37 (0.20..0.53)** | +0.5 ±1.7 | +0.0 ±1.7 | +0.2 ±0.7 | +0.7 ±1.8 | +1.0 ±1.7 | +1.4 ±1.9 | 0/6 | 5.9 | 8,192 |
| tuneTD | +0.37 (0.20..0.51) | +0.6 ±2.6 | -0.3 ±2.9 | +0.2 ±1.0 | +2.5 ±2.8 | +1.7 ±2.7 | +2.9 ±3.0 | 1/6 | 7.7 | 2,560 |
| divL | +0.38 (0.19..0.53) | +0.9 ±1.6 | -0.8 ±1.6 | +0.9 ±0.7 | +0.6 ±1.6 | -0.2 ±1.4 | +1.5 ±1.9 | 2/6 | 6.0 | 9,216 |
| all-L | +0.40 (0.23..0.55) | +0.7 ±1.9 | -0.1 ±1.9 | +0.4 ±0.6 | +1.7 ±2.0 | +0.7 ±1.8 | +2.6 ±2.2 | 1/6 | 6.8 | 22,528 |

Points, CAND minus REF; 95% CIs. "Signs right": of the five steps and v86→91. χ²: Σ (panel - live)² / (se² + se_live²)
over the five independent steps. The local gates passed every step at +0.2 to +0.6 (CHANGES 465-471).

**Per body** (`dsummary.py`): single bodies read r +0.23 to +0.38 (noise seeds +0.25..+0.37, the styles +0.23..+0.38,
ladder-comp bodies +0.11..+0.36). Pooling bodies, not choosing one, is what reaches +0.38-0.40, so the gain is less
map-rate noise, not a better body. The weak current panel sits at +0.03 (astraeus) and +0.11 (proteus).

## What it says

- **Draft, then strength.** Every design with live or ladder-comp drafts and an ocean-strength body reads
  0.35-0.40. The current panel (test drafts, weaker or older bodies) reads 0.10, as big-levers found. The draft
  matters more than which tuning or noise the body has; these differences are inside the r's SE (~0.08).
- **Ladder compositions nearly match exact live picks on per-map r** (tuneTD 0.37 against tuneL 0.35). Unlike
  spar's tables, they exist for generated maps. But tuneTD's chain deltas are spar-like (v89→91 +2.5), so the exact
  picks still matter for deltas.
- **Self-play flattery, if any, is small.** spar's body is oc-base29, which is v91 itself, and it reads v89→v91 at
  +2.5. The oc-base25-based live-draft panels read +0.7 (noise8) to +1.0 (tunings), and noise seeds 5-8 alone read
  +1.4, so the difference is within noise.
- **Determinism is what limits spar and the old gates.** With jittered or fixed bodies, members repeat each other's
  games: spar's cell-clustered CI is 2.4x its per-game CI, so its 26 members resolve less than noiseL's 8 (±3.5 against ±2.7 on v86→91). Noise
  members are independent: clustered = per-game.
  - The v86→91 CI is ±2.7 on 4 seeds and ±1.9 on 8, so it shrinks as 1/√seeds. ±1 needs ~30 seeds (~15k games a
    bot, 30k an A/B).
  - That is not a 0.25-point merge gate on its own, but it is a live-like judge with no floor below live's own ±4.6.
- **Overfit or variance?** Every live-like design reads the merges since v86 as level to slightly positive: +1.4
  ±1.9 on noise8, +1.5 ±1.9 on divL, +2.6 ±2.2 all pooled. None reads them as the +2 or more that the stacked gates
  implied, and none as live's -4.3.
  - If the panels are right, live's -4.3 is a -1.7 to -2.2 σ draw: mostly variance, as alext suggested. The
    stacked local +0.2 to +0.6 a step was partly a self-play artefact; the current panel reads +6.6.
  - If live is right, the gap is behaviour that no ocean body has: Fish's and Mite's carries out-earn the same picks,
    as spar found. More tunings or noise did not reach it, and the r plateau at ~0.38 says the same.
  - Either way, a merge should need a non-negative read on a live-like panel as well as the mirror and held-out
    gates.

## The gate

`diverse-tools/dpanel_ab.py CAND REF [--sprt P0,P1] [--alpha A] [--panel ...]`: cand and ref each play spar-dvn1,
spar-dvn2 and onwards (F and M), on the ladder maps, with their own drafts.
- Units are per map: 0.5 + the cand's mean minus the ref's, over every member and side.
- After each member it runs ab.py's SPRT on the units and stops at a decision.
- The default panel is noise seeds 1-32 (bodies built), then the five tunings.
- Runs are named `spar-c<tag>-dvn<k><F|M>` and reused.
- Example, v91 against v86 over seeds 1-4: +0.24 ±2.76 over 2,048 paired games, LLR ±0.05, undecided. Over 8 seeds
  it reads +1.4 ±1.9.

Use it as the **live-likeness gate** next to the held-out SPRT:
- A change that the mirror and held-out suites call H1 but that reads ≤ 0 here after ~16 seeds (±1.4) should not go
  live.
- Bigger changes (draft, macro, carry allocation) can be screened here directly.
- Its maps are the live pool, which is the target. For generated maps, the ladder-comp (td) noise bodies are the
  natural extension (per-map r 0.37 for td tunings), but they are not calibrated here.

## One gate for every stage (2026-11-09, user)

`diverse-tools/dgate.py variants/CAND variants/BASE [--stage screen|live]`: one sequential test replaces the
screen, the held out and the panel.
- **Opponents** (the user's set):
  - block 0: v87 (`spar-o25-F/M`) and v91 (`spar-oc29-F/M`), deterministic, 1,024 games a bot;
  - block k: v87 noise seed k (`spar-dvnk-F/M`, seed 1310000 + k, built on demand), 512 games a bot, each a fresh draw.
  - All play Fish's and Mite's live picks on the 128 ladder maps; the cand and the base play their own drafts.
- **Units:** one per (block, map): 0.5 + the cand's mean minus the base's over the block's games there. These are
  paired by seed, map and side: the same opponent draws face both bots.
- **Test:** ab.py's LLR at 0.505/0.5075 (rule 0). It ends at H0 (≤ -2.94). It marks SCREEN H1 at +2.94, continues, and passes
  the LIVE BAR at ln 99 = 4.595, provided the seeds added after the screen read ≥ 0 on their own.
- **No held out:** every noise seed is a new draw, so the evidence the live bar adds is games the screen never saw.
  That post-screen check is what a held-out suite gave, without fixing a suite that arms get selected on.
- The base's runs are shared by every candidate on the same base.
- **v87 in block 0 is the base itself, so that block is a near-mirror.** It flatters macro and greed changes. As
  one deterministic block among hundreds of noise seeds it carries little weight.

**Fixed and paired (the user's questions).**
- **Fresh settings for every pair, the same draws for both bots.** A noise draw depends only on (walls, team, epoch,
  seed), never on game state. So the cand and the base face the identical opponent sequence in every (seed, map,
  side) game.
- **The sequence is fixed across every test:** block 0, then seeds 1, 2, 3, ... in order. The base's games are
  played once and reused by every candidate, and all candidates are judged on the same games.
- **The confirm stage** is the fixed continuation of that sequence past the screen's crossing. The screen never saw
  those games, so they serve as the held out without a separate suite.
- **Why the seeds are directories:** a bot can't read a per-game seed (games are deterministic), so each seed is
  compiled into its own copy (`spar-dvnk-F/M`). Functionally it is one noise bot drawing fresh settings for every
  game.

**Fewer bots, more maps?** Precision comes from paired games, not from how many opponents play them.
- Each paired game's variance is the flip rate whichever axis it comes from: a new noise seed on a ladder map or a
  new map.
- More maps would broaden coverage, but live picks exist only for the 128 ladder maps. New maps would need
  ladder-comp drafts, which read the same per-map r but spar-like chain deltas. The live pool is these 128 maps, so the
  gate stays on them and draws its fresh games from noise seeds.

**Cost.** Measured on v87-sp-y2 and v87-fs-enemy against oc-base25 (22-23 seeds):
- A unit's variance is 0.062-0.069. The flip rate is 0.24 a paired game, and a unit holds 4 paired games
  (variance ≈ flip rate / 4). So the games inside a map unit are already independent, and further blocking or
  pairing has nothing left to remove.
- **Cost scales with the cand's flip rate f** (unit variance ≈ f / 4). nh-6-3, which only changes Heart of Ruin
  games, flips 6.7% of paired games (unit variance 0.016). At that rate the gate costs about what a mirror held out
  does per piece of evidence (0.016 per 4 cand games against the mirror's 0.030 per 2). The table is for f = 0.24
  (sp-y2, fs-enemy); scale it by f / 0.24.
- Expected cand games (the base's are shared) at the pass bar 0.505/0.5075 (rule 0: pass only above 50.5%;
  4 cand games a unit):

| true effect | screen (LLR 2.94) | live bar (4.595) |
|---|---|---|
| +1.5 pts | ~35k | ~55k |
| +1.0 pts | ~80k | ~130k |
| +0.75 pts | ~245k | ~385k |
| +0.5 pts | H0 after ~245k | |
| +0.3 pts | H0 after ~95k | |
| 0 | H0 after ~50k | |

  At the older 0.50/0.5025, +0.5 would screen in ~80k and +0.3 in ~170k, with their live bars at ~125k and ~265k,
  and a null change would take ~250k to reach H0.
- That is ~4.3x a mirror held out for the same evidence. nh-6-3's mirror held out had unit variance 0.030 per 2
  games: 88% of its units are a 1-1 side split, so the sides nearly cancel. Here a unit's variance is 0.065 per 4
  cand games. The mirror held out decided at 63k games; the gate needs ~270k for the same +0.3. The mirror's
  efficiency is also how it flatters.

**First results (2026-11-09, against oc-base25 at 0.505/0.5075):**
- **v87-nh-6-3: H0** at block 26: +0.07 ±0.41 pts over 14,336 cand games (LLR -3.10). This is re-scored after the
  base's v91 block was found to be the legacy debug-build runs (spar-c25-o29F/M); dgate now pairs only release
  runs. The first read was +0.05, H0. At the old 0.50/0.5025 bar it
  would still be undecided (LLR -0.45). Its mirror held out read +0.30 (H1 at 99%, 62,879 games) and spar -0.53, so
  the mirror gain doesn't carry to live-like play.
- v87-sp-y2 and v87-fs-enemy were still running (`~/tmp-offload/diverse/dgate2-*.out`): +0.47 ±0.70 and +0.40 ±0.74
  at block 36, LLR -0.3.

**Three-way decision (default from 2026-11-09, user).** A single SPRT at 0.505/0.5075 called H0 on any change
probably below +0.75, so a real +0.25 change read as "failed". dgate now runs two SPRTs on the same units, each with
ab.py's bounds ±2.94:
- **REJECT:** the low one (0.4975/0.50) reaches H0, so the change is probably below 50.
- **ACCEPT:** the high one (0.505/0.5075) reaches H1. The gate then continues to the live bar (4.595) on post-screen
  seeds.
- **ZONE:** the low one has reached H1 and the high one H0, both first crossings. The change is probably in about
  50-50.75, and the coordinator makes the call.
- Otherwise it plays on. `--single` restores the old rule; `--no-run` decides from cached games only.
- At f = 0.24 and true +0.25, a ZONE takes ~75k cand games.

**Playing on past ZONE (user, 2026-11-09).** A ZONE crossing is reported but no longer stops the gate (`--zone-stop`
restores that). The gate runs to ACCEPT, REJECT, or NARROWED: a 95% CI of ±0.25 pts (`--ci`). That width tells a
+0.25 change from 0 and leaves the Fish and Mite halves at ~±0.35, enough to read them apart. The result JSON gives
both halves (`fish`, `mite`).

## Flip analysis (2026-11-09)

`diverse-tools/flips.py CAND` tabulates an arm's paired flips against the base by opponent, picks, team size, game
length and map. `condscan.py CAND...` chooses a pick condition on odd seeds and reads it on even seeds.

- **Arm effects are cell-specific and repeat.** For every arm, a (map, side, opponent) cell's net over odd seeds
  correlates with its net over even seeds at r = 0.36-0.59 (chance is ±0.04).
  - So noise seeds re-draw games but not an arm's per-cell direction. The gate's mean is the arm's effect over these
    128 maps against this body.
  - These are effects against the v87 noise body playing Fish's and Mite's picks, not against Fish and Mite.
    Conditioning on map names would fit the body, so variants should condition on mechanism (picks, situations)
    and be read on held-out seeds.
- **fs-enemy** (an enemy Heart of Ruin's damage at its passive averaged over the health it has left):
  - Fish picks +0.57, Mite picks +0.04. Nearly all flips are in enemy-HoR games, as the mechanism says.
  - The gain is smaller when we field a HoR ourselves: Fish games +0.38 with our HoR against +0.77 without; Mite
    games -0.24 against +0.33.
  - The both-sides form is v88 (oc-base26), which read about 0. No pick condition beats the whole arm on held-out
    seeds by more than noise: the best, we lack Willow, reads +0.44 held out against the arm's +0.35.
- **Leads (held out, ±0.8 a half):**
  - mp-chan: we lack Tavi, +0.57 against +0.40 (sent to the miteprio agent, `~/tmp-offload/handoff/chan-flips-for-miteprio.md`);
  - mp-tank: we lack Willow, +0.50 against +0.37;
  - sp-y0: they have Vendetta, +0.54 against +0.24;
  - rv-ctxg3: we lack Vendetta, +0.58 against +0.32;
  - dfp-race-d0: team size 5, +0.82 against +0.16.
- **Built:** `v87-dfp-race-d0-t5`, the opening plan on five-pick teams only. Of these leads it has the largest
  held-out gain and a mechanism: a plan coordinating five bodies is worth more than one committing three. On 3-4
  picks it plays as oc-base25.

**Rule text** (TEST-STANDARD rules 5 and 7, proposed 2026-11-09):

> 5. **Decisions: one gate.** Every A/B is `py research/ideas-2026-11-08/diverse-tools/dgate.py variants/<cand>
> variants/<base>` (dirs under bots/, test_draft off; runs are reused by dir name, so a changed bot needs a new dir).
> - Cand and base play the 128 ladder maps, both sides, own drafts, against Fish's and Mite's live picks. The
>   opponents are v87 and v91 (block 0), then v87 noise seeds 1, 2, ... (512 games a bot each, built on demand).
> - The draws are identical for cand and base and fixed across every test, so the base's games serve every
>   candidate.
> - One SPRT at 0.505/0.5075 (rule 0: pass only above 50.5%) on (seed, map) units:
>   - H0 (LLR ≤ -2.94) = rejected;
>   - SCREEN H1 (≥ 2.94) = a screen pass; the gate continues;
>   - LIVE BAR (≥ 4.595), reached on seeds the screen never saw, which must read ≥ 0 on their own.
> - `--stage screen` stops at the screen. There are no separate screen suites, held outs or panels. Each arm of a
>   sweep is its own dgate. Rule 6's two fuels still apply.
> - Expect a +1.0 change to screen in ~80k cand games and pass the live bar in ~130k; +1.5 in ~35k and ~55k. A null
>   change reaches H0 after ~50k games, a +0.3 one after ~95k.
>
> 7. **Live bar (99%).** Queue only a dgate LIVE BAR H1, built on the current base plus only the arm's diff. Merge
> into the line only on a live paired net > 0 with the local evidence holding.

## Not built: gold or gem cheats (user idea, 22:00)

"Give gold cheats to a bot, like +1000 gold at start": an opponent with an economic head start. Decided against it
for calibration, for three reasons:
- **Strength is not the bottleneck.** Bodies from 66% to 78% local win (tuneTD to tuneL, spar's knob bodies) read
  the same r within noise. The gold gap spar found is *who* gets the gold (carries, +26-42% by r200) over the
  game, not the total at the start.
- **It would distort what decides games.** +1000 gold is ~33 shards in round 1, so the opening fights are a
  different game, and 24 of 31 live version flips diverge before r100.
- **Diversity is already free.** Noise seeds already re-draw every game at no engine cost.

The engine side would mean a new full-game handicap mode. Today the scenario layer is the wasm backend and lab
rollouts from round 2 or later, and its source has another agent's uncommitted edits. If the carry gap is pursued, the
fitting form is a per-team income multiplier on capture shares in run-batch, judged by `spar-tools/fidelity.py`'s
early-gold rows first, then by per-map r.

## Files

- `bodies.py` builds the bodies; `build.sh [N]` rebuilds them all; `runq.sh` runs the calibration queues.
- `dcalib.py [design...]` prints the per-map r and chain tables; `dsummary.py` the per-body rows and the summary table.
- `dpanel_ab.py` is the gate.
- Full output: `~/tmp-offload/diverse/dcalib-full.txt` and `dsummary.txt`.
