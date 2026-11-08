# Big levers: why ocean loses to Fish and Mite, and where a structural change could pay (2026-11-08)

Analysis only; no bot changed. The question: what decides the ~35% of games ocean loses to Intercontinental Fish and
Mite, and which structurally different experiments could be worth +1 point or more after dilution.

**Answer in one line:** the losses are a symmetric snowball with no single in-game pathology that our aggregate
behaviour lacks. They are concentrated on specific maps that Fish and Mite *both* exploit (per-map r = 0.55 between
them), and our local test opponents don't reproduce those maps at all (per-map r = 0.07-0.22). The biggest lever is
the evaluation apparatus. In-bot levers that are supported are map-class fixes judged live. Most "obvious" levers
checked out negative (section 4).

## Data

- **Scrims v86-v89** (oc-base23..27) against Fish and Mite: 2,555 games, 1,762 distinct (deterministic repeats),
  64.9% won. Decoded with `tools/replay/extract.mjs` into `~/tmp-offload/bigl/ana/`; staged by
  `big-levers-tools/stage.py`.
- **Local:**
  - 400 games of oc-base26-td against panel-astraeus-td, and 400 of hor26-b-nohurt against oc-base26 (near mirror),
    decoded in `~/tmp-offload/bigl/local-ana/`.
  - oc-base27 (own draft) against 11 local opponents on the 128 ladder maps, 256 games each (`replays/ab/bigl-ladder-*`;
    the two panel-td runs' summaries were overwritten by same-named runs, and their batches are
    `replays/batch-20261108-1637*-bigl-ladder-*`).
- **Archive:** big-arm's 11-05/06 per-game table (`~/tmp-offload/counter/games.pkl`, 757k games with picks, teams,
  ratings).
- Scripts are in `big-levers-tools/`, intermediate pickles in `~/tmp-offload/bigl/`.

## 1. What a loss looks like

**Gem accounting.** Owned gems = tributed + carried. They change only by captures, kill transfers and camp kills, so the
end gap splits exactly (`feats.py`, `lossmodes.py`). In the 896 losses:

| per lost game | us | them |
|---|---|---|
| owned-gem gap at the end | -594 | |
| from captures | -346 | |
| from kill transfers | -264 | |
| capture gems | 682 | 1028 |
| kills | 4.6 | 11.3 |
| deaths | 15.4 | 7.1 |
| gems carried into deaths | 318 | 202 |
| lifetime gold | 4,315 | 7,420 |

By capture side (`capside.py`), in losses:
- they steal 149 gems from our half (56 in wins);
- they take 246 of the shared groups' gems to our 116;
- they farm 633 on their own half (465 in wins).

The capture gap is map control, the downstream of deaths.

**When it is decided.** The owned gap in losses is -11 at r100, -34 at r200, -111 at r400, -194 at r600 and -272 at
r800. The median last round we led is r348. Win% by the owned gap at r400 runs from 14% (below -200) to 95% (above
+200).
- **First kill:** 77% when we kill first, 53% when they do. They kill first in 51% of games, at a median of r126.
- **Net kills by r150:** -1 gives 56%, +1 gives 81%.

**No asymmetric pathology.**
- **Death contexts are mirror images** (`deaths.py`, `death_tables.py`). In losses our deaths split isolated 4.0, down
  one 3.7, even 2.2 and outnumbered 1.8 a game. Theirs in our wins split 3.2 / 2.9 / 1.9 / 1.1.
- **Early deaths (r ≤ 300) are even:** 2,582 ours against 2,684 theirs, nearly all teamfights.
- **Fight-free openings favour us:** +23 captured gems by r200 (CI ±8) and +38 by r300 (`openings.py`).
- **Opening steals favour us** (`clears.py`): by r150 we clear a 10+ gem group on their half in 30% of games and they
  do it to us in 16%.
- **Clear speeds match** (median 12-16 rounds for Wolf and Elk groups, both sides).

## 2. Where the losses are: maps, and the blind spot

- **Concentrated by map.**
  - 10 maps at ≤ 20% give 20% of all losses: 00lanes 0/20, 04waves 0/20, 00fragment 1/20, 03ultrastarvation,
    04orchard, 00monolith, 00stampede, 02the_pack, 00elkring and 01islands.
  - 8 maps are ≤ 30% against *both* opponents: 00lanes, 03ultrastarvation, 00fragment, 00monolith, 04waves,
    04orchard, 01islands and 00stampede.
  - Of the (map, side, opponent) cells across v86-89, 12% are lost in every version, 35% are won in every version
    and 53% flip.
- **Map features don't explain it.** Spearman |ρ| ≤ 0.30 for every draftlab feature (`mapcorr.py`).
- **It isn't the draft on the worst maps.**
  - On 00fragment our comp is Fish's exactly (Vesper, HoR, C&I) and we lose 10/10. On 03ultrastarvation it is again
    identical (Marcella, HoR, C&I): 0/10.
  - 00fragment's mechanism (`opening.py`): both teams wake their mirrored central group at r5.
    - Our Issac tanks the camp and recalls at 31% health, then our HoR at 40%.
    - Fish's HoR tanks and stays: Fish clears its own group by r29, finishes *ours* at r37, and holds the centre all
      game (captures 944 to our 186).
  - On 00lanes, 01islands, 04orchard and 00monolith there are ≤ 5 kills a game and the loss is a narrow capture race.
    On 00lanes (18 altars, 21 groups a side) we lead to r600, then they out-capture us by ~30 gems every 50 rounds.
- **Local opponents can't see these maps.** Per-map win% of oc-base27 against local bots on the 128 ladder maps,
  against the live per-map win% (`local_vs_live.py` for the panel pair, `scan_corr.py` for the rest):

  | local opponent (256 games) | ocean win | per-map r with live |
  |---|---|---|
  | panel-astraeus-td + panel-proteus-td | 77.7 / 91.4 | **0.07** |
  | astraeus, proteus, demeter, hyperion, v69, v83, river, diana | 54-99 | 0.04-0.22 |
  | all eight pooled (16 games a map) | | 0.22 |
  | bots/fish | 98.4 | -0.08 |
  | *reference:* local half against local half | | 0.26 |
  | *reference:* live Fish against live Mite | | **0.55** |

  - The 9 maps we lose ≥ 75% live, we win 81% locally: 00lanes, 00fragment, 04orchard, 00elkring and 01islands all
    read 100%.
  - The two strongest bots agree on where we're weak. Our opponents agree neither with them nor with each other.
- **The version trend says the same.** Paired by (map, side, opponent) cell (`versions.py`):
  - v86 to v89: **-2.9 points (CI -7.6..+1.8)**, across four merges that were each H1 locally.
  - v83 to v89: -0.2 (-5.7..+4.9).
  - The last real live jump was a mechanic copied from Fish (464 turn order, v85 to v86 +2.0).

## 3. Ranked slate

Ceilings are on the live metric (win% against Fish and Mite). Each needs its own test design, because the local SPRT
can't see the maps where the losses are.

### 1. A live-correlated sparring partner (tool, not bot code; enabling)

- **Evidence:** the table above.
  - Every local opponent's per-map signal is 0.04-0.22 correlated with live, against Fish and Mite's 0.55 with each
    other.
  - Local merges since v86 sum to about -3 live.
  - Without a better judge, every arm below is either live-only (slow, ~500 games a version) or tuned to a proxy that
    can't see the losses.
- **Plan, cheapest first:**
  - (a) ocean playing Fish's and Mite's exact per-map drafts (deterministic, known for all 128 maps x 2 sides from the
    scrims) as the opponent. That isolates the comp part. 00fragment and ultrastarvation say behaviour matters too.
  - (b) A Mite imitation from its own-view data: 450 games, 2.07M turns, priority recovered exactly on 97%
    (`research/mite-2026-11-08`). Start from ocean, swap in Mite's turn order, farm targets and contact rules, and
    measure per-map r after each swap.
  - (c) A learned policy cloned from capture.db replays.
- **Gate before use:** on held-out ladder maps, per-map r with live ≥ 0.4, and it must beat oc-base27 on 00fragment
  and 03ultrastarvation (a proxy that doesn't is not Fish-like).
- **Code:** (a) small, (b) large but outside ocean.
- **Risk:** fidelity may plateau. (a) is cheap enough to try first.
- **Ceiling:** indirect. It is the precondition for turning the 12% of always-lost cells into a locally testable target.

### 2. Live-first map-class fixes on the robust-loss maps (small code per mechanism)

- **Evidence:**
  - 8 maps lost against both opponents at ~10%, 6.25% of games.
  - 12% of cells are lost in all four versions.
  - The mechanisms are visible in the replays (section 2). Three classes:
    - (i) a mirrored contested centre, where our camp tank recalls mid-clear and they finish our group (00fragment);
    - (ii) farm races on many-group, many-altar maps with few kills (00lanes, 01islands, 04orchard, 00monolith);
    - (iii) starvation, decided by kills (03ultrastarvation, 18 gems a side).
- **Arm sketch for (i):**
  - On a group that is contested (enemy crew in sight) and under ~40% of its health, don't let a camp-damaged tank
    recall while an ally can take the aggro.
  - Seat HoR or Marcella first at equal health on clears, Mite's quiet rule, so they take the tie camp hits.
  - The general version is small, but it must be gated: in aggregate our opening steals already beat theirs
    (30% to 16%).
- **Test:**
  - Paired live cells on the 8 maps (32 cells, ~160 games a version; a 10% to 40% shift is unmistakable).
  - Local panel at the non-negative bar (`--sprt 0.4975,0.50`) and `--mix varied` for no regression elsewhere.
  - Don't require a local H1: locally these maps are already won.
- **Ceiling:** +1.9 if the 8 maps reach 40%. Realistically +0.5 to +1.
- **Risk:** each class is a few maps, so prefer rules gated on a measurable map class over map names.

### 3. A per-map plan table for the fixed ladder pool, tuned live (small code; a policy question)

- **Evidence:** the ladder pool is 128 fixed maps, outcomes are deterministic per (map, side, opponent version), and
  the losses repeat across versions.
- **Arm sketch:** a draft-memory table keyed by map hash that switches a few plan knobs on the worst cells (opening
  commit, min_bank, crew size, the draft itself). Choose the values by a live bandit on those cells.
- **Code:** small.
- **Risk:** overfitting by construction. It is worthless on unseen maps, and quota-limited. **Needs the user's call**
  on whether the final evaluation uses this pool.
- **Ceiling:** the same +1 to +2 as idea 2, without the generality.

### 4. Early-window fight policy (medium code; weak evidence)

- **Evidence:**
  - The first kill swings the win rate 24 points (77% against 53%).
  - Net kills by r150 move it from 56% (at -1) to 81% (at +1).
  - The live-gate forensics found 24 of 31 version flips diverging before r100.
  - But early deaths are even in aggregate (2,582 against 2,684), and engage-numbers found copying Fish's engage rule
    at -1.9.
- **Arm:** below ~r250, require a higher local advantage to start a fight (EHP ratio, numbers), since a first death
  compounds.
- **Test:** local screen (the situation is common locally), then live paired.
- **Ceiling:** at most +0.3-0.5, uncertain. **Risk:** engage-numbers and state-modes are close relatives that were
  level.

### 5. Opponent identification as infrastructure only (small code; no arm yet)

- Fish and Mite are identifiable from their drafts and priority encodings.
- Per-map difficulty is mostly shared (r 0.55): 10 maps are bad only against Fish, 5 only against Mite. Kill
  transfers cost more against Fish (-302 against -225 a lost game).
- Mite's priority leaks intent, but weakly (`mite_intent.py`):
  - with its kill-chance code our low champion dies within 3 rounds 33.4% of the time, against 28.8% without;
  - with its retreat code it moves home 45% of the time, against 39%.
- No per-opponent policy is known to be better. Worth building only to serve idea 2's live tuning (a Fish-specific
  and a Mite-specific variant per class).

## 4. Checked and closed (don't launch)

- **Draft like the top teams (VV/Vendetta/HoR/C&I core):**
  - In the archive, among Fish's and Mite's opponents (our games excluded, rating and map controlled), having Prism
    is +0.93 logit. Lacking Vendetta or Vesper doesn't hurt.
  - The draft-change DiD on our scrims, v82 to v83, is -0.9 (CI ±7).
  - On two of the worst maps our comp already mirrors Fish's.
- **Endgame close-out:**
  - We blow 7.2% of our 1,000-owned crossings against Fish's and Mite's 16% (`closeout.py`).
  - Blown close-outs are 4.9% of scrim games and 5% of local games (so locally visible). Their channels and bags
    were exhaustively A/B'd on 11-06 (C1-C4, finish, funnel, escort, lock war, iw8 level live).
  - The new detail: in a blown close-out the race is tight. They need 385 more against 568, our carriers have an
    enemy within 6 for 18 of 80 rounds against 10, and 28% die against 3%.
- **Big bags:**
  - Our 400+ gem tributes complete 26% of the time live, against 30% in the local mirror (`tribsize.py`).
  - Live they are 1.6x as frequent (1.65 a game for 150+ against 0.9 in the mirror, 0.28 against the panel).
  - Long-channel arms were all level (EXPERIMENTS "Kill assignment", "Macro and altar fixes").
- **No self-inflicted lock cancels:** 3 cases in 1,762 games (`lockself.py`). Enemy locks cancel our tributes at an
  average bag of 379.
- **Tribute emblem:** we already buy more than they do (0.23 against 0.09 per champion).
- **Farming speed, opening steals, clear speed:** we are ahead in aggregate (section 1).
