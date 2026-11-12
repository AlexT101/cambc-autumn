# Converting the hoard against Fish r8: thirteen arms on charybdis 524, none passes (2026-11-12)

Branch `r8-convert-20261112` (from main b4985e544), worktree `/home/ubuntu/wt/r8-convert`. The reference is
`variants/rc-524`, a frozen copy of bots/charybdis 524 (= `variants/chy-emb6-524`). Every arm is a copy of it under
`bots/variants/rc-*` (gitignored) with its diff in `patches/`.

It builds on the two studies of v118's 345 live games against Fish r8
([v118-fish](../v118-fish/README.md), [v118-fish-b](../v118-fish-b/README.md)) and starts from what neither built:
getting a winning hoard scored.

**Nothing passes.** No arm gains against the Fish r8 body beyond its noise, and the stack that looked best against
the bodies (soft cap + deep altar) loses about 0.65 points head-to-head against charybdis 524. bots/charybdis is
unchanged on this branch.

## 1. Summary

1. **Twelve arms were gated and one more probed; read them as a family.** Each gated arm has an fr8 and an std read,
   six have a fork read and each read prints five splits: more than thirty 95% intervals and some 150 subgroup
   figures. One or two intervals clear of zero, in either direction, are what that many reads give with no effect at
   all. So only held-out reads are taken as estimates (pool v3 batches 26-33 and the fresh head-to-head maps, played
   only by the two arms the screens picked), screens are not pooled into them, and no subgroup is acted on. Two
   patterns that the family size explains: the soft cap's first read (+0.39 ±0.46 against fr8, the best of the first
   five arms) fell to -0.34 on the next two batches and +0.02 ±0.32 over all four; its lean towards multi-site maps
   (+0.19) and away from one-site ones (-0.17) was looked for after the fact, and the arm built on it (`rc-c2m`)
   reads the same as the one without.
2. **Held-out results of the two arms confirmed** (163,840 fresh games a gate read, batches no gate had played;
   head-to-head on fresh ladder-v4 maps):

   | arm | fr8: fr8-g25 / Mt3q | of it, Fish r8 body | std: Flp4 / Mt3q | of it, Flp4 | Mite body | head-to-head against 524 |
   |---|---|---|---|---|---|---|
   | `rc-deep` (a long tribute goes to an altar deep in our half) | +0.04 ±0.07 | +0.07 ±0.10 | +0.04 ±0.06 | +0.06 ±0.08 | +0.02 ±0.09 | 49.9% of 27,200 (49.4-50.5) |
   | `rc-c2` (soft cap at 26 turn ends + deep) | +0.09 ±0.23 | -0.07 ±0.34 | +0.13 ±0.20 | +0.02 ±0.26 | +0.25 ±0.29 | 49.4% of 27,200 (48.8-50.0); again 49.3% of 13,600 (48.4-50.1); together 49.35% of 40,800 (48.9-49.8) |

   - `rc-deep` is level on every read and never negative; its effect, if any, is under a tenth of a point (it changes
     about 1% of games). Not a gain, so not merged.
   - `rc-c2` is level against the bodies and **loses head-to-head**: the first sample's interval touched 50.0, one
     edge case among thirty-odd reads, so it was called neither way until a second, independent sample had been
     played on the unused maps; that one agrees (49.3%). `rc-deep` alone is level there, so the cost is the soft
     cap's (inferred: the soft cap alone was not played head-to-head). The intervals are Wilson's over games; a
     map's two sides are correlated, so they are a little narrow.
3. **The conversion work, measured** (section 3 has the tables behind it):
   - The Tribute emblem idea is already in 524: the carrier owns one in 90%+ of winning bags of 500+ gems.
   - A long channel fails by where it stands: 74% complete with no enemy within 16 at the start against 17-46%
     with any; 100% at an altar 15+ tiles inside our half against 25% at one in the middle. Half of the lock
     cancels come from an enemy that was within 8 tiles when the channel began.
   - Allies banking in parallel (the soft cap) does what it says: winning bags of 700+ gems fall 42% (367 to 214 in
     2,560 probe games), channels of 41-70 turn ends 22% and of 71+ 50%, losses that held a winning bag 125 to 108.
     Against the bodies that is worth nothing measurable (+0.02 ±0.32, +0.05 ±0.29), a tighter cap loses 1.4 points,
     and in a mirror the side with the smaller hoard loses. Prism's hoard deaths barely move (0.131 to 0.127 a Prism
     game on 2,268 Prism games; the first 640 games had read -14%).
   - Answering the lock with bodies does not work: an escort with lock-breaking leaves lock cancels where they were
     (175 against 178), and leaving the channel to fight the canceller halves lock cancels but doubles the channels we
     leave ourselves, and the conversion takes longer.
4. **The other pieces.** The survival stack (camp-fire margin, Health goal with its shop trip, just-in-time banking,
   no guard stand under camp fire) is level on 524 as it was on v118 (+0.01 ±0.59, -0.16 ±0.53). Handing gold-heavy
   captures to better gold users than Prism loses about half a point. Pricing the hoard's risk by position (the
   strongest correlate found: it dies 7 times as often a round on the enemy's half as on ours) loses 6 points locally
   and 9 from live positions.
5. **Live test.** Nothing here earns live quota: section 5.

## 2. How the arms were read

- **fr8 / std**: `tools/fgate.py ARM variants/rc-524 --pool v3 --ci 0` (fixed reads, 100k fuel, release builds, own
  drafts): fr8 is `--fish-body fr8-g25` with the Mite body Mt3q, std is the standard bodies Flp4 and Mt3q. The two
  share the candidate's Mite half. A batch is 2,560 fresh ladder-v3 maps, both sides, both bodies: 10,240 fresh games
  a bot, so "40,960 games" below is two batches of candidate and reference together. Figures are candidate minus
  reference in points with the 95% half-width over map units. Screens are pool v3 batches 16-19 (16-17 were the
  studies' too); the confirmation is batches 26-33, which no gate had played. The reference wins 86% against Flp4, 82%
  against Mt3q and 73% against fr8-g25.
- **probe**: the arm against fr8-g25 on the 320 maps of v3 batch 17's first part (640 games, the gate's seeds), every
  replay kept and extracted; `convstats.py` (winning bags, channels by length and end, Prism's hoard deaths) and
  `altarside.py` (channels by their altar's side). The same 640 games for every arm, so the tables compare directly.
- **fork**: `livefork_rc.py`, study A's `livefork_arms.py` with this programme's builds: 337 live v118 games against
  Fish r8 forked at rounds 300, 450, 600 and 750 with the live engine state, the arm and the reference each taking our
  side against fr8-g25 (two seeds), 2,054 paired continuations, standard error clustered by game.
- **h2h**: `tools/ab.py ARM variants/rc-524 --no-test-draft` on fresh `--mix ladder-v4` maps made for this programme
  (seeds 8260000-8260039, 13,600 maps, played by `rc-c2` and `rc-deep`; 8261000-8261019, 6,800 maps, kept unused and
  then played once by `rc-c2` as its second sample).
- Out-of-fuel turns a game from the fast runner's counts in each run's summary (`oof.py`).

## 3. What the local games say about conversion (reference against fr8-g25, 640 games)

`convstats.py`, `altarside.py`; the Fish r8 body reproduces the live cancel hazard, so these are measurable locally.

- We held a winning bag (score + one bag >= 1,000) in 476 games and converted 447 (93.9%); we won 11 of the 164
  where we never held one. 29 of the 182 losses held a winning bag (live: 21 of 147).
- By the bag when first winning: under 100 gems 229 games, 95.6% converted, 11 rounds to the win (median); 500-700
  gems 99 games, 97.0%, 41 rounds (mean 85); 700+ 82 games, 86.6%, 79 rounds (mean 152).
- **The Tribute emblem is already there.** The carrier owns one in 90-91% of the 500+ bags when they first win and
  71% of the 300-500 ones (the reactive Tribute price, `shop.cc` `reactive_tribute`). "Prism buys the Tribute emblem
  when its channel gets long" is what charybdis 524 does; no arm was built for it.
- Our channels by length: 21-40 turn ends 48.6% completed, 41-70 31.3%, 71+ 6.4% (live: 44%, 24%, 4%). Of the 627
  channels of 41-70: 188 left by us, 178 cancelled by a lock, 65 by a stun.
- **A long channel fails where enemies are, not by its length alone.** Of 1,252 channels of 21+ turn ends:

  | enemies within 16 of the channel at its start | channels | completed |
  |---|---|---|
  | none | 189 | 74% (89% of those up to 40 turn ends) |
  | 1 | 213 | 46% |
  | 2 | 281 | 25% |
  | 3+ | 408 | 17-26% |

  In 331 lock cancels the locker stood a median 8 tiles from us when the channel started (within 8 in 154, dead in
  39), and the lock came a median 13 turn ends in.
- **By the altar's side** (the enemy spawn's distance to the altar minus ours, Chebyshev):

  | maps with 2+ altars | channels of 21+ | completed |
  |---|---|---|
  | altar 15+ on our side | 77 | 100% |
  | altar 5-15 on our side | 100 | 64% |
  | altar within 5 of the middle | 603 | 25% |
  | the same maps' middle altars where a 15+ altar existed | 79 | 39% |
  | one-altar maps | 423 | 26% |

  A quarter of the games (164 of 640) are on maps with an altar 15+ on our side; on 54% every altar is in the middle.
- Prism's hoard: 0.149 deaths with 100+ gems a Prism game (live 0.29), 49 gems a game; we win 10% of the 80 games
  with one. Of 86 such deaths the killer is the body's Vesper in 52, the bag a median 276 gems at round 624, and six
  rounds before it Prism had no ally within 8 in 35 and one in 24, against two or more enemies in 65. Sampled over
  every round it carries 100+ gems off spawn, it dies within 8 rounds 0.13% of the time on our half (59% of that
  time), 0.45% in the middle (33%) and 0.87% on the enemy's half (8%); with one enemy within 8, 1.23% alone and 0.15%
  with three allies within 8.

## 4. The arms

Screens: pool v3 batches 16-17 (40,960 fresh games a read) unless a row says 16-19 (81,920). These picked the two
arms of section 1, so they are not estimates of them. Probe figures are from the same 640 games (reference: 458 won;
82 winning bags of 700+ gems; 41-70 turn channels 31.3% completed; 0.149 hoard deaths and 49 gems lost a Prism game).

| arm | mechanism | fr8 (fr8-g25 / Mt3q) | std (Flp4 / Mt3q) | probe | fork | verdict |
|---|---|---|---|---|---|---|
| `rc-sc50` | soft cap: Prism takes no ally's capture past a 50-turn channel | +0.04 ±0.18 | -0.01 ±0.16 | - | - | inert (0.9% of games differ) |
| `rc-sc26` | the same at 26 turn ends | +0.02 ±0.32 (16-19) | +0.05 ±0.29 (16-19) | 463 won; 700+ bags 48; hoard deaths 0.128, 39 gems | +0.15 ±1.31 | level; smaller hoards |
| `rc-sc13` | the same at 13 | -1.42 ±0.59 | -1.50 ±0.53 | - | - | loses |
| `rc-esc` | escort on maps of several altar sites, guards break the lock | +0.13 ±0.44 | -0.21 ±0.41 | 461 won; channels unchanged (lock cancels 175 against 178) | -0.68 ±1.18 | level, does not move conversion |
| `rc-hunt` | a long winning channel yields to a fight we win | not gated | not gated | 456 won; lock cancels 87 but left by us 389 (188); 300+ bags held 120 rounds to the end (103) | - | worse in the probe, dropped |
| `rc-surv` | cm + phs + jit + ag (the studies' level pieces and the altar-guard stand) | +0.01 ±0.59 | -0.16 ±0.53 | - | +0.24 ±1.49 | level |
| `rc-c1` | sc26 + surv | -0.06 ±0.43 (16-19) | -0.09 ±0.39 (16-19) | - | - | level |
| `rc-gh` | Prism holds a capture alone only where its gems' Focus outweighs the gold's better use | -0.35 ±0.53 | -0.58 ±0.49 | - | - | loses |
| `rc-deep` | a long tribute goes to an altar deep in our half | +0.11 ±0.13 | +0.06 ±0.12 | 455 won; on maps with a deep altar, channels at it 98 (77), 96% completed; elsewhere 30 (79) | +0.19 ±0.36 | level (held out: section 1) |
| `rc-deep2` | the same with a hazard graded by depth | -0.10 ±0.18 | -0.08 ±0.16 | 455 won; channels at 5-15 altars 117 (93), 64% completed | - | no better than deep |
| `rc-hs` | a kept bag works no group where its expected loss a round exceeds our income | -5.73 ±0.83 (one batch) | -6.41 ±0.80 (one batch) | 427 won; hoard deaths 0.120; 73 losses with 300+ unbanked (42) | -9.10 ±2.11 | loses |
| `rc-c2` | sc26 + deep | +0.12 ±0.33 (16-19) | +0.08 ±0.29 (16-19) | - | +0.15 ±1.31 | level against the bodies, loses head-to-head (section 1) |

`rc-c2m` (c2 with the soft cap only on maps with an altar nearer our spawn than theirs; built after the one-site and
multi-site splits above): +0.25 ±0.31 and +0.07 ±0.28 on batches 16-19, where `rc-c2` reads +0.12 ±0.33 and +0.08
±0.29. The condition holds on nearly every map (in the last batch 1,106 paired games differ against 1,290), so it is
the same arm.

Out-of-fuel turns a game against the reference on the same runs (`oof.py`): sc26 5.93 against 6.00, c2 6.10 against
6.20 (193,536 games), deep 6.25 against 6.24 (161,280), esc 6.28 against 6.01, surv 6.10 against 6.01, the rest
within 0.13 below. No failed game, no early loss, no broken or capped draft in any run; no arm touches `draft/`.

### 4.1 Soft cap (`rc-sc50`, `rc-sc26`, `rc-sc13`; `patches/sc26.patch`)

- **Mechanic.** A tribute is a turn end per 10 gems (a third fewer with the Tribute emblem), and a lock on its altar
  or a stun cancels it whole. `hoard_full(gems, fast)` (`economy/capture.cc`) is true once a kept bag's tribute would
  run past `params::hoard_channel`; the carry stops there and the allies keep and bank what they capture: `keeps_bag`
  (so farm's Focus bonus `carried_bonus`), `sole_capture_holder`, `leave_for_prism`, `prism_carries`, and farm's 'Q'
  pick (`economy/farm.cc`). Prism's own captures still add to its bag, and `keeps_gems` is untouched: it never banks
  early (the studies' hard caps, which do, lost 2.8-8.6 points).
- **The constant.** 26 is the length a channel completes half the time at the measured cancel hazard of 2.7% a turn
  end (ln 2 / 0.027 = 25.7; with the emblem 380 gems, without 260). 50 is study B's measured break and binds in
  0.9% of games; 13 was played to see the slope.
- **Probe, 2,560 games** (the 640 and `probe-more.sh`'s 1,920; reference then sc26): won 1,868 and 1,890; winning
  bags converted 93.6% and 94.5%; winning bags of 700+ gems 367 and 214; channels of 41-70 turn ends 3,281 and 2,567,
  of 71+ 772 and 387; losses that held a winning bag 125 and 108; Prism's hoard deaths 0.131 and 0.127 a Prism game,
  46 and 41 gems a game; gems tributed a Prism game by Prism 458 and 425, by allies 466 and 495. `rc-c2` on the 1,920:
  won 1,428 against 1,410.
- **Why it does not pay.** The 29% of games with a 500+ winning bag convert about 93% either way; the cap moves the
  time to the win, which the bodies seldom punish. In a mirror the uncapped Prism has more Focus late.

### 4.2 Escort and the lock answer (`rc-esc`, `rc-hunt`)

- `rc-esc` (`economy/altar_guard.cc`): where the altars are several sites, `escorted_altar` names the altar a
  winning bag's carrier channels at or is nearest (its tile as seen or posted), once its channel is longer than
  `params::tribute_window`; the strongest bodies stand there as on one-site maps (`guard_turn`), fight what comes
  within `altar_leash`, and hit an enemy lock on it. The probe's channel table is the reference's.
- `rc-hunt` (`economy/bank.cc` `continue_tribute`, `carry_bag`): a winning channel with more than `tribute_window`
  turn ends left is cancelled for a fight `prey` says we win, and the bag chases before it banks. Lock cancels of
  41-70 turn channels fall from 178 to 87 and those we leave rise from 188 to 389.
- A lock is placed from 2 tiles as a free action on the turn its carrier arrives, so only a kill or a stun before
  that turn stops it: bodies standing at the altar do not.

### 4.3 Deep altar (`rc-deep`, `rc-deep2`; `patches/deep.patch`)

- **Mechanic.** `deep_altar` (`economy/bank.cc`): the enemy's walk from its spawn to a tribute tile of the altar is
  longer than ours by more than two sight radii (16), so nobody on the line midway between the spawns sees a channel
  there. `long_tribute_altar` sends a tribute longer than `tribute_window` there when the walk (on foot, or home by
  the recall and on) plus one channel takes no longer than the walk to the nearest altar plus the channel's expected
  turn ends there with its restarts, (e^(hL) - 1) / h at `params::channel_hazard` = 0.027: 16 more steps for a
  30-turn channel, 56 for a 50-turn one. `bank_gems` aims at it and starts the tribute only there (`submit_only`),
  `mite_tribute_habit` does not start one elsewhere, `recall_to_bank` prices the trip to it, `carry_bag` does not
  wait at another altar.
- **Probe** (`altarside.py`): on maps with such an altar, channels of 21+ turn ends at it go from 77 to 98 (96%
  completed) and those in the middle from 79 to 30. It touches 4% of long channels, 1% of games.
- `rc-deep2` grades the hazard in a line from 0.027 at the middle to none at depth 16 and takes the altar with the
  fewest expected turn ends. It moves the channels it should (those at altars 5-15 inside our half from 93 to 117,
  64% completed) and reads no better: -0.10 ±0.18, -0.08 ±0.16.

### 4.4 Survival stack (`rc-surv`, `rc-c1`; `patches/cm.patch`, `phs.patch`, `jit.patch`, `ag.patch`)

- cm, phs and jit are the studies' diffs (`v118f-cm`, `v118fb-phs`, `v118fb-jit`), which apply to 524 unchanged.
- ag (`economy/altar_guard.cc` `guard_turn`): a guard's stand under an awake camp's fire is no stand. On
  `01boss-battle` the altar sits beside two Monoliths, every stand tile is in their reach, and the live 974-gem Prism
  died guarding there. Too rare to read alone; it rides in `rc-surv`.

### 4.5 Gold-aware hold (`rc-gh`)

`gold_outweighs` (`economy/capture.cc`): Prism is not a capture's sole holder, and it is not left to Prism, where
an ally on or beside it holds for more (`holder_value` at the holders' gold price) than Prism with the Focus its gems
add (`carried_bonus`). A wolf pays 10 gold a gem, a gem cluster none. It loses 0.35-0.58: the carry is worth more
than the gold's better use, as the spread experiments of 11-08 found for every reweighting.

### 4.6 Hoard side (`rc-hs`)

`economy/farm.cc`: a Prism keeping its gems skips a group where the bag's expected loss a round, `carrier_hazard()`
x our walk home over the enemy's walk there x `params::bag_swing` x the bag, exceeds `gem_income_rate()`. It is the
positional form of the caution the studies ruled out, with no new constant, and it loses the same way: hoard deaths
fall 20% in the probe and the hoard then sits out the race (73 losses with 300+ gems unbanked against 42).


## 5. Verified, inferred, not done, and the live test

**Verified**

| finding | by |
|---|---|
| every figure of section 3 | 640 probe games of the reference against fr8-g25 (replay counts) |
| the soft cap is level against the bodies at 26, inert at 50, loses 1.4 at 13 | fgate, 40,960-81,920 games a read |
| `rc-c2` is level against the bodies on unplayed batches | fgate, 163,840 games a read |
| `rc-c2` loses head-to-head | two independent samples, 27,200 and 13,600 games, 49.4% and 49.3% |
| `rc-deep` is level on every read | fgate 163,840 games a read on unplayed batches; 27,200 head-to-head; 2,054 fork pairs |
| the escort does not change channel completion; hunting the canceller makes conversion slower | probes, the same 640 games |
| the soft cap cuts 700+ winning bags 42% and leaves hoard deaths where they were | 2,560 probe games |
| gold-aware hold and hoard side lose | fgate; hoard side also from live positions (-9.10 ±2.11) |
| no arm raises out-of-fuel turns by more than 5% (the escort, 6.28 against 6.01) | the fast runner's counts in each run |

**Inferred**

- That the head-to-head cost of `rc-c2` is the soft cap's: `rc-deep` alone is level, the soft cap alone was not
  played head-to-head.
- That the soft cap or the deep altar would do more against live Fish than against the body. The body reproduces the
  cancel hazard (so conversion is priced) and under-models the hoard kill, but the soft cap does not lower hoard
  deaths locally either, so there is no local sign of the live benefit it was built for.
- That the altar-guard fix matters: one live game.

**Not done**

- Early cohesion: the body is our own base and does not pack (isolated 19.6% of champion-rounds against its 20.4%,
  outnumbered in contact 13.8% against 15.1%), so nothing local prices it.
- Draft leads (our own Vesper): a lab matter.
- A head-to-head of the soft cap alone, and of the survival stack.

**Live test: none recommended from this work.**

- `rc-deep` is the only arm worth merging on mechanism, and its effect is under 0.1 points: a 500-game live gate
  resolves several points.
- The soft cap has a measured head-to-head cost and no measured benefit.
- The survival stack stands where the studies left it: level locally, its live case is theirs, and this work adds
  only that it is still level on 524.
- What local gates can price: channel completion, conversion time and the cost of any caution (the body cancels
  like Fish). What they cannot: the fed Vesper's kill of the hoard and Fish's pack.

**The rules file.** Nothing in these games contradicts `cambc-rules.yaml`.

## 6. Files

| file | what |
|---|---|
| `patches/*.patch` | each arm's diff against bots/charybdis 524 (`patch -p1` in a `./copybot charybdis variants/NAME` copy) |
| `gate.sh`, `read.sh`, `st.sh` | an fgate read of an arm (fr8 or std, first batch, batches); the pooled read over finished runs; the logs' last lines |
| `h2h.sh` | the head-to-head on this programme's fresh ladder-v4 maps |
| `probe.sh`, `probe-more.sh`, `convstats.py`, `altarside.py` | the 640-game probe against fr8-g25, 1,920 more games of it, and their tables |
| `livefork_rc.py`, `lfbuild.sh` | study A's live-fork run with this programme's builds |
| `oof.py` | out-of-fuel turns a game per arm against the reference on the same runs |
| `env.sh` | the runs' environment (fast runner, the fgate runner library of the primary checkout) |

Working data (not in git): `~/tmp-offload/r8-convert/` (`logs/` gate, probe, head-to-head and live-fork logs; `ext/`
probe extracts; `lf/` live-fork builds and runs; `suites/` the fresh maps). The worktree's `replays/ab/` holds the
gate runs' summaries.
