# Carry: how Fish and Mite out-earn an ocean body with the same picks (2026-11-08)

Follow-up to [spar.md](spar.md)'s "carry-first gold" lead. Tools and arm patches in [carry-tools/](carry-tools/),
big files in `~/tmp-offload/carry/`. Data: the 500 v89 live games against Fish and r2 Mite, each paired with the same
(map, side, both drafts) game of oc-base27 against spar-oc29 (`econ.py`, `caps.py` and the rest).

**In one line:** no single carry-routing rule explains the gap. The live opponent earns +14% (Fish) / +18% (Mite) by
r200 with the same camp-hit count. The gain is spread over every phase and over three habits ocean lacks:
- it clears jointly and lets the carry hold;
- it doesn't ride home from small captures;
- it fights less.

Copying the first two in ocean's terms moved the behaviour a little and the earnings not at all. Locally one arm lost
(−1.5) and one is level.

## Correction to spar's fidelity table

`spar-tools/fidelity.py` and `early_types.py` keyed local replays by file name. The F and M runs share names
(`001-00ambush-12`), so 232 of 500 Fish rows were compared with the Mite-drafted spar game. Both are fixed: the key now
includes the batch. Corrected r200 earnings, live against the spar body:

| | Fish drafts | Mite drafts |
|---|---|---|
| team | 999 / 873 (+14%) | 1,059 / 901 (+18%) |
| Vesper Vale | +38% | +37% |
| Marcella | +46% | +71% |
| Heart of Ruin | −3% | +84% |
| supports | Issac −45%, Willow +72% | Tavi −62%, Cassi +37% |

## What their economy does differently (r ≤ 600, per game)

| | Fish | spar (Fish picks) | Mite | spar (Mite picks) |
|---|---|---|---|---|
| captures with ≥ 2 damage dealers (r200) | 53% | 42% | 49% | 41% |
| carry Vesper's own share of the damage on its holds (r200) | 0.43 | 0.62 | 0.39 | 0.57 |
| nearest ally ≤ 2 tiles (off-spawn champion-rounds, r200) | 61% | 45% | 53% | 41% |
| after a capture, the holder rides home (bag < 40) | 22-28% | 53% | 30-33% | 51-53% |
| after a capture, farms on (bag < 40) | 41-44% | 26-29% | 37-38% | 26-31% |
| healthy (≥ 0.6) completed recalls carrying gems | 7.5 | 14.4 | 9.0 | 13.8 |
| tributes under 25 gems | 41% | 5% | 51% | 5% |
| camp damage | +12% | | +17% | |
| gold per camp damage | = | | = | |
| champion-attack turns | 77 | 98 | 80 | 90 |
| deaths | 3.9 | 4.7 | 4.7 | 5.1 |

- **Joint clears, carry holds** (`caps.py`). Fish's supports help clear groups they then leave to the carry.
  - "Helped, not held" per game: HoR 1.9 vs 1.2, Vendetta 1.4 vs 0.8, Tavi 2.3 vs 1.1.
  - Its gold per capture is 80 vs 63: bigger groups, held by Vesper or Marcella.
  - This matches Fish's fitted farm choice: it goes where a visible ally is closer (+0.73), so it joins rather than
    partitions ([CHOICE.md](../fish-2026-11-05/CHOICE.md)).
- **No rides from small captures** (`after.py`, `qcost.py`, `recwhy.py`).
  - Ocean's `capture_recall` rides home whenever spawn-to-altar is shorter than here-to-altar, even for a bag
    under `min_bank` that then isn't banked. That is 8.3 recalls a game by r600 with 1-24 gems: 91% shop on landing,
    then walk back out (a median of 15 rounds to the next camp hit).
  - Fish keeps a recall from a capture only below 40% health.
- **The gap isn't one moment.** Gold leads from r25 (54 vs 43) and grows at about +10% a phase (`curve.py`).
  - Concentrating gold on the carry predicts nothing once team gold is held fixed: +0.1 ±0.9 points per +10% carry
    share in Fish's own games (`conc.py`). Team gold does (+1.7 points per 100 gold at r200).
  - Fish also buys Capture emblems that ocean's table rarely picks (Vendetta 3.1 vs 0.6 shard-equivalents by r300,
    `items.py`). Not tested here.

## Arms (each on oc-base29; fidelity = body playing the live drafts against oc-base27)

| arm | what | mechanism moved | local panel (0.4975/0.50) | varied | spar_ab |
|---|---|---|---|---|---|
| nosmallride (`carry29`) | `capture_recall` only for a bag bankable after payout | capture rides 16.3 → 6.1 a game, but other trips replace half; earnings −3% | **−1.55, H0** at 11,937 units | 49.7% (undecided) | −1.9 ±3.1 |
| join15 | farm rates a group claimed by an ally that out-holds us (value_holder's terms) ×1.5 | ≤ 2 tiles 45 → 47% (F), 41 → 44% (M); multi-dealer 34 → 37%; Mite-draft Vesper +43 and Marcella +33 gold at r200, Fish-draft flat | −0.26, undecided (LLR −0.74 at 30,720) | 50.5% (LLR +1.23) | −0.9 ±3.4 |
| join20 | the same at ×2.0 | ≤ 2 tiles 49 / 46%; earnings flat | **−0.79, H0** at 27,117 | 50.3% | −1.9 ±3.6 |

- Spar bodies against oc-base27: cr29 −2.9, jn15 +2.0 and jn20 +3.9 points (±5). The per-map r with live is 0.17-0.19,
  against o29's 0.25. All of it is noise.
- **Reading.**
  - Ocean's rides home are priced: the shop and heal on landing are worth what they cost, so removing them loses.
  - Fish's cohesion comes from its whole farm choice; a claim-join multiplier moves it only a quarter of the way
    before costing locally.
  - Neither arm meets the TEST-STANDARD bar. join15 is level and is queued live at the lowest priority, for the
    coordinator to keep or drop.
