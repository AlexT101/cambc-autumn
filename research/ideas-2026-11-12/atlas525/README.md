# The rest of ATLAS on charybdis 525: fixes 3 and 5, the disarmed press, and ways to pay for them (2026-11-12/13)

Goal: raise the win rate against Fish r8 and keep Mite level by shipping the parts of ATLAS's lethal-model change
that CHANGES 517 left out (fix 3: a stun's follow-up in `lethal()`; fix 5: retreat ranks steps by a one-cast kill
coming back; their merge fixes; the press on a disarmed enemy), made cheap enough to hold at 100k.
Handoff: [HANDOFF-fuel](../../macro-atlas/HANDOFF-fuel.md). Base and REF: `variants/chy-525` (= bots/charybdis 525).

## Port

`patches/atl-pf.diff` is `macro-atlas/patches/remaining-after-517.diff` applied to 525 (two hunks with fuzz, placed
by hand), minus two of its fuel floors that would change shipped behaviour: fix 2's `aim` off under `refine_fuel`
(on 525 `aim_at` also carries the bag focus of CHANGES 525) and fix 4's escape lethal reads off under it (517 ships
fix 4 without a floor). The floors on fixes 3, 5 and the press (`refine_fuel` 40k, `press::min_fuel` 60k) stay.

## Arms (bots/variants, gitignored; diffs in patches/)

| arm | what |
|---|---|
| atl-pf | the whole remaining change, as ATLAS's final bot (press sims, floors) |
| atl-np | fixes 3 and 5 with the merge fixes; the press off (`press::min_fuel` max) |
| atl-ns | pf with a sim-free press: pressed only when the pack's damage over the window covers its health (as ch517-ns) |
| atl-pk | pf whose press sim reads only a fight Safety already played this turn (`known_fight_of`), never a new one |
| atl-pk0 | pk without fixes 3 and 5 (stun follow-up, coming casts and the merge fix's lethal reads off): the press alone |
| atl-pfc, atl-pkc | pf / pk with no press on a turn after one whose fight was cut for fuel (step guard entry, sim or look, prey cut, turn order, or a turn run out): `note_fight_cut`, `fight_cut_round` |

## Results against chy-525

fgate `--pool v4 --fish-body fr8-g25 --mite-body mf-f9`, batches 0-3 (10,240 fresh maps, 81,920 fresh games an
arm; REF cached), own drafts, release. OOF: out-of-fuel turns a game from the runner's counts, CAND / REF, against
fr8-g25 and mf-f9.

| arm | fuel | win% (95% CI), fresh | Fish | Mite | OOF a game, Fish body | OOF a game, Mite body | verdict |
|---|---|---|---|---|---|---|---|
| atl-np | 200k | 50.16 (49.93-50.39) | 50.29 | 50.03 | 0.07 / 0.07 | 0.07 / 0.06 | ZONE at 200k: small |
| atl-pf | 200k | 50.52 (50.12-50.91) | 50.30 | 50.74 | 0.09 / 0.07 | 0.09 / 0.06 | gain exists, mostly Mite |
| atl-pf | 100k | 49.20 (48.72-49.68) | 49.43 | 48.98 | 8.82 / 6.74 | 8.38 / 6.45 | loses |
| atl-np | 100k | 49.80 (49.38-50.23) | 49.65 | 49.96 | 7.26 / 6.74 | 6.94 / 6.45 | level, no gain |
| atl-ns | 100k | 49.58 (49.11-50.04) | 49.46 | 49.69 | 7.62 / 6.74 | 7.37 / 6.45 | level-negative |
| atl-pk | 100k | 49.53 (49.06-49.99) | 49.50 | 49.55 | 7.82 / 6.74 | 7.53 / 6.45 | loses |
| atl-pk0 | 100k | 49.60 (49.15-50.05) | 49.48 | 49.72 | 7.56 / 6.74 | 7.09 / 6.45 | level-negative |
| atl-pfc | 100k | 49.37 (48.89-49.85) | 49.20 | 49.54 | 8.18 / 6.74 | 7.75 / 6.45 | loses |
| atl-pkc | 100k | 49.91 (49.45-50.37) | 50.02 | 49.80 | 7.75 / 6.74 | 7.38 / 6.45 | level; best arm, cannot pass (upper bound < 50.5) |

Livefork from live r8 positions (`fr_forkarms.py`, chy-525 vs CAND against fr8-g25 members 1-4, forks r100-r600,
415 games, 7,652 pairs, real budget): **atl-pf −0.21 ±0.55**, **atl-np −0.41 ±0.44** points. Neither moves the
outcome of live Fish r8 positions.

**Verdict: nothing ships.** On 525 against the r8 and Mite bodies the remaining ATLAS parts are worth about +0.5 at
200k (the press, against Mite; +0.3 against Fish whether the press is in or not) and nothing at 100k. Every way of
paying for them tried here is level or below at 100k.

## What was learnt

- **The prize is smaller on 525 than on 517.** ATLAS measured +1.3 head-to-head at 2x; against the bodies at 200k
  fixes 3 + 5 are +0.16 and the whole change +0.52, of which the Fish side is +0.3 in both. So even a free version
  would be worth about +0.3 against Fish.
- **Fixes 3 and 5 are cheap in release.** 100M bench (`wide`, 52 games): np's mean fuel a turn equals 525's
  (49,071 against 49,159, games differ); its tail is dearer (p99 +2%, max +11%), out-of-fuel turns +8% at 100k. A
  cached `stunner_near` (static stunner mask, per-foe stun distances; identical 52/52 at 100M) saved nothing in
  release (+0.01% fuel): the debug profile's per-call costs (stunner_near 161, lethal +291 a call) are mostly the
  profiling scopes' own host calls. Dropped.
- **The press loses at 100k whatever its own cost.** Debug profile at 100k (1,280 games a bot on batch 0 part p6):
  the press is 1.5M fuel a game, its fight sim 0.85M (80 sims a game, ~1 a turn, so no sharing across recomputes
  pays). Removing the sim (ns), or reading only fights already played (pk), cuts out-of-fuel turns from +30% to
  +14-17% and the loss from −0.80 to −0.45; the press alone without fixes 3 and 5 (pk0) is −0.40. The fights it
  starts cost the fuel: on press turns the step guard is cut at entry 15-19% of the time, and 21% of press turns cut
  a fight step (3% of all turns).
- **Fuel shortage persists across a fight's turns**: a press turn after a cut turn is itself cut 48% of the time,
  16% otherwise. No press on the turn after a cut (pfc, pkc) adds +0.17 (pf) and +0.38 (pk), the right sign both
  times, but pkc only reaches level (49.91, Fish 50.02).
- What would pay is not a cheaper press but fight turns that fit 100k (fightfuel README: everyone at 200k is +1.5).

## Reproducing

- Variants: `./copybot variants/chy-525 variants/atl-pf` then `patch -p1` with `patches/atl-pf.diff` inside it;
  the others are small diffs over atl-pf (or atl-pk).
- Gates: `tools/gate.sh CAND FUEL FIRST N` (fgate v4, fr8-g25 + mf-f9; logs in `logs/`). OOF table: `tools/oof.py
  CAND [fuel200000]`.
- Profile: debug copies with `macro-atlas/fuel-profile/prof_instr.py` (plus key 13 in press()'s sim block),
  `tools/prof.sh BOT` (pool-v4 batch 0 part p6, both bodies), `tools/pp.py` (OOF by phase, shortcuts, scope fuel)
  and `tools/presst.py` (press turns, sims, hits, cuts on press turns).
- Livefork: `tools/lf.sh CAND` (needs CAND's release build in place).
