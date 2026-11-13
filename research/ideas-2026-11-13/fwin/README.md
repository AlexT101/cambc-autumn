# Why games against Fish r8 are won (2026-11-13, base chy-525)

Question (user, via the coordinator): what do winners against Fish r8 do differently from losers on the same maps
(economy, Vesper's gold, timings, fights, draft), and could our bot do it in general, not per map? Also the user's
"will training the bot to match the book generalise outside of ladder maps?"

**Verdict: no clear mechanism that carries to fresh maps.** No team beats r8 more often than we do on the same cells.
Every team's wins part from its losses only after the first fights. The one cross-team regularity is in the draft
(Vesper against r8), and banning her loses against the local bodies.

## Data

- **Game table.** big-arm capture.db, every platform game since 11-12 14:00: 5,083 Fish r8 games (4,778 unranked, 305
  ranked). A cell is a (map, Fish's side) pair; Fish's team depends only on the map, and Fish plays deterministically
  until the first interaction.
- **Our games.** 755 traced r8 games: v117 345, v118 345, v119 65.
- **Other teams' games.** 444 downloaded, one every 20 s. 422 are r8 by the priority-mask signature (`r8sig` ≥ 0.9):
  Mite 185, BattleCats 112, others 125.
- **Features.** Extracted with `tools/replay/extract.mjs`; `feat.py` computes them per game.

## 1. No team beats r8 more often on the same cells

The table compares each team with us on the cells both played. "corr" is the per-cell correlation between their win
rate and ours. These win rates come from the game table, so they don't depend on which replays were downloaded.

| team | games | overall | shared cells | us | them | them − us |  corr |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mite | 1,129 | 41.9% | 250 | 54.4% | 48.6% | −5.8 ±3.7 | 0.15 |
| BattleCats | 425 | 36.5% | 225 | 56.1% | 41.0% | −15.2 ±3.7 | 0.22 |
| Trzy Kwaterki | 379 | 22.7% | 89 | 59.0% | 18.3% | −40.7 ±4.7 | 0.33 |
| Claudus Maximus | 352 | 19.9% | 128 | 55.3% | 20.0% | −35.4 ±4.7 | 0.12 |
| test4 | 350 | 16.6% | 84 | 63.5% | 20.6% | −42.9 ±5.4 | 0.17 |

- Mite's many wins against r8 come from volume: 1,129 games at 42%.
- The downloaded replays give the same picture: Mite −11.5 ±6.6 on 114 cells, BattleCats −11.6 ±6.3 on 86.
- **Per-cell outcomes are mostly not a property of the map.**
  - Our own versions agree per cell with phi 0.61 (v117/v118) and 0.48 (v118/v119).
  - Other teams' per-cell win rates correlate 0.1-0.3 with ours.

## 2. Different styles, same results

On shared cells (`cmpteam.py`), Mite and BattleCats play differently from us:
- **Gold at r100:** +75 and +44.
- **Tributes:** an earlier first tribute (~120 against our ~150) and more tributed gems (Mite 99 against our 62 at r200).
- **Wards:** +50-70.
- **Prism bags:** small, 105-220 at most against our ~420.

None of these separates their wins from their losses within cells, and their results are no better.

## 3. Within a cell, wins and losses part after the first fights

- **The opening is the same.** At r100, our wins and losses on the same cell are nearly identical (our gold +14 ±7),
  because Fish's opening is deterministic.
- **They part from r200, through fights.** At r500, wins against losses within a cell:

  | | us | Mite | BattleCats |
  |---|---:|---:|---:|
  | our kills | +1.4 | +2.0 | +3.1 |
  | our gems lost | −63 | −56 | −63 |
  | Fish's tributed gems | −95 | −124 | −217 |
  | Fish's Vesper's kills | −0.7 | −0.7 | −0.8 |

- **The divergent cells show the same signature.** On 53 shared cells, one team won every game and the other lost
  every one (we won 36 of these, they won 17). Whichever team won had more kills, fewer gems lost and more Fish
  Vesper deaths. Neither team had a style trait that the winning side always showed.
- **Denying Vesper's gold early is not supported.** Taking gold from Fish's half shows no gain within cells:
  +12.6 ±16.5 at r300 for us.

## 4. Gem flows (our games)

- **Where the gems go when Fish wins.**
  - Fish tributes 1,001 gems from captures and 286 from kills; 199 of those kills are its Vesper's.
  - We lose 296 gems to deaths, 202 of them from the Prism.
  - Fish's Vesper carries Fish's 100+ bags, for 131 rounds a game.
- **Fish's Vesper dying decides a lot.** She dies in 186 of 563 games: we win 76.3% of those against 44.8% when she
  survives. The Prism makes most of her deaths (187 of 422).
- **The swing comes from the fights.** Whether she dies comes from the fights in point 3, not from any earlier
  economic difference.

## 5. Draft: Vesper against r8

- **The regression.** It is a logistic regression of the opponent's win on its picks, over every team's r8 games,
  with team and cell fixed effects (`draftreg.py`, `draftopp.py`).
  - Vesper scores −0.72 ±0.12 log-odds against the mean pick, against r8.
  - Against Fish r2 she scores −0.09 ±0.07.
  - The effect holds in both time halves, with or without Fish's own Vesper, and without our games.
  - Marcella scores −0.73.
- **By team, against r8:** Mite −0.10, BattleCats −0.15, us −0.32.
- **Our own difference-in-differences.** Our win rate dropped from r2 to r8 by 0.25/0.24 on the cells where we draft
  Vesper, against 0.11/0.13 on the others. Our Vesper's kills fell from 3.51 to 2.05 a game, and her deaths rose from
  0.59 to 0.90.

**Test: `fw-nv`** is chy-525 with Vesper banned in its own draft (`draft_model.h`, `banned = 1u << 1`). It was played at
200k with `gate.sh` (fgate pool v4, Fish body fr8-g25, Mite body mf-f9), batches 0-1.

Results against chy-525:

| read | win% (95% CI) | maps | games |
|---|---|---:|---:|
| fresh (decides) | 48.41% (47.73-49.08) | 5,120 | 40,960 |
| fresh, Fish | 47.73% (46.82-48.63) | 5,120 | 20,480 |
| fresh, Mite | 49.09% (48.18-50.00) | 5,120 | 20,480 |
| ladder (side read) | 46.88% (43.91-49.84) | 256 | 2,048 |

**REJECT** (LLR high −4.66, low −3.09).

- **Local tests can't settle the live signal.** The body doesn't reproduce it: on our Vesper cells, the body's
  win-rate excess over live is 4 ±7 points larger than on our other cells. So a local gate can't confirm or
  refute the live signal; only a live pairing could. The draft-drop-our-vesper arm reproduced this gate exactly.

## The book question

**Matching the book would teach mostly openings and fight luck.** Within a cell, wins and losses are the same until
the first fights. The cell explains only part of the outcome: our versions agree at phi 0.5-0.6, and other teams
correlate 0.1-0.3 with us. A bot trained to match the book would therefore learn openings that are identical in wins
and losses, plus the outcomes of fights.

**The book's value doesn't carry over.** It comes from replaying a known win on the exact cell, against an opponent
that is deterministic there, and none of that carries to fresh maps.

## Don't retry

- **Copying Mite's or BattleCats' style against Fish:** early tributes, more wards, small Prism bags. Their style
  differs and their results don't.
- **Denying Vesper gold** from Fish's half.
- **A global ban on our Vesper:** it loses against the bodies. A live-only Vesper read would need a live pairing.

## Scripts

All take `EXT`/`ROWS` inputs; the working data is in `~/tmp-offload/fwin`.

- **Features and comparisons.**
  - `feat.py`: per-game features.
  - `cmp.py`: wins against losses, overall and within cells.
  - `cmpteam.py`: us against another team on shared cells.
- **Downloads.** `prep.py` unzips the downloads.
- **Gems and deaths.** `gemsrc.py`, `lost.py`, `carriers.py`, `fcarry.py`, `vdeath.py`, `victims.py`, `idle.py`,
  `parks.py`, `split.py` and `peek.py` cover gem sources and losses, carriers and Vesper deaths.
- **Draft.** `draftreg.py` and `draftopp.py`: the pick regressions.
- **Gate.** `gate.sh`: the fgate wrapper.
