# Dropping our Vesper from the draft against fed-Vesper teams (2026-11-13): REJECT, and the conditional ban loses too

Base and REF: `variants/chy-525` (= bots/charybdis 525). Arm: `variants/draft-drop-our-vesper` = 525 with Vesper
Vale in the draft's team lock (`draft_model.h` `banned = 1u << 1`; `ban-vesper.patch`). The same one-line change as
fwin's `fw-nv` (`../fwin/README.md`), built independently: the games are identical and so are the reads. This note
adds where the loss sits, and why the live signal misleads.

## Idea

Fish r8 and Mite funnel their gold into their own Vesper. Ours would then be a second, poorer carry: she takes 0.43 of
our gold away from the Prism and dies to their fed Vesper, paying her kill gold. Drafting another champion in her slot
should starve their carry. Arm B would ban Vesper only once the enemy shows one: Fish and Mite take Vesper only as
their first pick (74.5% and 82% of live games, `vcheck.py`), so a one-slot delay of ours would see it.

## The live signal (scrim log, v113+, `vcheck.py`, `did.py`)

| opponent | our Vesper | no Vesper | cell-matched against other teams on the same cells (DiD) |
|---|---|---|---|
| Fish r8 | 52.1% of 470 | 63.7% of 300 | −10.9 ±4.7 points (z −2.3) |
| Mite | 59.6% of 1,822 | 71.9% of 913 | −13.5 ±2.7 (z −5.0) |
| other teams | 86.4% | 85.0% | (the baseline) |

The cells repeat across versions with the same draft, so the true z is lower. Our draft is fixed per map, so this is
observational. It was strong enough to build the arm.

## Results against chy-525

fgate `--pool v4 --fish-body fr8-g25 --mite-body mf-f9 --fuel 200000`, batches 0-1 (REF cached), own drafts, release:

| read | win% (95% CI) | maps | games |
|---|---|---:|---:|
| fresh (decides) | 48.41% (47.73-49.08) | 5,120 | 40,960 |
| fresh, Fish | 47.73% (46.82-48.63) | 5,120 | 20,480 |
| fresh, Mite | 49.09% (48.18-50.00) | 5,120 | 20,480 |
| fresh, one-site | 47.30% (46.01-48.58) | 1,525 | 12,200 |
| fresh, multi-site | 48.88% (48.09-49.67) | 3,595 | 28,760 |
| ladder (side read) | 46.88% (43.91-49.84) | 256 | 2,048 |

REJECT at batch 2 (LLR low −3.09, high −4.66). No 100k run (200k first: no gain) and no head-to-head.

## Where the loss sits (`drafts.py`, `units.py`, `featsplit.py`, `bodyv.py`, `obs.py`)

Per-map units (CAND − REF over the map's four paired games), joined to both bots' drafts from draft-only games
(`--rounds 0`), the bodies' drafts from a replay-kept rerun of batch 0 (5,376 of 5,376 games identical to the cached
REF runs), and map features (`features.mjs`):

- **chy-525 drafts Vesper on 62% of fresh maps** (3,172 of 5,120; slot 0 on 57% of them, slot 1 on the rest). The
  other maps are untouched (+0.00). On her maps the ban costs **−2.57 ±1.09** points: **Fish −3.67 ±1.45**, Mite
  −1.47 ±1.47.
- **Every replacement loses**: Vendetta −2.7 (566 maps), Marcella −3.3 (399), Prism −5.3 (254), Tavi −1.5, Heart of
  Ruin −3.8, Stellar −3.7, Ryth −2.0; Ren +0.5 ±3.5 (285) is noise.
- **No map class gains.** It loses most on gem-poor maps (gems_side < 100: −6.94 ±2.71; 100-140: −2.98), the
  opposite of the live split that pointed at them, and on gold-poor maps (gold_side < 400: −6.0). Vesper's +33% gold
  makes her our best gold holder, which counts most where gold is scarce.
- **Arm B is ruled out without building it.** The bodies draft Vesper as often as live (Fish body 80%, Mite body
  85%; live 74.5%, 82%). On our Vesper maps where the body has shown Vesper, which is Arm B's trigger, the ban costs
  **−3.90 ±2.14 against the Fish body** and −1.74 ±2.15 against the Mite body (−1.4 ±6.0 / −5.0 ±7.0 where it has
  not). The mechanism's own condition, an enemy fed Vesper, is where dropping ours hurts most against Fish.
- **The body reproduces the live pattern, and the pattern is map difficulty.** In the body games, chy-525 wins 73.9%
  against fr8-g25 on its own Vesper maps and 78.8% on the others (gap −4.9; Mite body 72.1% / 79.5%, −7.4). Those are
  harder maps against these opponents. Banning Vesper there makes them harder still (70.2%, 70.6%). The live
  correlation is what a draft that takes Vesper on hard, gold-led maps looks like. Vesper is part of our answer on
  those maps, not the cause.

## Fidelity caveat

fr8-g25's Vesper kills less than live Fish's (2.08 against 3.06 a game; Prism gems lost to her 37 against 99,
`../../ideas-2026-11-12/fishr8/README.md`), so the "our Vesper feeds theirs" channel is weaker locally. By its own
numbers that channel is small: our Vesper dies about 0.77 times a game, about 150 gold of kill gold each, against
Fish's ~5,000 team gold by r600. For a ban to pay live, the body would have to be wrong by more than the −3.9 points it
measures against Fish when Fish shows Vesper. Under the standing rules a live test follows only local significance, so
none is proposed.

## Don't retry

- A global ban on our Vesper, or a ban conditioned on the enemy's revealed Vesper (Arm B).
- Reading the live "our Vesper cells lose more" signal as causal: in the bodies the same observed gap exists and the
  ban widens it.

## Files

- `gate.sh CAND FUEL FIRST N`: the fgate call (logs `~/tmp-offload/ddov/`).
- `vcheck.py`, `did.py`: the live split and the cell-matched DiD (scrim log).
- `drafts.py OUT REF CAND MAPDIR...`: draft-only games (run-batch `--rounds 0`) and their picks (drafts.mjs).
- `bodypicks.sh BODY J`: chy-525's batch-J games against a body with every replay kept, for the bodies' drafts.
- `units.py`, `featsplit.py`, `bodyv.py`, `obs.py`: per-map units, splits by features, by the body's Vesper, and the
  observed win rates. Working data in `~/tmp-offload/ddov/` (`units-*.json`, `bodypicks-b000.json`,
  `feat-b01.jsonl`).
