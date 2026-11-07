# State-dependent behaviour modes (ocean, 2026-11-07)

The user's idea: adjust aggression, camp choice and risk tolerance by game state. If a lead holds, keep doing what
built it; if it is lost, change behaviour. Results: EXPERIMENTS "State-dependent behaviour model" (level: 50.2% of
61,440 held out). Tools: `state-modes-tools/`.

## Evidence that motivated it

From 270 v82 ladder games, 512 ocean-vs-astraeus and 256 ocean self-play games (`collect.py`, `tables.py`,
`blown.py`, `cross.py`, `power.py`, `fragile.py`, `behind.py`; decoded with extract.mjs):
- **The snowball runs through deaths and farming.** Self-play: each 100 gems of lead adds ~8 more per 100 rounds;
  once gold is in, the gem lead adds nothing. The trailing side dies 2-3x as often (2.0-2.3 against 0.5-0.8 per 100
  rounds), 81-85% of those deaths on its own half.
- **Blown leads go in kills.** From a 150+ peak, lost games shed -350 to -370 gems through kills, and we die 3-4x as
  often as the opponent.
- **Our leads are mostly carried.** At the first +100 to +150, only 19-84 gems of it are tributed; we carry 166-247.
- **The readable state predicts nearly as well as full information.** Held-out log loss: tributed only 0.49 / 0.59 /
  0.61 (ladder / astraeus / self); + carried + item (spent gold) lead 0.38 / 0.48 / 0.50; + hidden unspent gold
  0.375 / 0.474 / 0.489. About 500 gold of items is worth 100 gems.
- **Fragile leads.** Ahead 100-200 gems with an item lead under -150 wins 72% on the ladder (62% self-play), against
  95% (88%) with an item lead of 150+.
- **The kind of deficit matters.** Comeback rate from first trailing by 150+ gems, by gold lead (< -800 / -800..-400 /
  -400..0 / >= 0): ladder 8 / 15 / 38 / 59%, vs astraeus 7 / 15 / 16 / 33%, self-play 0 / 20 / 19 / 25%.

All of this is correlational, so the knobs were randomized.

## Design

- **State** (`model/modes.{h,cc}` in the `oc-mode-*` variants): lead = tributed lead + carried lead + item lead / 5.
  - Carried lead: ours from comms `bag_of`, theirs as last seen within 40 rounds.
  - Items: shards from last-seen max health / Strength / Focus over each type's growth (Ryth's Strength passive and
    Prism's gem Focus taken off), 30 gold a shard.
  - Read every 4th round (~1k fuel a read). Ahead or behind beyond `mode_lead` 100.
- **Draw** (`state_modes` 1): per game, every state x knob cell gets a level in {-1, 0, +1} from a hash of the map
  (W, H, wall count, altar sum) and side. Every body agrees with no comms, and `draws.py` / `mapkeys.mjs` recompute it
  offline. `state_modes` 2 reads a fixed `mode_policy`; 0 is off and bench-identical.
- **Fit** (`fit.py`): win ~ intercept + the mirror side's result (when given) + a dummy per cell level.
  Intent-to-treat: games are compared by the levels they drew, never by whether a state was reached (the even cell's
  knob changes how often we fall behind). Map-clustered sandwich errors.

| Pass | States | Knobs (level -1 / +1) | Logger games | SE a level |
|---|---|---|---|---|
| 1 | even, ahead solid / fragile (item lead sign), behind soft / deep (-300 items) | retreat (pack-zone ratio x1.5 / x0.67, brake_bag 30 / 12, bag_big 160 / 60); recall line ∓0.08; bank (min_bank 40 / 12, chain 36 / 18); gold price x0.7 / x1.4 | 40,960 | 0.6 |
| 2 | even, ahead, behind | fight risk (hit_given_reach x0.5 / x2); kill value (life_value x2 / x0.5); bank (min_bank 50 / 12, chain 40 / 18); shop (shop_gain_scale x0.5 / x2); camp risk (x0.65 / x1.5) | 163,840 | 0.3 |

## What the fits say

- Pass 1 is noise-level (4 of 20 cells past 1.96 SE), and its argmax policy read 49.5% held out.
- Pass 2's effects (win-rate points, against level 0; table in EXPERIMENTS):
  - **Banking:** min_bank 25 is the optimum ahead and even (both moves cost ~1 point ahead). Behind, holding bags to
    50 reads +0.5.
  - **Shopping:** half the shop gain scale reads +0.2 to +0.5 in every state, but moves no measurable shopping in the
    p2 A/B.
  - **Fight boldness and camp risk** do nothing in any state at x2 / x0.5.
- The policy from pass 2 (`oc-mode-p2`) is level held out (50.2%), and +0.7 against astraeus (not significant).

## Reading

Within these knobs the state-dependence is small: the best cells are worth about half a point each. Most of the
"aggression" knobs are flat, which says the bot's fight sims already decide fights well at any lead. The one robust
finding is about banking: hold bags when behind, keep 25 otherwise.

The +5 target would need a different kind of lever. Not tried:
- where the team goes by state: which side's camps, contesting or ceding the middle, home defence when invaded;
- per-opponent effects: every fit is against a mirror, while ladder teams behave differently (they invade more when
  ahead);
- finer states (round, champions alive, altar count) and per-map-type cells.
