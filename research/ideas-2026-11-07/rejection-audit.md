# Rejection audit (2026-11-07)

Every rejected, level, null or lost verdict in `research/EXPERIMENTS.md`, `research/ideas-2026-11-05/*`, `research/ideas-2026-11-06/*` (BACKLOG.md included) and `research/ladder-scrims-2026-11-06/*`, reclassified by statistical power. Reruns and decisions are in EXPERIMENTS.md, "(ocean, 2026-11-07) Rejection audit".

**Rule.** The CI is the 95% interval on win rate minus 50 (or the paired delta), in points, with half-width 98/√n unless the source gives one: ±2.74 at 1,280 games, ±0.97 at 10,240, ±0.68 at 20,480, ±0.48 at 40,960.
- **(a) properly decided:** the upper bound is below +0.25 overall, or below a meaningful gain on triggered games for a rare gate (trigger rate × triggered upper bound < +0.25); or a clear loss.
- **(b) underpowered:** the CI includes +0.3 or more overall, or a meaningful triggered gain. This includes SPRT H0s on small samples and rare gates judged on all games.
- **(c) flawed:** a mirror-draft trap, a bug or no-op arm, mismatched drafts, or fuel noise shared by every build.

**Excluded** (rerun elsewhere): the backlog's endgame (items 13 and 7), altar ambush (item 3), Safer Prism, the soup and pool2 members (astport knobs, gemfight obw/ramp/rlag/rint/bls, comeback cbi/cbg2/amb/hop, fuelbud's pooled knobs, spawn spells, area control a1, fixc np/ngd/o05/ne, the proteus seat ledger, kill-dev/fixm soup knobs, gold_price_scale, mapcond_q), and draft7. Also skipped: shipped winners and fuel-exact changes judged on fuel.

**Counts.** The rows below group arms that share a verdict.

| class | ocean-era rows | astraeus-era rows | older groups |
|---|---|---|---|
| (a) properly decided | 47 | 8 | 2 |
| (b) underpowered | 61 | 7 | 2 |
| (c) flawed | 9 | 8 | 1 |
| mixed (a/b/c within the group) | 1 | 6 | 6 |

Counted per individual verdict, the four audit passes found about 166 (a), 282 (b) and 41 (c). That is before removing duplicates: the ideas docs and EXPERIMENTS.md repeat many of the same verdicts.

Most (b) rows are 1-20k-game "level" calls with upper bounds of +0.5 to +1.3 and low priors: they are siblings of shipped or lost arms, or superseded by later rewrites. Rows marked "superseded" are already in ocean in another form, or their code has been rewritten, so rerunning them against their old base cannot change the current bot.

The rerun list is ranked by upper bound × prior, restricted to frozen pairs that still exist and differ only by the idea; it is in the last section.

## Ocean era (2026-11-05 to 2026-11-07)

| idea | variant | base | verdict | n | delta [95% CI] | class | why |
|---|---|---|---|---|---|---|---|
| Tiebreak tb_gold / tb_deny / both (BACKLOG) | oc-bl-tbg/tbd/tb1 | oc-base10 | level | 651; 1,232 fired paired | +0.4 ±3.8; overall about +0.02 | a | fires only in ~0.2% of games (round-2000 ties) |
| Grouping, cooked gate grp2/grpj2/grpj2x | oc-bl-grp2/grpj2/grpj2x | oc-bl-grp | H0 | 4,495/3,491/1,212 | +0.1 ±1.5 / +0.1 ±1.7 / -0.6 ±2.8 | b | small SPRT; but spacing barely moved and the real pack lost |
| Grouping grp1/grp3/grpj1 | oc-bl-grp1/grp3/grpj1 | oc-bl-grp | lost | 1.7-4.5k | -3.9 / -3.6 / -1.3 [-2.8,+0.2] | a | losses |
| Real pack pk3/pk5 | oc-bl-pk3/pk5 | oc-base10 | lost | 20,480 paired | triggered -2.5 / -2.2 | a | triggered CI excludes 0 |
| Capture reset crh / crhb | oc-bl-crh/crhb | oc-bl-cr | H0 | 387 / 600 | -0.1 ±5.0 / -0.3 ±4.0 | b | rare gate (48 of 1,024 team-games), H0 on all games |
| Capture reset crb | oc-bl-crb | oc-bl-cr | H0 | 3,095 | +0.3 ±1.8 | b | small SPRT |
| Capture reset crz | oc-bl-crz | oc-bl-cr | dropped | 8,770 | -0.2 [-1.2,+0.8] | b | upper +0.8; OOF +64% |
| Ward inference wmm/wmi/wmmi | oc-bl-wm* | oc-base10 | level | 20,480 paired | overall upper ≤ +0.11 | a | trigger 0.9-3% caps it |
| carry_w 0.5 / 1 | oc-bl-cw05/cw1 | oc-base10 | level | 20,480 paired | +0.05 / -0.05 ±0.6 | b | overall CI reaches +0.6 |
| carry_w 2 | oc-bl-cw2 | oc-base10 | level | 20,480 paired | -0.48, upper about +0.2 | a | |
| Mirror-pull 04sunburst gate | - | - | dropped | none | - | a | one-map overfit; property gates lost in passes 1-3 |
| Obese bags m<0, round 2 | oc-obese-m* | oc-obese-dev | level | 600 late, paired | 1 flip | a | arms identical game for game |
| Obese V0 ob1/ob1b/ob2b/obb | oc-kill-dev knobs (MISSING) | oc-retest-clean | level | 2,330 late, paired | 0-1 flips | a | dead bags only after the game is decided |
| Obese V1 race m 50/150/300, half | MISSING | oc-retest-clean | H0 | 2.5-4.9k | -0.9..-0.1, ±1.4-1.9 | b | small SPRT, fires in 93% of games |
| Draft-time ambush / hop / both | oc-dg-amb/hop/both | oc-base11 | lost | 20,480 each | -1.0 [-1.7,-0.3] / -2.5 / -2.5 | a | loss |
| combo3 retune vs tuned control (astraeus) | astraeus-combo3-tune | astraeus-ctl-tune | dropped | 20,480 | -2.0 [-2.7,-1.3] | a | loss |
| Retuned astraeus control alone | astraeus-ctl-tune | astraeus-8c0343f | level | 20,480 | +0.3 [-0.4,+1.0] | b | upper +1.0; astraeus only |
| fuel11 f1 / f2 (window floors) | oc-fuel11-f1/f2 | oc-base10 | H0 | 40,052 / 18,795 | +0.15 [-0.34,+0.64] / +0.2 [-0.5,+0.9] | b | base since changed by fuel campaigns 12-13 |
| Pool2 add-one ne, sfc, pk, sl | oc-p2x-* | oc-pool2-1 | M tier | 2,048 each | +1.0 / +0.7 / -1.3 / +0.2, ±2.2 | b | 2,048 games resolve nothing |
| Pool2 add-one p2, g1, sfl, f20, sff | oc-p2x-* | oc-pool2-1 | no-ops | 2,048 | 0.0 | c | fuel gates screened at 2x, where they never fire |
| Pool2 add-one lwar, sfun, cah, amb, hop, rbank | oc-p2x-* | oc-pool2-1 | lost | 2,048 | -0.8..-11.5 | a | consistent with full-size reads |
| pool2-1 / pool2-2 no-kr0h arms | oc-pool2-1-nokr, -2-nokr | oc-base10 | null | 5,120 | +0.3 / +0.1 ±1.37 | c | kr0h's fuel sank the full arms; soup covers members |
| feintfix (astraeus) | astraeus-feintfix | astraeus-9e1fad3 | level | 20,480 | -0.5 [-1.1,+0.2] | a | |
| areaclear (astraeus) | astraeus-areaclear | astraeus-0305953 | lost | 20,480 | -1.7 | a | |
| mapcond2 half shrink | oc-mapcond2 | oc-base9 | not shipped | 20,480 | 0.0 [-0.7,+0.7] | b | quarter arm shipped (pool1t) |
| campdmg2 nearest-champion camp damage | astraeus-campdmg2 | astraeus-0305953 | level | 81,920 (+20,480) | 0.0 [-0.3,+0.4] | b | marginal; upper +0.4 at 100k |
| Fuelbud p1 / p2 / g1 / s1 / f20 / f30 | oc-fb-* | oc-retest-clean | H0 | 4.4-11.3k | -0.3..+0.1, ±0.9-1.5 | b | small SPRTs (p2, g1, s1, f20 compiled out of soup2) |
| Fuelbud a1, g2, r3, ll8, r1b | oc-fb-* | oc-retest-clean | H0 | 2.2-6.1k | -1.7..-0.7, uppers +0.3..+0.75 | b | small SPRTs, all negative |
| Fuelbud w8 / w12 watchdog | oc-fb-w8/w12 | oc-retest-clean | lost | 7,673 pooled | -1.0 [-2.1,+0.15] | a | pooled upper below +0.25 |
| Fuelbud s2, ll4, c1 | oc-fb-s2/ll4/c1 | oc-retest-clean | lost | 608-20,480 | -8.7 / -1.7 / -0.7 | a | |
| nosf (no spawn field turn 1) | MISSING | MISSING | kept final | 20,480 paired | -0.04 [-0.71,+0.62] | b | determinism choice |
| Farm-loop reserve c1 | MISSING | astraeus-5b66bde | not kept | 10,240 | -1.0 [-2.4,+0.4] | b | alternative to shipped rsv2 |
| ptw seats+ledger; cheap_after_heavy 70k/50k | MISSING | oc-retest-clean | below wn | 20,480; 40,960 | -0.5 [-1.2,+0.2]; -0.3 / -0.2 ±0.5 | a | |
| Kill refusal kr0h | MISSING (soup_kr0h) | oc-retest-clean | level | 40,960 | 0.0 ±0.5; fired 4.7% +1.0 | a | triggered upper × rate about +0.15 |
| Kill refusal small 2x SPRTs (kr0, kd0s, kd0h, kf600c, kfp600c, kf600h, rt, fn) | MISSING (oc-kill-dev) | oc-retest-clean | H0 | 200-1,300 | -1.1..+0.2, ±2.7-6.9 | b | seed-0 screens share first games; rare triggers |
| Kill refusal real budget kf600s, kfp600s, kd0s, SPRT stops | MISSING | oc-retest-clean | level | 20,480; ~2.6k | -0.3..-0.2, uppers +0.4-0.5 | c | +5-33% OOF shifts every game; never run in full at 2x |
| Reactive Tribute T3b / T2b | MISSING | oc-retest-clean | level (T1b shipped) | 14,444 / 4,812 | +0.3 [-0.5,+1.1] / -0.2 ±1.4 | b | siblings of the shipped T1b |
| Tribute T1-T3 without floor; Prism forward | MISSING | oc-retest-clean | lost | - | -1.6..-8 | a | |
| Channels C1 strict, C2 all/Prism, C4 30 | MISSING | oc-retest-clean | lost | 20,480 | -1.2..-0.7, upper ≤ 0.0 | a | |
| Channels C1 slack, C2 slack 100, C3 T30, C4 45, C4 Prism cap 450 | MISSING | oc-retest-clean | H0 | 213-923 | ±3-7 | b | tiny SPRTs; full siblings lost |
| Channels C3 T20 switch | MISSING | oc-retest-clean | level | 20,480 | -0.1 [-0.8,+0.6] | b | wait form is a soup member |
| fixm funnel / lockwar | oc-fixm-dev knob / oc-fixm-lockwar | oc-retest-clean | level | 30,720 over 3 budgets | pooled upper +0.1 / +0.06 | a | all budgets negative |
| fixm bankfin3 | oc-fixm-bankfin3 | oc-retest-clean | level | 20,480 | 0.0 [-0.7,+0.7] | b | but paired vs fish_farm -0.21 [-0.40,-0.03]: low prior |
| fixm combo3 | oc-fixm-combo3 | oc-retest-clean | level | 20,480 | -0.3 [-1.0,+0.3] | b | members shipped or in soup |
| fixm combo1; finish_margin, bankfin2, esc, b2-b123 | - | oc-retest-clean | lost | 2-20k | -0.9..-10.5 | a | |
| fixm deny / ender_route alone; esc2 / esc3 | MISSING | oc-retest-clean | H0 / undecided | 2.1-5.1k | -0.9..-0.1, ±1.4-2.1 | b | parts of shipped iw8 |
| fixm race-gated rdeny/resc/rsite/rall/site | MISSING | oc-retest-clean | no-harm H1 | 2.0-2.9k | -0.3..0.0, ±2 | b | no-harm screens, never powered for a gain |
| fixm iw, iw3, iw12, dw, iwg, iw2 | MISSING (deleted) | oc-retest-clean | H0 (iw8 shipped) | small | +0.1..+0.7, ≥±1.7 | b | soup tunes lock_stage_steps |
| fixm i2/i2g/i2a holders, lock_flee | - | oc-retest-clean | level / no-op | paired vs hoard | -0.5..-0.8 | a | |
| Perma-lock dev waves (g1b200, g2s500, gwin, n8b50, ...) | oc-lock-* | oc-retest-clean | ~51 | 3,204 each | +0.5..+1.4 ±1.7 | c | fuel noise shared by every oc-lock build (no-ops read 50.6-51.4) |
| Perma-lock l0 / l1 | oc-lock-l0/l1 | oc-retest-clean | no-op / H0 | 3,204 / 1,314 | +1.3 / -1.4 | c | same shared fuel offset |
| Perma-lock small H0s (g1b100, g3flip, sflip, n8, n12, n8imm, n8stun, n8h2) | oc-lock-* | oc-retest-clean | H0 | 940-2,172 | -2.6..-0.4 | b | small, on a one-site subset with shared noise |
| Perma-lock h1/h1t | oc-lock-h1/h1t | oc-retest-clean | lost | ~620 | -5.7 | a | |
| Perma-lock g2b500 | oc-lock-g2b500 | oc-retest-clean | level finalist | 20,480 | -0.1 [-0.8,+0.5] | b | rare gate (7.7% of games) judged on all games |
| Perma-lock n8l50 | oc-lock-n8l50 | oc-retest-clean | level | 20,480 | -0.3 [-1.0,+0.4] | a | all three budgets negative |
| Perma-lock L4 multi | oc-lock-l4 | oc-retest-clean | H0 | 2,022 | -0.2 ±2.2 | b | tiny SPRT |
| All-hands holds (ah*, a1t10, race, EV, convex), cooked ck* | oc-lock-* | oc-lock-obs2 | lost | 600-3,204 | -1..-33 | a | |
| Late holds a1t15/17/185, h1c2, a1c2, a1ev | oc-lock-* | oc-lock-obs2 | level/lost | 83-1,152 fired, paired | nets -18..+2 | a | normal play already wins 85-93% of fired games |
| Altar cooked guard g1-g5, h3-h6 alone | oc-altar-g*/h* | oc-base1 | level | 1,176 (one-altar maps) | -0.9..+0.9 ±2.9 | b | subset cell; the guard is in shipped e3 |
| Altar permanent guard h1/h2 | oc-altar-h1/h2 | oc-base1 | lost | 1,176 | -6.0 / -17.9 | a | |
| Altar escort e1/e2/e4/e5, e6 | oc-altar-e* | oc-base1 | level | 1,186; e6 10,240 | +0.5 ±2.9; e6 -0.2 ±1.0 | b | subset; superseded by e3 |
| Altar safe_altar s1-s3 | oc-altar-s* | oc-base1 | level | 3,944 | +0.1 ±1.6 | b | rare (9%); superseded by fixm b1 |
| Altar multi guard a1-a3 | oc-altar-a* | oc-base1 | level | 3,944 | -0.5..-0.2 ±1.6 | b | subset |
| e3 sweep kg2/kg4/kl4/kl9/kat900 | oc-altar-k* | oc-altar-k0 | flat | 8,088 (one-altar) | -1.0..+0.3 ±1.5 | b | two-sample on a 23% subset |
| e3 escort_at 800 | oc-altar-kat800 | oc-altar-k0 | lost | 8,088 | -1.7 | a | |
| Never cut the farm loop | oc-fuel-nocut | oc-base1 | level | 5,120 | +0.1 [-1.3,+1.5] | b | diagnostic; OOF 6.5x |
| SPSA oc3 | oc-tuned3 | oc-combo2 | not kept | 40,960 | +0.3 [-0.2,+0.8] | b | superseded by oc4/oc5 |
| Farm-route B1 / all bugs | oc-b1 / oc-b | oc-r0 | lost / level | 15-31k | -1.0 / -0.4 [-0.9,+0.2] | a | |
| Farm-route B2 live_steps fix | oc-b2 | oc-r0 | level, rare | 30,720 | -0.04 [-0.6,+0.5] | b | rare trigger diluted |
| Farm-route B3 via-spawn double count | oc-b3 | oc-r0 | level | 30,720 | -0.2 [-0.8,+0.4] | b | real bug fix; old base |
| R2 kited spare health; R3 heal 0.5 | oc-r2-*, oc-r3-h05 | oc-r0 | level | 30,720 | -0.1 ±0.56 | b | upper about +0.45-0.5 |
| R3 h0/h15/s/s15/s2; R4 recall-out | oc-r3-*, oc-r4-* | oc-r0 / oc-c-r1f1 | lost | 10-31k | -1.7..-0.4, R4 -0.6 [-1.15,-0.03] | a | |
| Bush blind bl0/bl05/bl075 | oc-bush-bl* | oc-base1 | level | 4.6-10.2k | bl0 -0.3 [-1.7,+1.1] | b | the mirror punishes hidden shooters more than ladder bots |
| Bush chase_share / ward_memory / farm_bush | oc-bush-cs*/wm*/fb* | oc-base1 | level | 10-38k pooled | 0.0 ±0.5-0.97 | b | uppers +0.5-1.0 |
| Bush reveal ward rw2 (mode 3 shipped) | oc-combo1-rw2 | oc-combo1 | not kept | 20,480 | +0.4 [-0.3,+1.1] | b | alternative to shipped mode 3 |
| Invade B2 deny 0.5 (d25/d75/dl50) | oc-invade-d50 (d*) | oc-base1 | level | 40,960 pooled | +0.23 [-0.26,+0.71] | b | three suites lean positive |
| Invade deny 1.0 | oc-invade-d100 | oc-base1 | lost | 2,675 | -2.2 | a | |
| Invade B1 whole-team steal; strict gates L0/L1; sunburst | oc-invade-s*, oc-inv2-* | oc-base1 / oc-combo2 | lost | fired sets | -1..-6 fired | a | loses more the more it fires |
| Invade raiders r1m*, r1m8b, L0r/L1r | oc-invade-r1m*, oc-inv2-L*r | oc-base1 / oc-combo2 | level | 5,536 fired | +0.7 ±1.3 fired, about +0.04 overall | a | ≤5% trigger caps it |
| Contest gold-only holds cg | oc-inv2-cg | oc-combo2 | level | 20,480 | +0.1 [-0.6,+0.8] | b | one run |
| Area control a2 / a4 | oc-ac-a2/a4 | oc-combo2 | level | 20,480 | -0.46 / -0.43, upper ≤ +0.25 | a | |
| Area control a3 | oc-ac-a3 | oc-combo2 | level | 20,480 | -0.07 [-0.75,+0.62] | b | |
| Mirror pull ungated u*, gated g*/o*, models | oc-late-* | oc-combo2 | lost | 20,480 each | -0.4..-1.8 | a | best upper +0.3, borderline |
| Mirror pull learned map gate (pass 3) | gate never built (oc-mp-u1) | oc-base3 | no gate | 28,672 subset | subset +0.75 [-0.29,+1.72]; overall +0.15 [-0.06,+0.34] | b | gated bot never A/B'd |
| Spawncamp home bonus k (cached/uncached) | MISSING (oc-sp2-*) | oc-fuel4 | cut | 2.6-5k near maps | k0.1 -1.1 [-2.5,+0.3] | c | the k=0.001 control lost as much: fuel, not the value term |
| Spawncamp home_stands_only | MISSING | oc-fuel4 | lost | 244 | -31.5 | a | |
| value late_mult 0.5 / gps 2.0 | oc-value-M05/gps20 | oc-base1 | level | 10,240 | +0.1 / 0.0 ±0.97 | b | gps since SPSA-tuned |
| value late_mult 2/3, gps 1.0 | oc-value-M2/M3/gps10 | oc-base1 | lost | 2-4.6k | -2.6..-1.1 | a | dose-response |
| value2 price_bought (+gps) | oc-v2-f1* | oc-combo2 | H0 | 8,675 | -0.4 [-1.5,+0.7] | b | |
| value2 ally_gold_weight; value3 alternatives; funnel constants | oc-v2-f2*, oc-v3-*, oc-v2-sf*m | oc-combo2 / oc-base3 | level | 7-20k | -0.6..+0.6 | b | superseded: rewritten by 419-420 |
| value2 3a / 3c | oc-v2-f3a/f3c | oc-combo2 | no-op | ~1k | 0 games change | a | |
| value2 draft_per_gold 0.4 | oc-v2-f3b | oc-combo2 | H0 | 8,838 | 0.0 ±1.0 | b | rare (6 of 128 games change) judged on all |
| value2 lump_power; spread_hold; spread_farm | oc-v2-f4*, sh*, sf* | oc-combo2 | lost | 2-21k | -2.9..-0.6 | a | dose-response / opposite won |
| value2 passive_scaled | oc-v2-f6 | oc-combo2 | H0 | 10,047 | -0.1 [-1.1,+0.9] | b | |
| value3 SPSA type weights | oc-v3-tuned | oc-base3 | undecided | 20,480 | +0.5 [-0.2,+1.2] | b | never confirmed held out |
| Gemfight bag_line_slope / bag_ramp 14p1, 19pm05 / enemy_bag_stand | oc-gemfight-v*, oc-gf3-v2sts1 | oc-combo2 / oc-base3 | lost/level | 20-41k | -2.0..-0.3, uppers ≤ +0.2 | a | |
| Gemfight siblings (obw 4/8, slope caps, ramp 19p05, combos) | oc-gf3-v*, oc-gemfight-v* | oc-combo2 / oc-base3 | level/H0 | 1.8-20k | -2.2..+0.6 | b | slope 1 shipped; rest are its alternatives |
| Fuel r6 K2 horizon 13 / K3 stand 9 / K5 no walk leaf | oc-f6-h13/s9/k5 | oc-fuel4 | H0 | 4.9-8.1k | -0.9..-0.3, uppers +0.5..+0.9 | b | small SPRTs |
| Fuel r6 K2 horizon 9; F1 windows 8/4, 12/4 | oc-f6-h9/f8/f12 | oc-fuel4 | lost | 2.3-3.4k | -1.8..-1.6 | a | |
| Fuel5 L1 lazy stand walkers; fuel campaign 6 r5 | MISSING | oc-fuel4 | -0.73 / 49.6 | 20,480 / 10,240 | -0.73 [-1.41,-0.05] | c | exact changes; trajectory noise, not decisions |
| Retest tw / w16-w24 / e1p1 | oc-rt4-*, oc-rt-e1p1 | oc-tuned4 / oc-base4 | level | 20-41k | tw +0.3 [-0.2,+0.8] | b | superseded by 419-420 |
| loop_reserve (oc-astport) | oc-astport | oc-retest-clean | level | 81,920 | +0.15 [-0.19,+0.49] | b | superseded: in ocean via astraeus after_loop (451) |
| Comeback hunts, race, bold, hops | oc-cb-* | oc-retest-clean | lost | 0.4-20k | -3..0; comeback rate -4.9 | a | +1.6 deaths for +0.5 kills |
| Comeback deny all game | oc-cb-z-deny-all | oc-retest-clean | lost | 8,346 | -0.4 [-1.5,+0.7] | b | |
| Comeback tiers z-tier1/2/3 | oc-cb-z-tier* | oc-retest-clean | not baked | 1.8-6k | +1.4 [-0.9,+3.7] | c | H1s from shared SPRT seed; covered by soup cbi/cbg2 |
| Comeback learned selector | MISSING (oc-cb-log1) | oc-retest-clean | not baked | ~1,100 cooked | ±2.2 | b | logger cannot resolve 1-2 points |
| F92 on draft5 data | oc-draftfeat2 | oc-retest-clean | no gain | 20,480 | -0.1 [-0.8,+0.6] | a | superseded: F92 on draft6 shipped |
| Draft6 C2 x4 shrinkage | oc-draft6-s4 | oc-draft6 | level | 20,480 | -0.1 [-0.8,+0.6] | b | teams differ on 16% of maps: diluted |
| Draft6 LCB; counters | MISSING | oc-base7 | null / not deployed | offline | +0.02 ±0.04 model pts | a / b | |
| mapcond contextual SPSA | tools only | - | not shown | offline | SE 10x the gradients | b | power failure, partly covered by soup mapcond_q |
| fixc banking b1-b4/b6; o1/o15/or1/cm1; n1; all1 | oc-fixc-dev knobs | oc-retest-clean | lost/level | 20,480 | -7.4..-0.4, uppers ≤ +0.3 | a | |
| fixc n2; b7/b8; BT1/BT2 | MISSING (knobs) | oc-retest-clean | level | 20,480 | -0.4..+0.2 ±0.7 | b | alternatives to shipped b5/bt3 |
| fixc ry (Ryth vs Marcella) | MISSING | oc-retest-clean | cannot fire | 20,480 | identical games | c | no-op: Ryth is picked in round 0, before Marcella is seen |
| Teacher farm exposure cutoffs | patch fbb53ca0 | teacher a299d952 | rejected | 20,000 paired | -0.10 [-0.80,+0.60] | b | unlimited-fuel teacher only |
| Teacher retreat bundle | 80219ba6 | HoR teacher | lost | 20,000 paired | -0.24 [-0.43,-0.05] | a | |
| astport2 own/enemy feint | oc-ap2-* | oc-base11 | level | 5-41k | -0.1 [-0.6,+0.4] | b | superseded: ocean now has 439/440 |
| oc-draftfix | oc-draftfix | oc-base14 | not merged | 40,960 | 0.0 [-0.5,+0.5] | a | not rejected on win rate; capped drafts 290 -> 0 |
| ocean_tune3 | bots/ocean_tune3 | astraeus | lost | 80,384 | -4.8 | a | |
| Grouping/kill/channel/lock arms in ladder-scrims docs | (as above) | | | | | | same verdicts as EXPERIMENTS rows; not double-counted |

## Astraeus era (2026-11-02 to 2026-11-05)

| idea | variant | base | verdict | n | delta [95% CI] | class | why |
|---|---|---|---|---|---|---|---|
| Opening gate ca78811f / gate + re-pick 94656606 | astraeus-gate-ca78811 / astraeus-gatefix-9465660 | astraeus-5713135 | not kept (OOF +26%) | 10,240 / 30,720 | +0.8 ±0.97 / +0.2 [-0.4,+0.7]; vs v66 +0.53 (z 1.97) | c | real-budget OOF confound; fewer deaths at equal kills |
| ast-pwc worst-case order | ast-pwc | astraeus-294 | held | ~40,960 | +0.5 [0,+1.0] | c | positive despite +21% OOF |
| ast-kill1b | ast-kill1b | astraeus-294 | level | 20,480 | +0.4 [-0.3,+1.1] | b | |
| ast-wc / ast-pred / ast-safety | ast-* | astraeus-294 | held/dropped | 10-20k | -3.25..0 | c | OOF +14-110% |
| idle-nearearly, deadlast, seat, pred-learn, kill1 | ast-* | astraeus-e9c3797/294 | lost | 10-20k | -5.6..-0.45 | a | |
| Step guard without fight_cost_estimate (sge) | astraeus-sge | astraeus-6c8746a | level | 10,240 | +0.8 [-0.2,+1.7] | b | positive point estimate, OOF +7.9% |
| Fuel gates A1/A2/B1/B2/D1 | astraeus-a1*/a2*/b1/b2/d1 | astraeus-6c8746a / 5b66bde | not shipped | 10-20k | -0.2..+0.1 | b | low prior |
| One safety model ablB / ablC | astraeus-ablB/ablC | astraeus-e73fe3c | left out for fuel | 10,240 | +0.4 / +0.2 ±0.97 | b | rejected on OOF +70%; gates relaxed since |
| One safety model all six; own-ground stand | e73fe3c / MISSING | | level/worse | 10-20k | -0.6..-0.5 | a / b | |
| Unseen step 2 guard stands | astraeus-s12-30ae22e | 33e5cd33 | lost | 80,384 | -0.4 [-0.8,-0.1] | a | |
| Oscillation r1/r2 arms | MISSING | MISSING | lost/level | 2.7-20k | -4.1..+0.2 | a / b | |
| Phase 1-4 wip bundles and losing parts | astraeus-p*-* | prior bundle | lost | 10-40k | -5.3..-1.0 | a | |
| Camp aggro s6/x8 family | aggro-* | astraeus-38aa25c | nothing kept | 52,394 | s6 +0.05 [-0.4,+0.5] | c | code fuel alone -0.23 (null); s6 vs null +0.28 |
| Crystals v1-v5, buyonly / nobuy | crystal-* | astraeus-10b2313 | lost / level | 52,394 | -3.2..0 [-0.4,+0.4] | a / b | nobuy rare (pocket maps) |
| proteus port into astraeus | proteus-f95dce1 | MISSING | dropped | 40,448 | +0.3 [-0.2,+0.8] | c | OOF +45-60%; ptw shipped, ledger in soup |
| Fuel campaign 6 r3 a1/a2/a3, post-strike veto, bf8df313 | MISSING | MISSING | dropped/lost | 10-20k | -1.7..-0.2 | a / c | bf8df313 is exact: trajectory noise |
| Batch 1-7 level arms (woken camps, dash threats, HoR, melee reach, prey, healthy deaths, fled guard, yield gaps, home_race, guard1, chase v1, shields, Monolith, tank order, trip turns, ...) | none frozen | astraeus-8880ba3/702704b/103c9ba/9bba28d/3bfe479 | level | 10,240 each | -0.6..+0.4 ±0.97 | b | no frozen arm; low prior |
| Batch losses (prey filter, camp deaths, chase v2, Focus shop) | none | | lost | 10,240 | -3.5..-0.9 | a | |
| chain-dest / cheap | none | astraeus-3bfe479 | dropped | 10,240 | +0.5 / +0.3 | c | OOF +48% from a stalled-bank bug |
| 283 tributer flag | none | | dropped | 10,240 | -0.1 | c | arm lacked a timing check |
| Dash landings no nearer the enemy | none | | not kept | 10,240 | +0.1 | c | suspected planning bug doubled OOF |
| Chase v1 waived, leave V3/V3d/V3e/press | some frozen | astraeus-5713135 | lost | 10,240 | -5.8..-1.2 | a | V3: fuel bug |
| t5 zone/stand/pair, ward2, leave V1/V2/V4, L1b | none / astraeus-L1b | | level | 10,240 | -0.4..+0.3 | b | |
| Ranged retreat v2 / merged / rs | astraeus-rs | astraeus-290 | level | 10-20k | about -0.3 | b | |
| Cohesion A/B/C arms | coh-* | astraeus-292 | dropped/lost | 10,240 | -3.9..+1.1 | a / b | OOF +7-24% |
| Teleport crystal shortcuts | crystal-* | | lost | | | a | |
| Kite on held stations; shelter fixes | MISSING | | lost | 10,240 | -3.0..0 | a | |
| Gold lean c4, chain_bias; pair-yield arms; pair-notank | MISSING | astraeus-9abbbde | dropped / level / no-op | 2.2-7.3k | -3.5..+0.6 | a / b / c | 500k fuel |
| Fuel gates census arms | astraeus-5b66bde-gv-* | astraeus-5b66bde | diagnostic | - | - | a | |

## Older work (before 2026-11-02): coarse

These bases predate cambc 5.0.0, the macro rewrites and every ocean change; most variants are gone. All are low prior for the current bot.

| group | variants | verdicts | n | class | note |
|---|---|---|---|---|---|
| Hold rule, stack 269-273, fight play-out, reach play-out on fall-first | MISSING | lost / level / held | 1-10k | a / b / c | reach play-out: OOF +15-22% confound, +0.5 ±1.25 (c, med prior, no variant) |
| Strike 4a retreat in search | MISSING | 40.8 real / 52.6 at 100M | ? | c | lost to fuel; anytime search now allowed (no variant) |
| macro-1..5 arms | mostly none; astraeus-95500f7, 532f164 | lost / level | 0.6-10k | a / b | claim arbitration by arrival +0.4 [-1.3,+2.1] (b, med, no variant) |
| macro-5 max_wait 0 vs shipped 3 | astraeus-532f164 | not compared directly | 9,356 | b | ocean uses max_wait 2 |
| demeter gold leans, fuchsia, emblem labs, draft labs 2-4 | MISSING / dl2-* | lost / level | 1-20k | a / b | counter-aware draft lost -1.6 |
| quill, middle band, denial pricing, Willow | quill family, cand-* | level / lost | 10-20k | a / b | |
| Squads, deathballs, packs, raids; ranged retreat v1 | none | lost | ~10k | a | |
| Dash-aware travel | astraeus-dashpath* | level / lost | 10k | b | |
| river, koi, eris, hermes, v36-v61 bundles, Vendetta | MISSING | lost / level | 70-1,700 | a / b / c | eris denial and ambush, Health in builds and the Prism Health term are mirror traps (c); no variants |
| Strategy and economy list, magic numbers, emblems, comms, DRAFT-COMPUTE | MISSING | lost / level | ~1,100 | a / b | ±2.95 at 1,104 games |
| Older bots (aphelios, morgana, nemesis) | MISSING | lost | 240-500 | a | |

## Rerun list

Ranked by upper bound × prior, among pairs whose frozen variant and base both exist and differ only by the idea. All start at 2x fuel, own drafts on both sides (every one of these directories has `test_draft` off), on unused fresh suites 791001-791600 (`maps/suites/merged/audit-p1`). Each common SPRT uses 0.50/0.5025 with its own seed; an H1 goes to a real-budget held-out run on 792001-792080 (`audit-p2a`, 40,960 games). Rare gates are paired against a base-vs-base mirror on the same maps and sides, in 12,800-game chunks (`audit-r1..24`), sequential until the paired CI decides.

| # | idea | pair | method | why chosen |
|---|---|---|---|---|
| 1 | opening gate + re-pick | astraeus-gatefix-9465660 vs astraeus-5713135 | common SPRT, seed 101 | (c) OOF confound; vs v66 +0.53 (z 1.97); fewer deaths |
| 2 | worst-case enemy order | ast-pwc vs astraeus-294 | common, 102 | (c) +0.5 [0,+1.0] despite +21% OOF |
| 3 | step guard without fight cost estimate | astraeus-sge vs astraeus-6c8746a | common, 103 | +0.8 [-0.2,+1.7]; 4-line diff |
| 4 | one safety model ablB | astraeus-ablB vs astraeus-e73fe3c | common, 104 | rejected on fuel only, +0.4 ±0.97 |
| 5 | value3 SPSA type weights | oc-v3-tuned vs oc-base3 | common, 105 | +0.5 [-0.2,+1.2], never confirmed |
| 6 | perma-lock g2b500 | oc-lock-g2b500 vs oc-retest-clean | rare, paired | 7.7% trigger judged on all games |
| 7 | ast-kill1b | ast-kill1b vs astraeus-294 | common, 106 | +0.4 [-0.3,+1.1] |
| 8 | capture reset hold crh | oc-bl-crh vs oc-bl-cr | rare, paired | H0 at 387 games on a ~5% trigger |
| 9 | bush blind 0 | oc-bush-bl0 vs oc-base1 | common, 107 | upper +1.1 |
| 10 | invade deny 0.5 | oc-invade-d50 vs oc-base1 | common, 108 | pooled +0.23 [-0.26,+0.71] |
| 11 | contest gold-only holds | oc-inv2-cg vs oc-combo2 | common, 109 | upper +0.8 |

Not rerun:
- **No frozen variant:** reach play-out, strike 4a, claim arbitration, the eris mirror traps and the pass-3 map gate.
- **Superseded in ocean:** loop_reserve, the astport2 feints, value2/3 rewrites, tw and F92 on draft5.
- **No-op arms that need code, not games:** fixc ry, pool2's 2x fuel-gate screens and value2 3a/3c.
- **Shared fuel-noise lock waves:** low prior, and g2b500 stands in for them.
- **Comp-asymmetric arms:** none with a frozen pair has a prior worth a test_draft run; the mirror-trap ideas (eris denial and ambush, Health in builds) have no variants.

## Decisions (2026-11-07/08)

The full numbers are in EXPERIMENTS.md, "(ocean, 2026-11-07) Rejection audit". The queue grew to 36 pairs: the 11 above plus 25 more (b) rows with frozen pairs.

**Winners at the real budget.** Each reached H1 at 2x and again in a real-budget SPRT on unused maps (793001-793600):
- the opening gate + re-pick: 50.42 of 72k;
- the gate alone: 50.56 of 48k;
- ast-kill1b: 50.78 of 41k;
- area control a3: 50.29 of 112k;
- value3 SPSA type weights: 50.28 of 175k.

**Fuel-bound: positive at 2x only.** pwc, ablB (a loss at the real budget), ablC, bush bl0, invade d50, aggro s6 and campdmg2.

**mapcond half shrink.** It wins against no conditioning, but is level against the shipped quarter.

**H0 or null.** These are now properly decided (a): cg, K5, K2 h13, passive_scaled, late_mult 0.5, B3, fuel11 f1, bankfin3, the astraeus control retune, carry_w 0.5, fuelbud p1, deny-all, bag_ramp 19p0.5, lock L4, grp2, and the rare gates sge, g2b500, d6s4, f3b, B2, R2 and crz.

**Lost.** crh, paired: -0.11 (-0.21..-0.01).
