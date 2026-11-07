# Draft7 lab: draft6 repeated with oc-base10 as the player (ocean, 2026-11-06/07)

**Result: level. Not shipped.** The refit changes our team on 45% of maps but reads 50.0-50.3% against oc-base11.
Draft6's F92 model is not stale for the current player. Procedure as [draft6.md](../ideas-2026-11-05/draft6.md).
Tools are in `draft7-tools/`; `pipeline.sh` runs every step after the lab. Large files are in
`/home/ubuntu/tmp-offload/draft7/` (`replays/draftlab/draft7`, `-f92` and `-f92p` are symlinks to it).

## Design (as draft6, new seeds)

- **Player:** `variants/oc-base10` (CHANGES 441). Its draft is draft6-f92, which is also `current_lab`.
- **Opponents:** self, `astraeus-now-1106` and `panel-proteus`, 1/3 each.
- **Prior:** draft6's `prior.json` and `ladder.jsonl`, unchanged. Big-arm's 11-06 archive was still empty.
- **Pool:** the 128 ladder maps plus fresh-590000..590099 (ladder mix), 25,257 maps.
- **Held out, never in the pool:**
  - `d7-e` (590200-239);
  - `d7-held` (590300-339 + 590600-639);
  - `d7-varied` (590400-419, varied mix);
  - `d7-panel` (590500-529 + panel-check-514510).
- **Lab:** 25 features (Thompson and probes as draft5/6), then F92 as a link lab.
- **The base moved during the work:** oc-base11 arrived (CHANGES 449: draft-side facts; `draft_model.h` and
  `map_features.h` are identical to oc-base10's). So the candidates are oc-base11 plus the new header, and the
  A/Bs are against oc-base11.

## Lab and fits

- **Lab:** 999,996 games in 1 h 51 min (3 / 4 / 5 picks: 215,960 / 287,728 / 496,308), 16 batches, 0 errors and 0
  draft mismatches. In batch 0's mixed drafts, ocean won 63.3% against astraeus-now-1106 and 69.2% against
  panel-proteus (draft6: 61.1 and 67.3); self-play side A won 50.4%.
- **25 features:** lam b 4, w 1280, syn 320, dev 256, opp 1, ctr off. CV 0.5572 (no map 0.5775, intercepts 0.5828).
  Draft6's was 0.5698 on its own games.
- **F92** (`draft7-f92`; search over w and dev, one pass, 63 min): w 320, dev 1024 (x4), b 64, syn 320.
  - CV 0.5533, -38 (1e-4) against the 25 features (draft6: -39).
- **Pooled alt** (`draft7-f92p`: draft6's games at weight 0.5, 2.0M games): its model.json came out NaN, and
  `oc-draft7-alt` drafts in id order (24.2%, SPRT H0 at 281 games). It is a fit failure, not a test of pooling. The
  likely cause is the 25,079 prior maps from `draft6/maps.jsonl`. Not debugged.
- **Parity** (`native.mjs` on the 128 ladder maps + fresh-590200, against oc-base11's `src/draft`): 0 key and 0 team
  mismatches, 0 C++ failures. 86 maps differ in the last bit of sq_/pr_ values (libm against V8, as in draft6).
- **`diff -r` against oc-base11:** only `draft_model.h`.
- **Porting:** nothing conflicts with oc-draftfin/oc-base11. The header names the same 92 features in the same
  order, and the feature passes are untouched.

## A/B: `variants/oc-draft7` against `variants/oc-base11`, own drafts, fast runner

| Run | Games | oc-draft7 | 95% CI | one-altar | multi-altar |
|---|---|---|---|---|---|
| d7-e, 2x fuel, SPRT 0.50/0.51 seed 590001 (H0) | 6,443 | 50.0% | 48.7-51.2 | | |
| d7-held, real (lab never saw) | 40,960 | **50.3%** | 50.0-50.6 (by map pair) | 50.5% of 9,080 | 50.3% of 31,880 |
| d7-varied (`--mix varied`), real | 10,238 | 50.1% | 49.3-50.9 | 49.3% of 1,520 | 50.2% of 8,718 |

**Panel** (`d7-panel`, 20,480 games a member, real fuel). oc-base11's own rates were measured alongside.

| Member | oc-base11 | oc-draft7 | diff |
|---|---|---|---|
| astraeus-now-1106 | 60.86 | 60.50 | -0.36 |
| panel-proteus | 69.66 | 69.97 | +0.31 |
| panel-demeter | 72.08 | 71.99 | -0.09 |
| panel-ocean-td | 84.65 | 84.63 | -0.02 |
| baselines/v67 | 80.93 | 81.29 | +0.36 |
| mean | 73.64 | | **+0.04** |

None is down beyond noise (~0.9 points at 20k). The mean is level.

## Picks: draft6-f92 against draft7-f92, on draft7's 25,257 pool maps

- Teams differ on 11,326 maps (45%).
- Shares over all maps:
  - Cassi 97 → 97, Prism 82 → 82, Vesper 60 → 62, HoR 55 → 56, Willow 47 → 50;
  - Marcella 35 → 31, Vendetta 28 → 27, Ren 18 → 21, Tavi 8 → 11, Ryth 11 → 8, Varg 9 → 7, Stellar 2 → 1.
- On the 126 ladder maps:
  - up: Ren 17 → 26, HoR 47 → 52;
  - down: Marcella 37 → 29, Varg 14 → 10, Stellar 6 → 2.
- The direction continues draft6's shift (Willow, Vesper, Tavi and Ren up; Marcella, Ryth and Varg down), but the
  swapped teams are worth about the same in play.

## Conclusions

- **Draft6's data was not stale for oc-base10/11.** Refitting on the current player gives the same CV gap between F92
  and the 25 features and the same direction of picks. The 45% of changed teams are near-ties: 50.3% on 40,960
  held-out games.
- The run of +1.3 to +3 refits stops here. Draft6's gain came from the change of lab design (mixed opponents and a
  ladder-mix pool), not from refitting as such.
- The next draft gain has to come from elsewhere: other features, the ladder prior (11-06+ data), or a fixed pooled
  fit (the NaN above).
- Games: lab 1,000,000 (+ 2,648 smoke); A/B 6,443 + 281 + 275 (2x), 40,960 + 10,238 (real), panel 10 x 20,480.
  Total ~1.27M.
