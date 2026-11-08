# Spar: a local opponent whose per-map results track live Fish and Mite (2026-11-08)

Follow-up to [big-levers.md](big-levers.md) slate item 1. Tools in [spar-tools/](spar-tools/), big files in
`~/tmp-offload/spar/`. No ocean code changed.

**In one line:** an ocean-family opponent playing Fish's and Mite's *exact* live picks on each ladder map and side
raises the per-map correlation with live from 0.0-0.2 (every earlier local opponent) to **0.33-0.36**. It also puts
ocean's local win rate at the live level (66-69% against live 64%).

- **Draft:** most of the old blindness was the draft.
- **Behaviour:** the rest is behaviour, and it doesn't fall to knobs. Fish's and Mite's carries out-earn the same
  picks played by an ocean body by 30-90% at r200.
- **The bar isn't reached:** r ≥ 0.4 isn't met, where a second top bot would sit at about 0.46.
- **A/B deltas:** v86→v89 and soup-k don't show their (non-significant) live sign. Its deltas are no more precise
  than live, because 128 ladder maps × 2 sides × 2 opponents is only 512 deterministic cells for both.

**Use:**
- Per-map diagnosis: which ladder maps we lose to Fish- and Mite-like play.
- A first-pass check of large changes on the live pool.
- Not 0.5-point merge gates.

**Next lever:** carry-first gold allocation in a spar body, measured by `fidelity.py`'s early-gold rows before any
r run.

## Target and bar

- **Live target:** v86-v89 scrims against Fish and against r2 Mite (Mite changed bots at v86's r2; its r1 games are
  dropped), 2,031 deterministic (version, map, side, opponent) cells, 16 per map, 64.3% won (`spar-tools/live.py`).
- **Reliability of the target:**
  - Fish against Mite per map: r = 0.38 in this era (big-levers' 0.55 mixed in r1 Mite).
  - v86-87 against v88-89: 0.68. Side a against side b: 0.47.
- **What r a good opponent can reach.**
  - An independent opponent as close to Fish and Mite as they are to each other (ρ = 0.38 with each) would score
    2ρ/√(2+2ρ) = **0.46** against the pooled target.
  - A perfect clone would approach the target's own reliability (~0.7-0.8).
  - So 0.4 is a "nearly another top bot" bar.
- **Held out:** maps split in halves by md5 of the name. Bodies were compared on both halves. The body choice is
  within noise, so the pooled r on all 128 maps is the headline, with both halves shown. The SE of r on 128 maps is
  about 0.08.

## Calibration: per-map r with live

Cand = the live versions themselves (oc-base23/25/26/27 = v86/87/88/89, own drafts), so each local cell pairs with a
live cell.

| opponent setup | games / map | ocean local win | r (95% CI) | halves | r Fish / Mite |
|---|---|---|---|---|---|
| earlier local opponents (8 bots, big-levers runs, oc-base27) | 2 each | 54-99% | -0.10..+0.20 | | |
| same 8 pooled | 16 | 79.7% | +0.15 (-0.02..+0.32) | +0.25 / +0.05 | |
| oc-base29 on its own draft (near mirror) | 8 | 48.9% | +0.06 (-0.10..+0.22) | +0.18 / -0.07 | |
| **spar-oc29** (oc-base29 body, live drafts) | 16 | 69.2% | **+0.33 (+0.16..+0.48)** | +0.32 / +0.34 | +0.27 / +0.28 |
| spar-o29s (life_value 443, hurt 0.55) | 16 | 66.4% | +0.33 (+0.16..+0.47) | +0.33 / +0.32 | +0.29 / +0.26 |
| spar-o29gs (o29s + gold_price_scale 2.0) | 16 | 65.9% | +0.36 (+0.20..+0.51) | +0.44 / +0.26 | +0.36 / +0.24 |
| spar-o29g (gold_price_scale 2.0) | 16 | 67.2% | +0.25 (+0.07..+0.41) | +0.39 / +0.10 | |
| spar-o29b (braver: life_value 150, hurt 0.30) | 16 | 69.7% | +0.24 (+0.08..+0.39) | | |
| spar-o29c (camp-bold: camp_risk 0.25, finish 0.9) | 16 | 69.3% | +0.20 (+0.02..+0.37) | | |
| spar-o29t (life_value 690) | 16 | 68.6% | +0.26 (+0.09..+0.41) | | |
| five ocean-knob bodies pooled | 80 | 68.6% | +0.32 | +0.34 / +0.31 | |
| other bodies with live drafts, oc-base27 only: v83 / o10 / astraeus / diana / v69 / proteus / bots/fish | 4 | 75-99% | +0.20 / +0.22 / +0.16 / +0.20 / +0.14 / -0.03 / +0.01 | | |
| oc-base29 body with unlimited fuel, oc-base27 only | 4 | 66.6% | +0.20 | | |
| **jitter panel**: spar-oc29 + 12 jittered copies (j1-j12), oc-base27 only | 52 | 68.6% | **+0.34 (+0.19..+0.48)** | +0.38 / +0.30 | +0.29 / +0.27 |
| *reference: live Fish against live Mite* | | | 0.38 | | |

- **The draft is the big step.** The same body on its own draft reads 0.06 and on the live drafts 0.33.
  - Local drafts reproduce live exactly: in all 512 checked games (oc-base27 against spar-oc29-F and -M), both teams'
    picks equal the live game's. Ocean's draft is deterministic given the revealed picks.
  - The 12 maps lost ≥ 75% live are won 49-56% against spar, against 81% against the old opponents. 00fragment reads
    19-25% and 03ultrastarvation 38-44%, so the spar beats oc-base27 on both (big-levers' fidelity gate).
- **Strength matters, and a weak body flattens the map signal.** bots/fish, proteus and v69 lose 84-99% even on live
  drafts and read ≈ 0. The ocean bodies at 66-69% (near live's 64%) read best.
- **Ocean-family knobs plateau at 0.33 ± noise.** Seven bodies span 0.20-0.36, which is within about two SEs of each
  other. Pooling them doesn't beat the best single body (0.32-0.35), so the shortfall is shared behaviour, not
  local noise.
- **Cells don't transfer.** A deterministic local cell agrees with its live cell 59-61% of the time (phi
  0.07-0.14), barely above the 54% base rate. Outcomes are chaotic per game, so only per-map rates carry signal.

## What is left: behaviour, not draft or maps

`spar-tools/fidelity.py` and `early_types.py` pair 500 v89 live games with the same (map, side, both drafts) game
against spar-oc29 (decoded: `~/tmp-offload/spar/ana`, `ana-gs`). The live opponent, against the spar body playing
the same picks:

| per game, the opponent team | live Fish/Mite | spar-oc29 | spar-o29gs |
|---|---|---|---|
| gold earned by r200 | 1,029 | 901 | 935 |
| gold earned by r400 | 2,263 | 1,984 | 2,082 |
| lifetime gold | 5,199 | 4,801 | 5,150 |
| gems captured | 948 | 862 | 848 |
| damage to champions | 20.9k | 24.3k | 23.6k |
| damage to camps | 86.0k | 78.5k | 81.8k |
| kills (ours) | 6.4 (7.3) | 5.4 (9.2) | 6.0 (8.6) |

- **They farm more and fight less than an ocean body with their comp.** The gold goes to their carries.
  - By r200, Fish's and Mite's Vesper Vale earns 32-42% more than the spar's.
  - Heart of Ruin earns 20-84% more, Marcella 24-89% more, Prism +49-63%.
  - Issac and Mite's Tavi earn less: Mite's Tavi is a support, and the spar's farms gold.
- **The early gold gap tracks the flips.** In the 118 games that live lost and spar won, the live opponent had 1,100
  gold by r200 against the spar's 876 (+26%). In the 85 reverse flips it was 1,061 against 1,057.
- **The knobs moved the team totals toward live but not the allocation.** o29gs closes lifetime gold (5,150 against
  5,199) but its carries are still 30-90% behind at r200.
  - The next fidelity step is structural: carry-first gold allocation (who takes the capture shares and the
    last hits), not a price.
- **The maps themselves.** The live-minus-spar residual is largest on open maps (openness ρ -0.27) and on capture
  races with few kills (00lanes 0% live against 62% spar, 04waves 0 against 75%, 04orchard, 00monolith, 00elkring).
  - No single map feature explains it (|ρ| ≤ 0.27).
  - The forced drafts exist only for the 128 ladder maps. On fresh mapgen suites the spar plays oc-base29's own draft,
    so there it is just a mirror.
  - A Fish/Mite draft *model* for unseen maps would be needed to take the spar off the ladder pool. That is
    reasonable for live, whose pool is these 128 maps.

## A/B deltas: does it see the live sign?

The panel is spar-oc29 plus j1-j12, each against Fish's and Mite's drafts: 6,656 games per bot, paired by
(member, map, side). CIs are clustered by (map, side, opponent) cell, because jittered members repeat each other's
games. Live is paired by cell.

| change | spar panel | live |
|---|---|---|
| v86 → v87 (oc-base23 → 25) | +0.5 ±2.9 | -1.8 ±4.6 (512) |
| v87 → v88 (25 → 26) | +0.3 ±3.0 | -0.4 ±4.4 (495) |
| v88 → v89 (26 → 27) | +0.1 ±0.9 | -0.2 ±1.7 (495) |
| **v86 → v89** | **+0.9 ±3.4** | **-2.3 ±4.9** (512) |
| v89 → v90 (27 → soup-k on 27) | +1.4 ±2.8 (+2.3 ±4.6 on live's 200 cells) | **-6.0 ±6.9** (200, partial) |
| v87 → v90 | +1.7 ±3.2 | -4.5 ±7.4 (200) |
| oc-base25 → oc-base29 | +2.8 ±3.2 | (not live) |
| oc-base27 → oc-base29 | +2.5 ±3.1 | (not live) |
| oc-base28 → oc-base29 (spar-oc29 only) | -1.2 ±4.3 | (not live) |

- **No: the spar doesn't show the live sign.** The v86→v89 chain and soup-k read slightly positive on it and
  negative live.
  - Neither side is significant. The differences are 3.2 ±6.0 and 7.4 ±7.4 points, consistent with both being
    noise.
  - The oc-base29 rows play ocean against its own body (spar-oc29 is oc-base29), so they may flatter it (the
    mirror-flatters caveat).
- **Per cell, deltas don't transfer at all.** The correlation of spar's per-cell v86→v89 delta with live's is
  +0.01 over 512 cells. A version change re-draws ~30% of the deterministic games locally and live alike, and which
  ones flip is chaos.
- **The precision floor is the map pool, not the opponent.**
  - The ladder is 128 maps × 2 sides × 2 opponents = 512 deterministic cells, live and on the spar alike.
  - A 3% knob jitter re-draws only ~18% of a body's games, so 13 members shrink the CI only from ±5.0 (one body)
    to ±3.4.
  - A spar delta of +0.25-0.5 (the local merge bar) is far below what it can resolve. So is live's (±4.6 per
    512).
  - **Use the spar for direction on big changes and per-map diagnosis, not for 0.5-point merges.** To shrink its CI
    it needs bodies that disagree with each other more (larger jitter, different families) while keeping r. Every
    new family tried here lowered r.

## How to use it

- **Bodies** (bots/variants is gitignored: `spar-tools/build_panel.sh [SRC]` rebuilds the panel from oc-base29):
  - `bots/variants/spar-<body>-{F,M}`: an ocean-family bot plus `src/draft/spar_draft.h`, the live opponent's picks
    per ladder (map, side), keyed by draft.cc's `map_hash` (which includes the team). On other maps it plays its own
    draft.
  - Made by `spar-tools/makespar.sh SRC TAG` (copy, `patch_spar.py`, `gen_table.py`). `hashes.json` holds the 256
    ladder hashes, read from the `SPARHASH` debug line.
  - Jittered copies come from `jitter.py SRC DST SEED` (8 float knobs × (1 + 0.03 N(0,1)); seeds 1200001-1200012).
- **A/B:** `python3 research/ideas-2026-11-08/spar-tools/spar_ab.py bots/CAND bots/REF [--panel o29,j1,...]`
  (26 runs of 256 games a bot, ~15 min on the shared pool). It plays each against every panel member (ladder suite, both sides, own drafts, fast runner) and reuses finished runs.
  It prints the paired delta with a map-clustered CI.
- **Calibration:** `calib.py label=run:ver:opp,...`. `deltas.py BODY,...` gives version-pair deltas against live.
- **Drafts:** cand and ref must play their own drafts (`test_draft` off). The spar's picks answer ours as live did
  only if ours equal the live picks, which holds for ocean's deterministic draft. A cand that drafts differently
  meets the live opponent's picks for the old draft.
