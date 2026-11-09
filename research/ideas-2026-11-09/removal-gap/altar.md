# Removal gap: altar and lock features (429 timed lock, 429 deny, 470, 471's trib_min_bag)

Fork of the removal-gap investigation (2026-11-09). Tools are in `tools/` here; extracts of kept replays are in the
scratchpad (`gap/ana-*`). Terms:
- **Mirror:** ocean-rm2 against itself.
- **Arm:** ocean-rm2 plus one removed feature (`bots/variants/gap-ana-<arm>`, analysis only) against ocean-rm2 on
  `merged/ocrm-1921` (40,960 games), paired game by game with the mirror (`tools/flips.py`).
- **Live:** ~4,280 r2 games of v86-v96 against Fish (inte) and Mite (`~/tmp-offload/handoff/gate/analysis`). Every
  version there has 429 in.
- **"Victim":** the team whose tribute channel is cut.

## Arm results (rm2 + feature against rm2, ocrm-1921, paired with the mirror)

| arm | paired (95%) | flips | OOF cand / ref |
|---|---|---|---|
| lock (429's timed lock) | **+0.49 ±0.25** | 8.0% | 491.7k / 492.8k |
| deny (429's channel_to_deny; without the lock plan it stops at once) | -0.20 ±0.36 | 21.2% | 490.2k / 489.7k |
| 470 (no deny lock before round 600) | +0.05 ±0.40 | 30.8% | 486.0k / 486.3k |
| 471 (all three soup-k constants) | +0.52 ±0.43 | 33.5% | 484.1k / 482.4k |
| 471t (trib_min_bag 138 only, `gap-ana-471t`) | +0.22 ±0.26 | 8.6% | 487.7k / 488.7k |

In rm2's context only the timed lock is clearly a mirror gain.

## 429's timed lock

**What fires.** The lock arm's timed cuts (a lock of ours cancels an enemy channel of 50+ gems with ≤2 turns left)
come 0.068 a game, on ~350-gem channels lasting ~26 turns. Prisms are 29 of 67 victims. The mirror's incidental
timed cuts are 0.027 a game, on 80-gem channels.

**The gain is not the timed cut.** I reran 500 of the arm's flip maps with every replay kept (1,000 games, and
reruns match the originals game for game).
- The arm's timed cut fired in:
  - 10% of the up-flips (median 604 gems);
  - 9% of the down-flips (758 gems);
  - 7% of the unchanged games.
- What separates the up-flips is the immediate lock cuts **in the mirror**: 0.82 a game in the up-flips, 0.09 in
  the down-flips, 0.55 in the unchanged games. The arm makes 0.15-0.17 in all three.
- The plan turns rm2's at-once hard stop into a wait that seldom ends in a lock. The gain comes from the locks it
  doesn't place at once.
- Among the 1,000 kept arm games, the 57 with a timed cut read -0.07 paired (+3 -7).

**Why an immediate lock loses against ocean.** I traced `stop_game_ender` with a debug_block line
(`variants/gap-trace-sge`, debug mirror on 512 maps, `tools/sge.py`).
- Episodes run 2.8 a game, and our body dies within 15 rounds in **70%** of them.
  - **Against a channel (0.92 a game, 760-gem bags):** the stop cancels 65% of them. Our body dies 82% of the time,
    and the ender lands within 60 rounds anyway 28% of the time.
  - **Against a walking ender (1.9 a game, ~320 gems):** our body dies 64% of the time, kills the ender only 15%,
    and cuts 8% of them.
- Half of the channel episodes go on after the cut against the now non-channelling ender. Their bodies die 87% of
  the time, every time after the channel ended.
  - The cause is the hard stop's follow-up: "attacks, followed until it stops at an altar, whatever the risk",
    walked into a guarded Prism hoard.
- After an immediate cut the ocean victim breaks the lock within 10 rounds 65% of the time (median 6). It kills our
  locker 77% of the time (`tools/aftercut.py`, mirror T0 EARLY).

**Why ladder bots don't present it.** Live, after our immediate cuts:
- Fish and Mite kill the locker 34-46% of the time and break the lock in a median of 8-10 rounds (38-39% within 10).
- With our timed cuts, the locker dies 29-30% of the time.

On the ender proxy (`tools/enderproxy.py`: an enemy body whose bag wins, seen by ours):
- Mite's walking enders die 30% of the time, against 4-8% for ocean's in the mirror.
- Ocean's game-ending bags are Prism hoards (retaining_gems until winning), 500-800 gems, 50-60 turn channels with a
  guard. Fish's and Mite's big channels are mostly Vesper's, feinted and restarted (`tools/bigtype.py`).

So the at-once lock and chase cost about what they gain against Fish and Mite. Against ocean's guarded hoard they
lose the body. v80's live record (level) agrees.

**Victims behave alike otherwise** (`tools/approach.py`, 100+ channels):
- A lock carrier comes within 5 during 34-40% of channels, in the mirror and live alike.
- Manual cancels within 2 rounds of it: ocean 8-13%, Fish 7%, Mite 26% (Mite feints).
- Ocean stands more guards by the altar: 1.06 within 3, against 0.73-0.80.

**Mechanism (high confidence for the mirror part):** the timed lock exploits rm2's own hard stop more than the
victim's channel. The hard stop sends every body that sees a game-ending bag into reach whatever the risk, and
keeps it attacking the ender after the cut. Against ocean's guarded Prism hoards that trades a body for a lock
broken in ~6 rounds. The plan's wait removes most of those trades.

## 429's channel_to_deny

- Alone (without the lock plan) it stops at once by lock or stun. In the arm it cuts 0.28 non-winning 100+ channels
  a game (mirror 0.06): ~263 gems, 8.5 of ~19 turns run. Our stopper dies within 15 rounds 48% of the time.
- In the kept games with such a cut the arm reads **-0.24 paired (+8 -33)**, and -0.20 ±0.36 overall.
- In ba65375 the deny feeds the timed lock (stop_game_ender sets the lock plan), so its mirror value there is the
  same wait.
- **Mechanism (medium confidence):** the same weakness as above. An immediate interrupt of a guarded ocean channel
  costs the stopper and buys the turns run. Live it was level (fix-macro.md: DENYs a coin flip).

## 470 (no altar-deny lock before round 600)

- In rm2's context it is level on the mirror: +0.05 ±0.40, 31% flips. Its earlier mirror gains (+0.3-0.6) were on
  oc-base25-27.
- The 470 arm against rm2 (`tools/denylock.py`, `tools/altarside.py`):
  - rm2 places 2.5 deny locks a game before round 600.
  - The ocean victim hits 40% of them and breaks 37% within 100 rounds.
  - Its tributes at that altar fall from 35 to 25 gems over the 100 rounds before and after the lock (-28%).
- Live against our early deny locks, Fish and Mite break about as many (37-41%). Their tributes there fall more:
  41 to 21 gems for Fish (-48%) and 52 to 33 for Mite (-37%).
- **Mechanism (medium confidence; it agrees with EXPERIMENTS "Why v90-v93 lose live"):** an early deny lock denies
  what the opponent would have tributed at that altar.
  - Ocean victims, which seldom feint or restart, need that altar less and route round it, so the lock is mostly a
    wasted 10 gold and walk.
  - Fish and Mite cluster tributes at contested altars, so it denies twice as much live.
- 470 exploits nothing in rm2. rm2's early locks are neutral on the mirror and pay live, so there is nothing to fix.

## 471's trib_min_bag (100 -> 138)

- It moves the reactive Tribute emblem from bags of 100-137 to 138+ (`tools/tribshop.py`):
  - Tribute buyers at 100-137 fall from 0.21 a game to 0.01, and at 138+ rise from 0.51 to 0.64.
  - Total buyers are unchanged (~1.5 a game).
- The debug mirror's KTRIB trace first picks Tribute at 100-137 in 782 of 1,412 cases.
- Our 100-137 channels are seldom interrupted anyway (`tools/midchan.py`): 90% finish in the mirror, 94% against
  Fish and 85% against Mite. So a 3-4 turn cut buys little anywhere.
- +0.22 ±0.26 alone (n.s.). **Mechanism: not found.** If it is real, the likeliest reading is the 150 gold a mid-game
  Tribute emblem diverts from fight stats, which matters more in an ocean-vs-ocean fight economy. Untested.

## Fix: `bots/variants/gap-fix-ender`

**The change.** stop_game_ender's forced branch, and continue_recall's cancel for it, now need a **hard stop** for
the ender: a channel under way, and either a stun ready for our next turn or a lock for its altar (the `hard`
predicate stop_game_ender already used, as `holds_hard_stop`). A walking ender, or a channel we can only damage, goes
through the ordinary priced play (strike search, prey and chase pricing, cbdp's cooked snipe). stop_game_ender takes
over once the ender channels.

**Why it is principled.** "Whatever the risk" pays only when the action decides the game before the channel lands.
For a walking carrier nothing lands yet, and a body that dies chasing it can't stop the channel later. This is ocean's
own fight model deciding, with no constants and no special cases. It does not wait, stage or time locks, and it adds
no deny. Immediate hard stops on channels are unchanged. Against carriers that are vulnerable (Mite's walking
enders die 30%), the priced chase should still engage. That is the live risk to watch.

Screen against ocean-ba65375 on ocrm-1920 (reference: rm2 47.6%, 47.1-48.1, of 40,960, OOF 478.9k / 464.9k):
- **47.8% (47.3-48.3) of 40,960.** Paired against rm2's reference on the same games: **+0.20 ±0.20** (4.3% flips,
  +921 -841). Borderline: the CI touches 0.
- OOF turns: cand 489.2k against rm2's 478.9k on the same suite (+2.1%). A body that skips the forced branch runs
  the whole turn. Ref 468.6k against 464.9k.
- Mechanism check (debug mirror of the fix on the same 512 maps, `variants/gap-trace-fixender`, ender proxy):
  - Our deaths within 15 rounds of seeing a walking ender fall from 34% to 15%, and of a channelling one from 52%
    to 39%.
  - Forced episodes are channel-only; their deaths fall from 82% to 57%.
  - Enders land within 60 rounds no more often (walking 26% -> 22%, channel 54% -> 46%).
  - Kills of walking enders fall slightly (8% -> 5%).
- **Not tested:** against rm2 or non-ocean bots on held-out maps, and live. Its live risk is the walking enders the
  forced chase did kill (Mite's die 30% on the proxy).
