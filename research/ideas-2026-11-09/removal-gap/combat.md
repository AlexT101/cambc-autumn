# Removal gap: the combat-model features (467, 468, 471 cast_cost / fight_weight, c1)

Fork of the removal-gap investigation (2026-11-09). Everything here is on `variants/ocean-rm2` (CHANGES 486) unless
named. Release builds, own drafts, fast runner. Tools in `tools/` here (hordash*.py, horpas*.py, contact.py, cmb*.py,
pair.py, hdash_out.py); scratch data in the session scratchpad `gap/`.

## Data

- **Per-feature arms** (`variants/gap-ana-<f>` = rm2 + that feature's hunks, analysis only) against rm2 on `ocrm-1921`
  (40,960 games each), paired game by game with the rm2-vs-rm2 mirror (`gap-mirror`, exactly 50.00%):

  | Arm | Win % | Paired vs mirror | Flips | OOF CAND / REF |
  |---|---|---|---|---|
  | 467 fight_scale | 50.30 | +0.30 ±0.37 | 24.9% | 487,981 / 484,899 |
  | 468 landing_floor | 50.21 | +0.21 ±0.21 | 5.9% | 491,748 / 489,392 |
  | 471 (all three soup-k constants) | 50.52 | +0.52 ±0.43 | 33.5% | 484,091 / 482,368 |
  | c1 caps | (see below) | | | |

- **Subset** `merged/gap-csub` (1,024 ocrm-1921 maps, every replay kept): mirror, 467, 471, 471c (cast_cost only),
  471w (fight_weight only), c1 arms, extracted for paired behaviour (`pair.py`).
- **Trace**: `variants/gap-dbg-hor` = rm2 + one `debug_block` (`HDASH`) on every Heart of Ruin landing chosen by
  `cast_at_enemies` (the non-search fallback that 468's floor gates), debug build against rm2 debug on gap-csub.
- **Live**: our v86-v95 r2 games against Fish (inte) and Mite (~/tmp-offload/handoff/gate/analysis): v87 = oc-base25,
  v88 = +467, v89 = +467 +468, v95 = v87 + nh-6-3.

## 468 landing_floor (hurt Heart of Ruin lands on champions only for 2x the value)

**Where it acts (verified, trace).** 468's floor gates only `enemy_cast` (abilities.cc), the fallback cast path the
strike search does not cover. Every HoR landing it chose on gap-csub (rm2, debug, 2,048 games), by branch, health and
value, with the HoR's death and enemy deaths within 4 rounds (replay):

| Branch | Health | Value | Landings | HoR dies within 4 | Enemy deaths within 4 |
|---|---|---|---|---|---|
| retreat | < 0.6 | < 500 (468 refuses) | 634 | 0.26 | 0.06 |
| retreat | < 0.6 | >= 500 | 324 | 0.41 | 0.15 |
| retreat | >= 0.6 | any | 666 | 0.05-0.10 | 0.03-0.08 |
| stop_ender | any | any | 96 | 0.09-0.68 | 0.18-0.31 |
| chase fallback | any | any | 27 | 0.00 | 0-1.3 |

93% of the fallback landings come from the **retreat branch**: `retreat()` walks off (escape_walk) and then
`cast_at_enemies` lets the HoR dash back onto the enemies it is fleeing, for the flat 250 `min_landing_value`. 468's set
(hurt, under 500) is 0.31 a game and trades ~0.26 HoR deaths for ~0.06 enemy deaths per landing.

**Is it a mirror-only weakness? No (verified, live).** Champion-hitting HoR dashes below 0.6 health
(`hordash_live.py`, die/kill within 4 rounds):

| | share hurt | hurt: HoR dies | hurt: kills |
|---|---|---|---|
| mirror rm2 (gap-csub) | 0.25 | 0.16 | 0.17 |
| live v87 vs Fish / Mite (no 468) | 0.21 / 0.23 | **0.23 / 0.22** | 0.19 / 0.20 |
| live v89 vs Fish / Mite (468) | 0.17 / 0.17 | 0.16 / 0.15 | 0.26 / 0.25 |
| live v95 (nh-6-3) vs Fish / Mite | 0.14 / 0.16 | 0.13 / 0.15 | 0.26 / 0.31 |
| Fish's / Mite's own HoR against us | 0.15 / 0.16 | 0.13 / 0.18 | 0.35 / 0.29 |

Ladder bots punish a hurt landing at least as hard as ocean does (0.23 deaths a landing against 0.16 in the mirror),
and 468 did what it was meant to live (hurt share -25%, deaths after a hurt landing 0.23 -> 0.16). Its expected size is
~0.1 HoR deaths saved a game, about the +0.2 the mirror reads, far below live's resolution (±1.8 points a version).
**Conclusion: 468 does not exploit an ocean-specific habit; it corrects ocean's own retreat-dash habit, which costs as
much or more against Fish and Mite. "Level live" is under-powered, not evidence of overfitting.** Confidence: high on
the mechanism and the live micro-effect, medium on "not overfit" (the live win rate cannot show 0.2 points).

## 467 fight_scale (HoR's passive averaged over the health left, in the fight simulation)

**What it changes in the mirror (verified, paired, gap-csub 2,048 games, arm = rm2 + 467 against rm2).** The arm's own
play barely moves (its HoR dashes -0.05 ±0.19 a game, kills -0.01); the *opponent's* does: rm2's HoR champion dashes
-0.21 ±0.18 a game (hurt ones -0.10 ±0.08), its dash kills -0.06 ±0.06, rm2's kills -0.18 ±0.19 of 4.9. The gain is
the enemy-HoR half of 467: rating the enemy HoR stronger, the arm gives rm2's HoR fewer targets, mostly hurt ones.

**Why ocean's HoR and not Fish's (verified, live).** 467 prices a HoR as if it fights to the death, the passive rising
as it is hit. How much of a HoR's champion damage is actually dealt hurt (`horpas_run.py`, damage-weighted):

| HoR | passive on its champion damage | share dealt below half health | deaths a body |
|---|---|---|---|
| ocean in the mirror (rm1 / ba, ocrm-1920 kept games) | 1.138-1.147 | 0.20-0.23 | 1.3-1.4 |
| ours live, v87-v89 vs Fish / Mite | 1.128-1.142 | 0.17-0.22 | 1.3-1.7 |
| **Fish's** against us | 1.108-1.113 | **0.11-0.13** | 1.5 |
| **Mite's** against us | 1.117-1.118 | **0.12-0.13** | 1.6 |

Ocean's HoR keeps fighting hurt and so delivers the ramp 467 models; Fish's and Mite's disengage earlier and deal under
half as much of their damage hurt, so 467 overprices them and our side backs off fights it would win. Our own HoR fights
hurt as much live as in the mirror, so the own-HoR half of 467 is not mirror-specific; the enemy half is. Enemy HoR is
drafted by Fish and Mite in ~90% of live games (mirror: ~52%), so the overpricing fires often live. Consistent with
v87-fs-enemy (467 for enemy HoRs only) reading +0.56 ±0.25 on dgate's new bodies, which are ocean bodies with ocean's
HoR, and level live. Confidence: medium-high (the passive data is direct; the paired subset is ~2 sigma).

**The weakness 467 exploits: ocean's HoR fights hurt** (the same habit as 468's, seen from the other side). A fix in
rm2 would make ocean's own HoR disengage like Fish's; 468's floor and the arm below are the two forms tried.

## Fix prototype: a landing on enemies is refused where it would be lethal (`variants/gap-fix-landsafe`)

**What.** `Safety::lethal_landing(p, radius)`: `lethal(p)` (credible threats and camps kill us at p before our next
turn, against health and shield) with the visible, stunnable enemies within the landing's radius left out, since the
landing stuns them. `enemy_cast`'s landing filter refuses such tiles (beside `landing_wakes`); the turn's Safety reaches
it through `landing_safety`, set at the top of `decide`. The strike search's own landings are untouched (it prices
danger itself). No constant, no health gate: it is `SlotHit::suicidal`'s rule (no cast whose retaliation kills us)
extended to the danger a landing walks into, which `min_landing_value`'s flat 250 never priced.

**Why it is not 468.** 468 raises the value bar for one champion below one health fraction; this applies the existing
danger model to every landing, at any health. It targets the habit found above (retreat-branch landings back onto the
pursuers), which costs against Fish and Mite too.

**Screen** (release, own drafts, `ocrm-1920`, 40,960 games, against `variants/ocean-ba65375`):

| | Win % (95% CI) | OOF CAND / REF |
|---|---|---|
| rm2 (reference, `gap-rm2-vs-ba-1920`) | 47.63 (47.1-48.1) | 478,862 / 464,863 |
| gap-fix-landsafe | 47.56 (47.1-48.0) | 480,598 / 466,744 (+0.4%) |

Paired against the reference: **-0.07 ±0.17**, 3.0% of games flipped (+593 -623). **Level: no gain.** It changes
fewer games than 468 (5.9%), and the deaths after hurt retreat landings mostly come over the next turns' pursuit, not
from a blow before our next turn, so a one-turn lethality test misses most of them. Not worth carrying; not tried
against non-ocean opponents.

## c1 (strike search capped at 12 nodes and 6 exact queries; rm2 has 24 and 10)

Arm against rm2 on ocrm-1921: **50.32%, paired +0.32 ±0.32**, 16.5% flips; OOF 459,265 against 486,089 (-5.5%).
- **The gain is not the OOF turns (verified).** Split by the mirror game's OOF turns for CAND: 0 OOF +0.28, 1-10
  +0.57, 11-40 -0.15, over 40 +0.20 (no rise with fuel pressure). Games the arm newly wins cut its OOF turns by 0.64,
  games it newly loses by 2.87: the flips do not follow the saved turns. The subset read the same (OOF -5.7%).
- **Nothing mirror-specific found.** Our OOF turns a game are about the same live (11-13 against Fish, 7.5 against Mite)
  as in the mirror (11-12), and the search runs in contact, which is *rarer* in the mirror (below). c1 was never played
  live alone (only inside CHANGES 441's pool, whose leave-one-out on oc-base9 read c1's removal +0.3). The likeliest
  reading is CHANGES 486's: ocean's turns grew (478-483) and the cap now leaves fuel for the later fuel-gated stages of
  the turn, which is not opponent-specific. **Mechanism: not found; no evidence it is an overfit.** Confidence: low.

## 471: cast_cost 40 -> 29.12 and fight_weight 0.688 -> 0.819 (trib_min_bag belongs to the altar notes)

Arms against rm2 on ocrm-1921, paired with the mirror (40,960 each):

| Arm | Paired | Flips | OOF CAND / REF |
|---|---|---|---|
| 471, all three constants | +0.52 ±0.43 | 33.5% | 484,091 / 482,368 |
| 471c, cast_cost only | +0.19 ±0.37 | 21.9% | 484,451 / 486,784 |
| 471w, fight_weight only | -0.16 ±0.36 | 22.4% | 490,516 / 488,509 |

Neither of my two constants reads above noise alone; whatever 471 gains is in trib_min_bag or the interaction.

**cast_cost (hypothesis, supporting data only).** cast_cost stands for what the slot could do in its next 8 rounds. That
is worth less where chances to cast are scarce, and the mirror is where they are scarcest (`contact.py`): our bodies
spend 7.4% of their alive rounds within 4 of an enemy champion in the mirror, against 9.1-9.9% live (311 contact rounds
a game against 372-430). Ocean casts at champions about twice as often per contact round as Fish (9.6-11 against 5.7
per 100) for less damage a cast (~295 against Fish's ~400): ladder bots cast selectively. A lower bar fits the scarce
mirror; live, with more contact, the slot's next 8 rounds are worth more and the extra low-value casts cost them. Live
v90 (soup-k) did cast more (champion casts 40 -> 42 vs Fish, 39 -> 45 vs Mite; 100 games each). The paired subset
could not resolve the arm's extra casts (+0.25 ±0.82 champion casts a game). Confidence: low; not verified.

**fight_weight: mechanism not found.** It moves the emblem mix (gap-csub paired, per game: Power -0.35, Skirmish +0.26,
Durability +0.22, Bruiser +0.38, Jungle -0.12; live v90 the same direction, Bruiser +4), and games run ~10 rounds longer
with more champion damage on both sides, but alone it reads -0.16 ±0.36 on the mirror, so there is no mirror gain to
explain.

## Summary

| Feature | Mirror alone on rm2 | What it exploits / does | Mirror-specific? | Confidence |
|---|---|---|---|---|
| 467 | +0.30 ±0.37 | Prices the enemy HoR as fighting to the death; ocean's HoR does (20-23% of its champion damage below half health, Fish/Mite 11-13%), so it avoids rm2's hurt HoR (rm2 HoR dashes -0.21, kills -0.18 a game) | Yes, the enemy half | medium-high |
| 468 | +0.21 ±0.21 | Stops ocean's own retreat-branch HoR landings back onto pursuers (93% of fallback landings) | No: costs as much or more live (death after a hurt landing 0.23 live vs 0.16 mirror), and 468 cut it live | high (mechanism), medium (not overfit) |
| 471 cast_cost | +0.19 ±0.37 | Lower cast bar fits the mirror's scarce contact (7.4% vs 9-10% live) | Probably | low |
| 471 fight_weight | -0.16 ±0.36 | Emblem mix toward fight stats; no mirror gain | n/a | not found |
| c1 | +0.32 ±0.32 | Cheaper strike search (OOF -5.5%), but gains don't track OOF | No evidence | low / not found |

Fix tried: `gap-fix-landsafe` (lethal landings refused), level (-0.07 ±0.17 against rm2's reference vs ba65375).
