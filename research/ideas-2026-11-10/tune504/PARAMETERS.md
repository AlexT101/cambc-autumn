# Proposed tune8 parameters

All 27 are floats, scaled linearly to [0,1]. No hidden half-to-double defaults. Initial perturbation is 10% of each stated range, decaying with k^−.101; integer discretization is intentionally absent.

| Parameter | Default | Range | Site | Purpose |
|---|---:|---:|---|---|
| `gold_price_scale` | 1.32098 | 1–1.65 | `params.h:151` | Marginal gold value in camp choices; retain map conditioning and clamps. |
| `mid_gold` | 1.25 | 1–1.5 | `params.h:285` | Size of existing midgame gold hump; phase boundaries remain ordered/fixed. |
| `fight_weight` | 0.688214 | 0.45–1 | `params.h:228` | Reactive emblem fight value, newly relevant across Prism ordinal choices. |
| `fight_camp_prior` | 490.123 | 250–750 | `params.h:229` | Shrinkage of observed champion-damage share toward farming early in game. |
| `shop_gain_scale` | 0.751062 | 0.55–1 | `params.h:231` | Shopping-trip saving against travel/heal opportunity cost. |
| `income_prior_gems` | 30 | 15–60 | `economy/shop.cc:273` | Strength of reactive shop income prior; preserves positive denominator. |
| `prior_rounds_per_gem` | 4.5 | 3–6 | `economy/shop.cc:274` | Initial income pace used by passive-emblem horizon. |
| `prior_kills_per_gem` | 0.005 | 0.0025–0.01 | `economy/shop.cc:275` | Initial Hunter/Treasure kill income; healer zero remains hardcoded. |
| `prior_tribute_cut` | 0.015 | 0.0075–0.03 | `economy/shop.cc:276` | Initial passive Tribute time saving, separate from reactive big-bag trigger. |
| `holder_gold_price` | 0.3 | 0.2–0.45 | `economy/capture.cc:73` | Capture-holder assignment and takeover gold value, not engine reward. |
| `efficiency_power` | 1.46538 | 1–2 | `params.h:242` | Relative gold-use efficiency exponent for holders and farming. |
| `pair_hold_share` | 0.549802 | 0.35–0.75 | `params.h:122` | Cassi/Issac capture allocation versus other allies. |
| `rounds_per_gem` | 2.3 | 1.7–3.1 | `bot_parts.h:162` | Remaining farming duration prices shop savings and camp endgame urgency. |
| `cycle_horizon_scale` | 100 | 75–130 | `bot_parts.h:159` | Time discount on farm cycles, preserving map-size scaling. |
| `home_power` | 1.89136 | 1.4–2.4 | `params.h:78` | Enemy-ground discount in camp weight; positive exponent retained. |
| `camp_risk` | 0.457168 | 0.35–0.65 | `params.h:76` | Camp damage charged against available health in target selection. |
| `crew_tank_line` | 0.320324 | 0.24–0.4 | `params.h:87` | Health reserve used in crew tank ranking. |
| `crew_trip_risk` | 0.795274 | 0.6–1 | `params.h:90` | Camp damage used to price crew trips home; positive divisor. |
| `crew_stickiness` | 1.41127 | 1.1–1.7 | `params.h:93` | Keep an established strong-camp operation rather than churn. |
| `crew_rival_factor` | 0.900855 | 0.7–1 | `params.h:94` | Discount competing new crew proposals; cannot become a bonus. |
| `mono_gather_share` | 0.626383 | 0.5–0.8 | `params.h:105` | Required staged Monolith output; wait cap remains fixed. |
| `mono_stickiness` | 1.68305 | 1.3–2.1 | `params.h:108` | Monolith operation commitment relative to ordinary camps. |
| `farm_stickiness` | 1.2 | 1.05–1.4 | `economy/farm.cc:9` | Keep currently selected farming group; target identity unchanged. |
| `recall_health_fraction` | 0.315491 | 0.25–0.4 | `params.h:63` | Base threatened recall line and usable-health pricing; map-conditioned as before. |
| `safe_recall_health_fraction` | 0.109358 | 0.06–0.14 | `params.h:65` | Unthreatened recall reserve; upper bound below map-conditioned recall clamp .1489. |
| `finish_camp_health_fraction` | 0.688171 | 0.55–0.8 | `params.h:74` | Damage fraction allowed when finishing below recall line; unchanged predicate. |
| `heal_trip_fraction` | 0.536285 | 0.4–0.65 | `params.h:140` | Siege heal-trip threshold, after exit from live camp reach. |
