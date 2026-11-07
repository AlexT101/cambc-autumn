# Endgame race knobs as soup members

These are the `params::bl::es_*` knobs in `bots/variants/oc16-bl-esw`, which is oc-base16 plus the race model
(`model/race.{h,cc}`).

## Off state and identity

- **Off:** `es_on = false`, `es_deny = false`, `es_kill = 0`. This is `variants/oc16-bl-eswoff`. On bench at 100M it
  is identical to oc-base16: replays 16/16 and 52/52, with equal fuel.
- **With the race on and its actions off** (`variants/oc16-bl-esw0`), replays are also identical. The cost is +6 fuel
  a turn, which is the enemy score packed into World's history. Nothing else runs outside the read window.

## Members

| Knob | Type | Range | esw's value | What it does |
|---|---|---|---|---|
| `es_round` | int | 900-1200 | 1000 | the race is read from this round on... |
| `es_score` | int | 400-700 | 500 | ...or once either side has tributed this much |
| `es_k` | float | 75-300 | 150 | read only while the projected margin is within this many rounds |
| `es_gap` | int | 0-600 (0: off) | 400 | skip while tributed plus carried gems differ by more than this |
| `es_deny` | bool | | true | deny a visible enemy tribute of any size when cancelling it flips the projected winner |
| `es_kill` | float | 0-1 | 0.5 | a kill that flips the projected winner is worth this fraction of a whole win's gems |
| `es_bank` | bool | | false | bank now when that alone flips a lost race (it lost at 2x, -0.2: keep off) |
| `es_fuel` | int | 0-80000 (0: off) | 0 | don't read the race on a turn with less fuel left than this |

## Evidence

- **At the real budget on oc-base16** (sequential tests, paired with a base16 mirror):

  | Arm | Games | Result |
  |---|---|---|
  | esw | 20k | -0.18 (CI -0.57..+0.22) |
  | eswd (deny only) | 26k | +0.01 (CI -0.20..+0.23) |
  | eswf (`es_fuel` 60000) | 41k | -0.05 (CI -0.32..+0.21) |

- **At 2x, held out:** deny +6.5 on its triggered games, kill +4.4. Each is about +0.12 overall.
- **The B1 grid of k by w** was flat, within ±0.05 overall.

A soup should therefore expect the race to be level on its own. Its value would be in interactions with other
members. Details are in BACKLOG.md, items 13 and 7.
