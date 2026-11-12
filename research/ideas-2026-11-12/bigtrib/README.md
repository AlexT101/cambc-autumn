# Fish r8's big tributes: interrupting them delays the bag but does not deny it (2026-11-12)

Lead: Fish r8 banks in fewer, bigger tributes (fishr8 README, section 4). Base `variants/chy-525` (= charybdis 525).

## Live r8: what happens around Fish's 100+ tributes

`btrib.py` (output `btrib-live-r8.txt`) reads 244 live v117/v118 games against Fish r8 (`~/tmp-offload/fishr8/live/ext`).
Fish starts 4.23 tributes of 100+ gems a game (median bag 296, channel 24 turns). Half of Fish's tributed gems come from them.

**Starts that would win the game** (474, 1.9 a game) are the game-ender's job (`game_ender`, `stop_game_ender`):
- 302 are stunned and 66 locked, but Fish starts again, up to 33 times in one game.
- We won 3 of the 56 games where Fish ever had a winning start. Once Fish holds a winning bag, the game is lost anyway.

**Non-winning starts** (558, 2.29 a game; median bag 192, channel 17 turns, r200-800):

| | share | outcome |
|---|---|---|
| scored | 69% | mean 192 gems |
| cancelled: stun / lock / Fish's own | 18% / 5% / 7% | |
| one of ours saw the carrier | 67% | 209 of these scored |
| one of ours with a lock within 8 of the altar | 51% | 156 scored; only 1 was within 2 (lock range) |
| a ready stunner of ours within 8 of the carrier | 51% | 143 scored |
| the carrier died within the channel + 20 rounds | 2% | |
| our death within 10 of the altar | 17% | |

- **Killing the carrier is out of reach.** 64% of carriers are Fish's fed Vesper (median 3.7k health). Our bodies within
  8 could kill the carrier within 60% of the channel in only 50 of 558 starts, and most of those were already cancelled.
- **A delay does not change the result.** Of our losses, 110 of 113 end at 1000 gems, with us at a median 312.
  At our last-300-round rate, we would need about 2,400 more rounds (median). Only 4.5% of losses were within 100 rounds.
  A cancel puts off one bag by tens of rounds, so it cannot change these games.

## Arms (forced, general: they act against every team)

`interrupt_turn` (`economy/altar_guard.cc`, called in `decide` after the chase) walks to stop a visible enemy tribute.
- It needs a bag worth a life (`gem_value` × gems ≥ `life_value`, the bar from CHANGES 525).
- It needs time: we must arrive before the channel lands (`last_round_before_channel_ends`).
- It steps by `step_safely`.
- It does not start while we carry a bag worth a life ourselves.
- With a lock, it goes for the altar's `lock_tiles()`, unless a visible ally with a lock is nearer the altar. The
  turn end's `place_lock` places the lock.

| arm | change | patch |
|---|---|---|
| bt-wl | walk to lock | `bt-wl-chy525.patch` |
| bt-ws | wl, and without a lock, walk into a ready stun's reach (the strike search casts) | `bt-ws-chy525.patch` |
| bt-wlc | wl, and the lock trip outranks a retreat (`want_home`) | `bt-wlc-chy525.patch` |

**Mechanism** (`mech.py`): 256 debug games each on the 128 ladder maps, against fr8-g25 (noise 1).
- wl fires in 90 of 256 games, but an episode lasts a median 2 turns. The next decision is a retreat in 42 of 125
  episodes, since our safety model will not walk us into Fish's altar zone. Locks rise 3.88 → 4.05 a game.
- wlc makes lock cancels of Fish's 100+ bags 0.17 → 0.35 a game.
- ws makes stun cancels 0.60 → 1.04 a game.
- Neither changes Fish's gems by r600 (307.6 base, 306.3 wlc, 305.3 ws), and our deaths stay about the same.
- Fish restarts every cancelled bag, and the restart costs it nothing we can measure.

## Results against chy-525

Livefork from live r8 positions (`fishr8/fr_forkarms.py`; 415 v117/v118 games, forks r200/300/450/600, fr8-g25):
cand − base in points ±SE, clustered by game.

| arm | members 1-2 | members 3-4 | pairs |
|---|---|---|---|
| bt-wl | +0.37 ±0.55 | +0.13 ±0.55 | 2 × 2,996 |
| bt-ws | −0.20 ±0.62 | −0.43 ±0.61 | 2 × 2,996 |
| bt-wlc | +0.03 ±0.70 | −0.63 ±0.65 | 2 × 2,996 |

bt-wl had the best livefork read, so it went to the gate: `fgate --pool v4 --fish-body fr8-g25 --mite-body mf-f9 --fuel 200000`, batches 0-3.

| read | win% (95% CI) | games |
|---|---|---|
| fresh (decides) | 50.04 (49.84-50.23) | 81,920 |
| fresh, Fish | 49.93 (49.66-50.20) | 40,960 |
| fresh, Mite | 50.15 (49.88-50.43) | 40,960 |
| ladder | 49.90 (49.06-50.75) | 4,096 |

LLR high −14.9: the gate rules out a +0.5 gain. Level.

**Verdict: no ship.**
- Interrupting Fish's big tributes, by lock or stun, safe or committed, only delays bags that Fish restarts.
- The carrier is almost never killable.
- Losses to Fish are lopsided, so delays do not convert them.
- Not run at 100k, since there was no 200k gain.
- The TODO item "walk to lock an altar where a visible enemy tributes a big bag" is closed by this.
