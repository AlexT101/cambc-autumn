# Removal gap: what the removed features exploit, and fixes in post-removal ocean (2026-11-09)

Question: the features removed in CHANGES 485-486 win the mirror against post-removal ocean (`variants/ocean-rm2`)
but not live. What do they exploit in ocean's own play, why don't ladder bots offer it, and can rm2 be fixed so it
doesn't have the weakness (without reintroducing, porting or re-tuning the removals)?

Cluster notes: [altar.md](altar.md) (429 lock and deny, 470, trib_min_bag), [carrier.md](carrier.md) (b1, gf, b5, b3w),
[combat.md](combat.md) (467, 468, cast_cost, fight_weight, c1). Scripts: `tools/`. All A/Bs 40,960 games, release, own
drafts, fast runner; "paired" = per-map paired difference against a reference batch on the same maps (`tools/flips.py`).

## 1. Each feature alone on ocean-rm2

Arms are ocean-rm2 plus one removed feature (`variants/gap-ana-<arm>`, hunks from `tools/split.py`), against ocean-rm2
on ocrm-1921, paired with rm2's mirror (50.00%).

| Arm | Paired | Flips | OOF cand / ref |
|---|---|---|---|
| 429 timed lock | **+0.49 ±0.25** | 8.0% | 491.7k / 492.8k |
| 471 (all three constants) | +0.52 ±0.43 | 33.5% | 484.1k / 482.4k |
| 471 trib_min_bag only | +0.22 ±0.26 | 8.6% | |
| 471 cast_cost only | +0.19 ±0.37 | 21.9% | |
| 471 fight_weight only | -0.16 ±0.36 | 22.4% | |
| c1 | +0.32 ±0.32 | 16.5% | 459k / 486k (-5.5%) |
| gf | +0.31 ±0.41 | 30.5% | |
| 467 | +0.30 ±0.37 | 24.9% | |
| 468 | +0.21 ±0.21 | 5.9% | |
| b5 | +0.17 ±0.17 | 3.5% | |
| 470 | +0.05 ±0.40 | 30.8% | |
| b3w | +0.04 ±0.11 | 1.4% | |
| b1 | -0.04 ±0.10 | 1.2% | |
| 429 deny (without the lock plan) | -0.20 ±0.36 | 21.2% | |

The arms sum to +2.2; all of them together read 52.2% (51.7-52.7): they add up.

Held-out suite `gap-1930` (1930000-1930079, ladder-v2): ocean-rm2 vs ocean-ba65375 48.2% (47.8-48.7), OOF 489k / 475k.
Against astraeus rm2 65.6% vs ba65375 68.0%; against proteus 76.5% vs 78.7%. The removed features gain about as much
against those ocean-family bots as on the mirror, so this panel can't separate "exploits ocean" from "really better".
`bots/fish` is no panel (rm2 beats it 97.1%).

## 2. Mechanisms

**Verified, high confidence: the stop-the-ender weakness (429 lock, 429 deny, b3w).** Found independently by two
analyses. `stop_game_ender` runs ahead of every branch, with the step guard off and a forced travel dash, and after a
cut keeps attacking the ender "until it stops at an altar". In debug mirrors rm2's body dies within 15 rounds in 70%
of episodes: 82% against a channelling ender (bags ~760), 64% against a walking ender, which it kills only 15% of the
time. Ocean's game-ending bags are guarded Prism hoards (500-800 gems, 50-60-turn channels, more guards by the altar);
after an immediate lock the ocean victim breaks it in a median 6 rounds and kills the locker 77% of the time. Live,
Fish and Mite kill our immediate lockers only 34-46% of the time; Mite's walking enders die 30% (replay proxy) against
4-8% for ocean's; on multi-site maps ocean bodies die near enemy winning carriers 2-4x as often as Fish's or Mite's do
near ours.
- 429 timed lock: the gain is from not making rm2's immediate hard stop, not from the late cut. On 500 rerun flip
  maps the timed cut fires in 10% of up-flips and 9% of down-flips; what separates them is the mirror's immediate
  lock cuts (0.82 a game in up-flips, 0.09 in down-flips).
- 429 deny (medium): the same weakness; without the plan it stops 100+ channels at once and the stopper dies 48%.
- b3w: its escorts kill the stoppers this habit sends (61% within 10 rounds, escort dying 4%); it moves almost no
  results on rm2 because those stoppers mostly die anyway.
- Why ladder bots don't present it: they rarely build guarded single-tribute hoards (their 300+ bags come from kills
  and Monoliths; they feint and restart tributes), and they kill stoppers less.

**467 (medium-high; data verified, the ladder cost is a hypothesis).** It prices a Heart of Ruin as fighting to the
death. Ocean's does (20-23% of its champion damage below half health); Fish's and Mite's 11-13%, so 467 overprices
them, and they draft HoR in ~90% of live games (mirror ~52%). In the arm rm2's HoR makes 0.21 fewer champion dashes a
game and rm2 0.18 fewer kills.

**468 (high): not a mirror exploit.** 93% of the landings it gates are retreat-branch dashes back onto our chasers;
hurt and under 500 value, the HoR dies within 4 rounds 26% of the time. Live the habit costs more (deaths after a hurt
landing 0.23 against Fish/Mite, 0.16 mirror). 468 worked live (v89: hurt landings 0.21 -> 0.17, deaths after them
0.23 -> 0.16); its ~0.2 points are below a live version's resolution (±1.8).

**470 (medium): level on rm2, nothing to fix.** rm2's early deny locks cut ocean victims' tributes at that altar by
28%, Fish's and Mite's by 37-48% (they cluster tributes at contested altars).

**gf (hypothesis, low-medium).** Boosts our health +30% in almost every carrier chase; rm2 loses 0.58 ±0.34 more bodies
a game. Fish's carriers punish marginal chases (target killed 0.076, chaser dies 0.086), ocean's don't (0.10 / 0.069).
Doesn't explain Mite, whose numbers look like ocean's.

**cast_cost (hypothesis, low).** Contact is scarcer in the mirror (7.4% of alive rounds within 4 tiles; 9-10% live),
so a lower cast bar pays there. Not verified.

**No mechanism found:** fight_weight (-0.16 alone); trib_min_bag (those channels finish 85-94% everywhere); b5 (the
mirror presses big carriers less than live does); b1 (no effect on rm2); c1 (its gain doesn't rise with fuel pressure,
and live fuel pressure is similar; likely not opponent-specific).

**Context (verified): ocean hoards far more than ladder bots.** Champion-rounds a game carrying 150+: ocean mirror 229,
Fish 124, Mite 77; 300+ tributes completed a game 0.33 against ~0.08. 62-76% of ocean's 300+ bags come from captures.

## 3. Fixes on ocean-rm2 (no new constants)

Final A/Bs on `gap-1930`; paired against rm2's own batch on the same games (rm2 vs ba65375 48.24%, rm2 vs astraeus
65.58%). Screens on ocrm-1920/1921.

| Fix | Screen (paired vs rm2) | vs ba65375 | paired vs rm2 | vs rm2 | vs astraeus (paired) | OOF vs ba65375 |
|---|---|---|---|---|---|---|
| `gap-fix-ender` | +0.20 ±0.20 | 48.4% (47.9-48.9) | +0.18 ±0.20, 4.5% flips | 50.2% (49.8-50.7) | +0.07 ±0.20 | 498.4k / 479.4k (rm2 489.4k: +1.8%) |
| `gap-fix-sgeguard2` | +0.46 ±0.42 | 48.4% (48.0-48.9) | +0.21 ±0.43, 19% flips | 50.4% (49.9-50.9) | +0.15 ±0.38 | 490.5k / 480.0k |
| `gap-fix-sgecomb` | | 48.4% (47.9-48.9) | +0.18 ±0.44 | 50.2% (49.8-50.7) | +0.15 ±0.40 | 490.8k / 479.3k |
| `gap-fix-landsafe` | -0.07 ±0.17 (OOF +0.4%) | not run (level on its screen) | | | | |

Pooled over screen and final: ender ~+0.19 ±0.14 against ba65375; sgeguard2 ~50.45 ±0.33 head to head against rm2
(50.5% on ocrm-1921, 50.4% on gap-1930). None significant on the held-out suite alone; none loses against astraeus.
- **gap-fix-ender:** the forced stop branch (and continue_recall's cancel for it) runs only when we hold a hard stop on
  a channel under way: a stun ready for our next turn, or a lock for its altar. A walking ender, or a channel we can
  only damage, goes through ocean's normal priced fight play. Traced: deaths near walking enders 34% -> 15%, near
  channels 52% -> 39%; enders land no more often.
- **gap-fix-sgeguard2:** `ender_spares_a_turn`: while a turn's delay still lets us stop a walking ender before its walk
  plus whole channel ends (`carrier_tribute`'s timing), a body that `want_home` would send home retreats; otherwise the
  stop keeps the step guard and no forced dash. Traced: deaths on spared walking turns 16.7% -> 0.7%.
- **gap-fix-sgecomb:** sgeguard2 plus ender's rule for channels; no better than either.
- **gap-fix-landsafe:** refuses a HoR landing where `lethal()` holds (not counting enemies the landing stuns). Level:
  the deaths come from pursuit over later turns, which a one-turn check misses.

## 4. Next

1. Read gap-fix-ender live or on dgate's new bodies (Fish's lock habits, Mite's tribute habits): the narrowest change
   (4.5% flips), ~+0.19 on two suites. Risk: giving up kills of vulnerable walking enders such as Mite's.
2. The root of the stop weakness is ocean's guarded single-tribute Prism hoards. Not prototyped: a tribute-safety model
   counting whether a lock carrier can reach the altar before the channel lands.
3. HoR: a multi-turn pursuit check on retreat landings, rather than landsafe's one-turn check.
4. Much of the remaining gap is likely features that are simply good rather than exploits (468, c1, probably 471's
   constants); their live reads were too small to show 0.2-0.5 points.

Files: analysis variants `gap-ana-*` (`gap-ana-471t/471c/471w` one-constant 471 arms), `gap-trace-*`, `gap-trc-*`,
`gap-dbg-hor`; rerun suites (subsets of ocrm-1920/1921) `merged/gap-car-2k`, `gap-csub`, `gap-c468flip`, `gap-alt-*`;
reports `replays/ab/gap-*`, `replays/ab/gapF-*`. Uncommitted; `gap-1930` added to maps/SUITES.md.

Outcome: gap-fix-ender shipped as CHANGES 489 (with the matching continue_tribute cancel as 490), merged to main in 16d6f7803.
