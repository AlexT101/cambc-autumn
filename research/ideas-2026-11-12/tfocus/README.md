# A team focus call like Fish r8's: we already converge, and a call does not move it (2026-11-12)

User: "also have we tried stealing the focus call?" Fish r8 broadcasts a shared target in its priority's low bits
(`../fishr8/README.md` section 5). Base: `variants/chy-tfocus-b525` (= bots/charybdis 525, 65f01d3ad).

## Do we converge?

A strike is a unit's damage on enemy champions in a round; its target is the enemy it hit hardest (a linked pair is one
target). A unit's options are the enemies it saw at its turn start within 4 tiles of it. A **choice round** has 2+
strikers and 2+ enemies that are options for at least two of them. A **reachable pair** is two strikers that could each
have hit the other's target. Chance is each striker picking uniformly among its options.

| team (games) | choice rounds a game | all hit one target (chance) | strikes on the round's top target (chance) | reachable pairs on one target | persistence | engagement damage on enemies that died |
|---|---|---|---|---|---|---|
| Fish r8, live (244) | 3.0 | **68.6%** (33.6) | 85.9% (69.3) | **85.7%** | **79.2%** | 38.2% |
| us (v117/v118), live, same games | 2.9 | 53.0% (34.9) | 78.9% (70.0) | 76.4% | 68.3% | 22.5% |
| 525 against fr8-g25 and mf-f9, ladder (512) | 3.1 | 63.3% (33.1) | 83.8% (69.0) | 84.3% | 74.0% | 30.1% |
| the bodies (c520-ps planner) | 2.7-4.1 | 65.9-66.9% | 85.0-85.6% | 84.4-84.5% | 77.1-77.8% | 25.0-25.3% |

Persistence: a team's striking round after one 1-2 rounds earlier, while that round's top target is alive and still an
option: the share that strike it again.

- Fish's hits match its calls: 86% of its strikes in choice rounds go to the round's top target, the same as the share
  of its messages naming the round's target.
- Our planner converges almost as much locally (84% of reachable pairs against Fish's 86%), less live (76%).
- Single units hardly switch. Given a unit strikes again the next round, it strikes the same enemy 93% of the time
  (Fish 94%). It strikes again at all in 51.5% of rounds (`follow.py`).
- When our pairs split, the later striker's target has the same health fraction as the other one (0.76 against
  0.75) and is no closer.

**Does convergence go with kills?** Agreeing rounds were compared with split ones within strata of strikers, shared
options, and allies and enemies within 8. The outcomes are an enemy death and an own death within 3 rounds:

| | enemy death | own death | damage on enemies that die |
|---|---|---|---|
| Fish r8, live | +6.4 pts | −4.2 | +18.7 |
| us, live | +0.1 | −2.4 | −3.6 |
| 525, local | +1.7 | −3.8 | +5.5 |

The effective weights are 135-335 (SE about 2.5-4 points).

**Dilution.** Suppose every split choice round became agreement. That is about 1.1 rounds a game. At our planner's
+1.7 / −3.8 points, it would add 0.02 kills and remove 0.04 deaths a game. That is well under the 50.5% bar.

## The smallest call, built anyway: it does not change convergence

`c1-call.patch` (`variants/chy-tfocus-c1`, +66 lines):
- **Post.** At its turn end, each unit posts the enemy it struck this turn (or last turn), the weakest if it struck
  several. It goes in priority payload bits 8-10, which only members of a complete support pair (Willow and her mate)
  use. Their mates read only each other, and the live round tag stays in bits 14-15.
- **Read.** The strike search prices damage on an enemy that a visible ally calls at the health it will have once that
  ally's next blow lands (`hit_worth` at `h − called`). The blow is `params::focus_follow` (0.5, the measured 51.5%
  follow-through) times the ally's `strike()` at its distance. The price never falls below the plain value. The concave
  `kill_distance` then makes damage on the called enemy, and assists into its kill, worth more.
- **c2** is the same with `focus_follow = 1`, a sensitivity check.

**Mechanism**, 512 ladder games against fr8-g25 and mf-f9 (run-time members, 100k; `ab.py --experiment-config`):

| | 525 | c1 | c2 |
|---|---|---|---|
| choice rounds, all on one target | 63.3% | 63.2% | 63.7% |
| reachable pairs, same target | 84.3% | 84.6% | 84.7% |
| persistence | 74.0% | 73.7% | 73.6% |
| engagement kills | 0.473 | 0.466 | 0.457 |
| kills / deaths a game | 6.40 / 4.24 | 6.54 / 4.37 | |
| kill share at equal numbers | 0.617 | 0.613 | |
| win % against fr8-g25 / mf-f9 (256 each) | 64.8 / 71.9 | 67.2 / 67.2 | 66.0 / 68.0 |
| out-of-fuel turns against fr8-g25 / mf-f9 | 2092 / 1843 | 2393 / 1972 | 2411 / 1923 |

- **The channel works.** In a debug build (`chy-tfocus-c1dbg`), each game has 260 posts and 39 strike-search reads of a
  called enemy.
- **The weight is small.** The median called blow is 5% of the target's health. Under the sqrt, that raises the value
  of damage on it by about 3%. Retaliation, end-tile danger and reach decide the remaining splits, not a near tie.
  Doubling the weight (c2) moves nothing.
- **No gate.** The mechanism did not change, so a gate would only measure noise. A call strong enough to override
  those terms would override the safety pricing, with no evidence that it would pay.

**Verdict.** We already converge. Locally the planner matches Fish's convergence (84% against 86% of reachable pairs).
Agreement does not go with kills for our planner. The smallest principled call leaves convergence unchanged, so we stop.
The live gap (76% against 86%) is opponent-driven: the same planner reads 84% against the bodies. It shows mostly as
lower persistence. The opponent effect is real, but at most about 0.3 points a game is in reach.

## Files

- `conv.py`: per-round convergence, chance levels, stratified outcomes.
- `split.py`: reachable pairs, and what the off-target striker chose.
- `persist.py`: persistence, and engagement damage use.
- `follow.py`: per-unit follow-through.
- `c1-call.patch`: the call, against chy-tfocus-b525.

Live data: `~/tmp-offload/fishr8/live/` (`py conv.py live`). Local extractions are in `~/tmp-offload/tfocus/ext-{base,c1,c2}`.
The ladder run-time config is `~/tmp-offload/tfocus/ladder-cfg.json`. A body without `--experiment-config` and
`FASTRUNNER_LIB=tools/fastengine/runner/target-rt/release/libfastrunner.so` plays broken games (0.4 kills a game).
