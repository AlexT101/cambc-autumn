# Gold price: the gold-vs-gem exchange rate (ocean = oc-base23, 2026-11-08)

The user's three ideas on `prices().per_gold = gold_price_scale x gems_share x next.saved / next.cost`
(economy/shop.cc) and `gems_share = min(left / alive, rounds / 2.3)`, `left = min(gems_short, 1000 - enemy,
ally_rate x rounds)` (economy/camps.cc): (1) the enemy term, (2) the even split, (3) the scale from data.
Earlier rounds: research/ideas-2026-11-05/value.md (scale 1.0 lost, 2.0 / 2.2 / 3.0 level, a late lean lost).

## Data

### Ladder archive (2026-11-05..07, engine 3.0.0, 374k games; `~/tmp-offload/willow/archive`)

Logistic P(A wins | delta tributed, delta lifetime gold, delta camp damage (`s_farm`), delta rating) at each
checkpoint; rate = coef(gold) / coef(tributed gem). The archive has no carried gems, so gold still stands in part for
untributed captures (the camp-damage control moves it only ~15%).

| max tributed (close games, \|lead\| < 75) | all games | both ratings > 2150 (32.7k games) |
|---|---|---|
| 0-100 | 0.086 | 0.35 |
| 100-250 | 0.143 | 0.57 |
| 250-400 | 0.094 | 0.30 |
| 400-600 | 0.061 | 0.17 |
| 600-800 | 0.035 | 0.072 |
| 800-1000 | 0.016 | 0.022 |

By checkpoint (top games, all leads): 1.04 (r100), 0.68 (r200), 0.48 (r300), 0.40 (r400), 0.26 (r600), 0.16
(r800), 0.095 (r1000), 0.039 (r1400).

### ocean's own per_gold (oc-gp-trace = oc-base23 + a PG line every 25 rounds; 5,120 games against oc-base23 on
`gp-trace`, fresh-673500..673509)

| max tributed | median | mean | enemy term binds | share if dropped / now | pace version / now |
|---|---|---|---|---|---|
| 0 | 0.338 | 0.61 | 0% | 1.00 | 1.00 |
| 1-100 | 0.269 | 0.37 | 21% | 1.01 | 0.97 |
| 100-250 | 0.198 | 0.27 | 14% | 1.01 | 0.92 |
| 250-400 | 0.132 | 0.19 | 15% | 1.03 | 0.91 |
| 400-600 | 0.085 | 0.13 | 20% | 1.05 | 0.90 |
| 600-800 | 0.052 | 0.078 | 26% | 1.14 | 0.88 |
| 800-1000 | 0.011 | 0.023 | 40% | 6.3 | 0.81 |

When the enemy leads by 100+, the enemy term binds half the time; the pace version would cut the share to 0.71x.
The `rounds / 2.3` cap binds ~1%.

Reading: the top-ladder rate sits at or above ocean's mean from 100 to 600 tributed (0.57 / 0.30 / 0.17 against
0.27 / 0.19 / 0.13) and level elsewhere; with the carried-gem confound that is at most a ~1.5x lean mid-game.
Dropping the enemy term mostly matters past 800, where the enemy is about to win and gold is worth nothing: the drop
should lose. The pace version is a 10% cut mid-game, 30% when behind.

### The split (archive 2026-11-06/07, sides with 200+ collected, games of 600+ rounds)

Each body's share of its side's collected gems x side size (1 = even split):

| type | ours | top teams (rating > 2300) |
|---|---|---|
| Vesper | 1.73 | 1.99 |
| Prism | 1.64 | 1.89 |
| Marcella | 1.33 | 1.53 |
| Vendetta | 1.32 | 0.97 |
| Heart of Ruin | 0.92 | 0.81 |
| Willow | 0.62 | 0.33 |
| Issac / Cassi | 0.58 / 0.44 | 0.51 / 0.32 |

The even split misstates a body's share by up to 2x either way. farm.cc already multiplies per_gold by
`relative_efficiency` (gold efficiency over the team mean), which leans the same way for Vesper and Prism.

## Design (knobs `params::gp::` in `bots/variants/oc-gp-dev`, defaults = oc-base23; bench 16/16, wide 52/52 identical)

- `enemy_mode`: 0 now; 1 no enemy term; 2 `ally_rate / enemy_rate x (1000 - enemy)` (World now keeps the enemy's score
  history like the ally's), ratio clamped to [`pace_lo`, `pace_hi`]; before we score, ratio 1.
- `split_mode`: 1 by `camp_output`; 2 Willow at `healer_weight`; 3 by the type table above (`type_share`).
- `mid_mult`: per_gold x (1 + (M - 1) h), h a hump on the higher score (0 -> 1 over 0-100, 1 to 500, -> 0 by 700),
  the data's mid-game lean. `scale_mult`: a flat multiplier on top of the per-map `gold_price_scale`.

Arms (wave 1): em1, em2, em2s (clamp 0.67-1.5), sp1, sp3, sph5 (Willow 0.5), mid15, mid20, sc125. Screens against
`variants/oc-base23`, own drafts, fast runner, `gp-dev` (fresh-673000..673039, 20,480 games at most), SPRT
0.50/0.5025, one seed each. Confirm on `gp-conf` (673100..673199, 51,200), panel `gp-panel` (673400..673419)
against astraeus-td, proteus-td, base-td with both on test drafts, robustness `gp-var` (673300..673309, `--mix varied`).

## Results

(below, and in EXPERIMENTS "gold price (ocean, 2026-11-08)")

- **Enemy term:** keep it. Dropping it (49.7) or reading it at the pace ratio (49.7; clamped 0.67-1.5 50.2 then 50.0
  over 102k; 0.8-1.25 49.8) is level or worse.
- **Split:** keep it even. Every reweighting loses: by camp output 48.9, by the measured type shares 48.9, their
  inverse 48.3 (H0), ^-0.5 49.7. Willow at half or a quarter is level (49.9 over 86k, H0; 50.0).
- **Rate:** the data's mid-game lean holds at a shallow dose. The x1.25 hump (mid125) is 50.3 over 102k decision games
  and 50.45 over 102k held out, panel level, varied 50.8: **merged as CHANGES 466 (oc-base25)**. x1.5 is level on the
  mirror (50.1 over 194k) but best on the panel (+0.62 ±0.53); x2 49.9; a flat x1.25 49.9.
