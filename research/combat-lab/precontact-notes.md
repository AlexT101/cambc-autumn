# Pre-contact behaviour: what sets the terms of a fight (2026-11-09)

Copy: `bots/variants/cl2-pre` (from `variants/cl2-belief` = oc-cl2-base + the heal_if_home belief fix). Reference for
every A/B: `variants/oc-cl2-base`, `--no-test-draft`, suite `maps/suites/merged/cl2-dev`, fast runner, 20,480 games.
Scripts (scratchpad `pre/`): `margins.py` (CS stand margins from the cal rows), `episodes.py` (first contacts from the
cal replays), `fit.py` / `fit4.py` (factor model and stratified tables), `deny.py` / `deny2.py` (big tributes and
their deniers).

## Study (the cal replays: 1,976 debug mirror games of cal-dbg / cal-dbg2 = oc-cl2-base)

**First contact.** Champion a's first round with an opposing champion b within reach(a) + reach(b) (one-turn strike
reach, walk + dash + attack or spell: 2-5; capped at 8), after 10 rounds with no enemy that close. One row a contact,
from a's side (S); b is the nearest such enemy. State at the end of round r-1; outcome over rounds r..r+15 among the
participants (alive within 8 of a or b at r-1), by pick. **Bodies** = their dead minus ours. 172,764 contacts, 87 a
game (44 a side); a death is counted in ~2.1 contact windows, so bodies a game ≈ the sum over contacts / 2.1.
The margin m (cal-notes) is a's first CS stand verdict in r..r+5 (found for 44%).

The margin dominates, as cal-notes said: m ≤ −1.5: +0.18 bodies, ours first 7.5% / theirs 22%; m ≥ 1.5: −0.23,
24% / 4%. Who walked in (closing over 3 rounds) does not matter at a given margin; 87% of contacts begin at first
sight (neither saw the other the round before).

**Factor table.** Effect = bodies over 15 rounds a contact against the stated reference (95% CI from a Poisson
bootstrap over games); "a side-game" = contacts a side a game; residual = the coefficient in a least-squares model with
both margins, numbers, health share, ally distances, readiness, camp damage, holds, tributes, dead counts, spawn
distance, terrain and bags (t in brackets).

| factor (S = our contact champion's side) | contacts a side-game | raw effect | residual (t) | ours controls it pre-contact? |
|---|---|---|---|---|
| **b is tributing a bag of 100+** | 0.42 | **−0.54** (−0.60..−0.49), ours first 43% / theirs 3% | tributing b −0.17 (−15) | **yes: the deny walk** |
| a under camp fire at contact (b not) | 4.1 | −0.055 vs +0.006 none | camp damage to S −0.024 / 100 (−8) | weakly: farming itself |
| a under 50% health | 1.5 | −0.060 vs +0.004 healthy | hpshare +1.0 / unit (+32) | weakly: heal trips (lost before) |
| a cast 2 spells on camps in the 8 rounds before | 1.4 | −0.040 vs +0.002 | ~0 | yes, but small |
| a's stun ready (stunners) | 6 | +0.010-0.019 | rdyS +0.024 (+3) | yes, small |
| a's dash ready / a travel dash in the 8 before | 19 | none; dashers who dashed do +0.03 better | travA −0.015 (−5) | no gain |
| nearest ally 0-1 vs 4-8 | 13 | +0.035 | +0.008 / tile (mixed signs) | cohesion leans lost (46-49%) |
| corridor: 8+ blocked tiles within 2 vs none | 6.8 | −0.031 | −0.0036 / tile (−6) | path choice; ≤0.03 a game |
| a saw b first | 16 | −0.006 (noise) | ~0 | no |
| numbers within 6, −1 / −2 | 7 / 3 | −0.018 / −0.029 | dn6 +0.019 (+7) | packs (lost before) |
| our dead picks minus theirs +1 | 6 | −0.063 | −0.029 a pick (−7) | state |
| a within 5 of its spawn | 4.6 | −0.053 (calibrated stand verdicts there) | homeA +0.0016 / step | state |
| a acts first in the contact round | 2.6 | −0.062 | −0.094 (−12) | cl2-seat's mechanism |
| a carries 100+ | 2.2 | +0.160 (the mirror of row 1) | | |

Everything except row 1 is below 0.1 bodies a game even if fully controlled, or is a farming / cohesion trade the
earlier arms already lost. Row 1 is a behaviour: ocean walks into a big enemy tribute "whatever the risk"
(fight.cc `stop_game_ender`, reached from `channel_to_deny` for 112+ bags and from `game_ender`).

**Big tributes (deny.py, deny2.py).** 2.6 tributes of 100+ a game. With no opposing champion within 4 while it
channels: 83% land. With one (0.98 a game, 1.4 approachers each): 12% land (lock 38%, stun 34%, the carrier's own
cancel 15%); **the approachers die 0.86 an event** (0.62 with no guard within 6, 0.99 with three), the carrier 6%,
bodies +1.10 to the carrier's side. 57% of the deaths to Prism carriers are by the carrier (640-gem bags: +960 Focus).
Per side that is ~0.5 events and ~0.4 deniers dead a game.

**The timing gap.** Cancels of 100+ channels, turns left at the cancel (all analysed replays):
- lock (the timed lock, CHANGES "The timed lock"): median 2 left of 24; 20% at ≤1 left.
- **stun: median 6 left of 36, mean 15.7 left; 58% with 5+ left.**
- the carrier's own cancel: median 26 left (it saw a threat).

A stun cancels the channel and the gems stay carried (rules: tribute), so a stun costs the carrier only the turns it
had run; it restarts. A stun cast at once spends a denier's exposure on a fraction of the channel. The timed lock
fixed exactly this for locks ("placed on our last turn before it lands, it costs the whole channel"); stuns were left
immediate: `stop_game_ender` walks to stun reach and casts on arrival.

## Behaviour v1: the timed stun deny

For `channel_to_deny`'s denies only (never `game_ender`'s: a missed game-ending stop loses the game), holding a ready
stun and no lock plan: keep a stun plan {enemy, its tile, our last turn before its channel lands, as
`last_round_before_channel_ends`}, wait out of the carrier's sight in a band 8-11 steps from the stun tiles (tiles
within the stun's reach-with-walk of the carrier) and out of every visible enemy's reach (lock_plan_wait's band rule),
and walk in when the walk just fits (round + steps + 1 ≥ last). On arrival the existing stop (walk, then cast) runs.
The plan lapses past its round, when the stun will not be ready then, when the carrier is seen not channelling, or
when it dies.

Expected effects:
- First order: each stun deny costs the carrier the whole channel (~36 turns of a 500-gem tribute) instead of
  ~15, for the same one approach; fewer restarts, so fewer approaches a channel and fewer deniers dead a channel.
- Second order, economy: the denier waits up to ~30 rounds off farming, like the lock plan's. Today it stands within
  reach of the altar for the same channel and usually dies (60 rounds dead): waiting out of reach is cheaper.
- Fuel: one Chebyshev field from the stun tiles a plan (the carrier does not move while channelling), cached; the
  band board a plan. A few k fuel on plan turns only.
- The mirror's fixed policy: the carrier cancels on a threat it sees (median 26 left). Our denier now arrives at the
  end, so a cancel then costs it the whole channel too. Its guards still meet the denier at arrival; deaths at arrival
  stay, but there is one arrival a channel instead of several. The carrier's other enemies (our other bodies) are
  unchanged. Risk: an arrival that fails (blocked, killed on the walk, the plan's timing one turn short) lets a channel
  land that today would have been stunned; the one-turn slack and the lock plan's precedent bound it.
- Not built: cl2-seat (turn-order seating), cl2-campfire (camp fire in chases and lures).

**Smoke 1** (512 debug games, maps/gen, against oc-cl2-base): the timed stun fired ~0.15 plans a game. Stun cancels
of big enemy tributes were left 8.5 turns early against 9.3: most stun cancels come from ordinary casts (the strike
search's `stun_worth` already prices a tributer's stun by the turns run), not from the deny walk. Too rare alone.

**Added to v1 before the A/B** (the lockers' side, `lockers.py`): a lock cancels a channel but leaves the carrier
its next turn beside the locker. Lockers of 100+ tributes die within 5 rounds 62% (Prism carriers 77%, 65% by the
carrier itself); with the carrier stunned at the cancel (22 cases) 18% by the carrier.
- `carrier_lethal`: the carrier's strike on its first turn after the channel's end, at 2 (a lock tile), kills us.
- `channel_to_deny` skips a lock-only deny of a lethal carrier.
- `stop_game_ender` (denies only) prefers the timed stun to the lock when the carrier is lethal and the stun is ready.

**Smoke 2** (the same 512 games): approachers dead 0.24 a game against 0.25; lock cancels 76 against 74; DGATE fired
209 turns. The gate changes few decisions because most stops are `game_ender`'s, which v1 leaves alone.
`ender.py` on the cal replays:

| 100+ tributes | a game | approached | approachers dead a game | landed, approached / not | carrier's team won |
|---|---|---|---|---|---|
| game-ending (score + bag ≥ 1000) | 0.70 | 58% | 0.45 | 8% / 82% | 95% |
| not ending | 1.86 | 31% | 0.39 | 15% / 84% | 79% |

The row-1 bodies sit mostly in decided games: a game-ending bag's side wins 95% whether it is stopped or not, and a
non-ending one's 79%. What v1 can still change is the non-ending denies' ~0.2 deaths a side-game, at the cost of
those tributes landing.

## Results

| round | arm | cl2-dev win % (20,480) | OOF | notes |
|---|---|---|---|---|
| 1 | timed stun deny + lethal-carrier gate on lock-only denies + stun over lock for a lethal carrier | **50.3 (49.6-51.0)** | −0.15% | level |

**Round 1, why level** (`deny3.py` on its 1,000 kept release games; per game, the denying side's view):

| denier | enemy 100+ tributes | landed | approached | approachers dead | stun cancels: turns run |
|---|---|---|---|---|---|
| cl2-pre | 1.14 | 63.4% | 37% | **0.23** | 19.3 |
| oc-cl2-base | 1.36 | 54.3% | 43% | 0.39 | 21.8 |

The gate did what it was built for: 0.16 fewer deniers dead a game (above the 0.1 bar). But the tributes it no longer
contests land (+9 points), and the win rate does not move: on this evidence a lethal carrier's lock deny trades a
body for a channel at about par, as EXPERIMENTS' "DENYs of non-winning channels are a coin flip" found. The timed
stun did not lengthen what stun cancels cost (19.3 turns run against 21.8): most stun cancels are ordinary casts.
