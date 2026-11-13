# Other teams' wins against Fish r8 in the replay book (2026-11-13)

## Mite refresh, 11:25 UTC

`mine_mite.py` reads big-arm's capture database without platform requests and fetches a bounded set of
cached ranked wins by other teams. It excludes our team, screens forced drafts against the existing Fish
entries, and writes `candidates.json`, `summary.json` and an rbuild-compatible `provisional.tsv`.
Timestamps and matching drafts do not establish the opponent version. **Do not admit these entries to
the ranked book until they pass live validation against the target pin.**

The first pull since 08:00 found 454 foreign wins on 203 map/side cells (ranked and unranked), with 10 cached
ranked recordings and three cached candidates passing the Fish draft screen. All three reproduce exactly
against their recorded opponent puppets on `variants/rbook-mite-foreign-r11`, using seeded priorities:

| cell | winning team | existing x2 Mite entry |
|---|---|---|
| 02harvest a | NEETCoders | none |
| 04yin_yang a | Intercontinental Fish | yes, old pin |
| 05space_station b | Intercontinental Fish | yes, old pin |

All three require forced picks. Work and recordings:
`/home/ubuntu/tmp-offload/rbook-foreign/mite-refresh-r11/`; local verification: `verify/verify.json` (3/3).
The three-entry qualification bot is **not a replacement REST bot**. The r11 refresh currently uses our
own sweep wins only; foreign entries remain pending target-pin validation and combined-book checks.
The forced-draft fallback check against `variants/chy-525f` completed all three games with zero bad
drafts/guards (one win; this tiny sample is not a strength measurement).

## Earlier Fish work

The question: which other teams' wins against Fish r8 can the replay book play, on cells where we have no win of ours?
The book is in `../rbook/`.

## When a foreign win replays without forcing a pick

- **The draft must match exactly.** The winner must have drafted 525's team in 525's order, on our side of the map.
  - Champion ids and spawn tiles follow pick order. The same champions in another order start on other tiles, so the
    replay breaks at once.
  - A win from the other side does not transfer: team A and team B start different rounds.
  - Our draft against Fish is one team per cell: all 340 cells drafted the same team in every r8 game.
- **Only one new cell qualifies.** big-arm's capture holds every Fish game since 11-12 11:50. Only 10 cells have
  another team's win with 525's exact team, and 9 of them are already in the book from our own wins.
  - The new cell is **03contours:b**: NEETCoders, 686 rounds, ended at 1,069 gems.
  - It was verified on both the rbook-ff host and the plain-priority host.
- **Mite r9 adds nothing.** Only 3 cells have another team's exact-draft win against Mite r9, and we already win all
  3 ourselves.

## Forced picks (built and verified; not approved)

`w4` holds one r8 win per cell for the 82 cells with no win of ours, where a replay of the game is on disk.
- **Fetched from big-arm:** 3 ranked replays, in one stream.
- **What verify gave:** 38 entries (37 forced, plus the exact one), and every one reproduces against the Fish puppet
  on a copy of `rbook-prio`. The build used `rbuild --prio plain --force-versions 901`.
- **Bundle:** 1,069,277 bytes with these 38 entries alone. The host with an empty book is 598,568 bytes, so the
  entries add about 12.4 KB each.
- **Left out:** 4 cells whose on-disk wins were against another Fish version (priority signature about 0.13 against
  1.0 for r8).
- **Not reachable:** 30 cells have wins only in unranked games. big-arm keeps replays of ranked games only (276 of
  4,635 Fish rows on 11-13), so those replays would need the platform API.
- **No win by anyone:** 10 cells.

**The class says who else meets a forced pick.** See `costs-w4.tsv`, one row per entry.

| class | entries | draft departs from 525 at | known about the opponent by then |
|---|---:|---|---|
| exact | 1 | never | — |
| prefix2 | 4 | pick 2 | Fish's first 2 picks seen |
| prefix1 | 19 | pick 1 | Fish's pick 0 seen |
| blind | 14 | pick 0 | nothing: every opponent on the cell gets it |

**Mite meets the forced pick on 35 of the 37 cells.** Mite r9 opens like Fish there, mostly Vesper first. The two
exceptions are 00the_line:a and 04gap:b.
- On those 35 cells, our r9 games against Mite won 40 of 112 (36%).
- Forcing replaces that draft with a partly forced one. Its strength against Mite is untested.
- The `ladder_share_prefix` column: how many other teams, in their games against Fish on that map, opened as Fish did.
  It is a proxy for the rest of the ladder.
- Forcing only fires on the exact ladder map: the map id and layout hash are checked. Fresh maps are unaffected.

**No new code is needed to force picks.**
- `build_book.py --force KEYS` (`rbuild --force-versions 901` for the `v901` keys) sets `force_draft = true` and each
  entry's `force` flag.
- `draft.cc` then takes `book::draft_order()`. It plays an entry's picks while our picks and the opponent's picks so
  far match that entry, and hands back to 525's draft at the first mismatch.
- In the current book this is off only because no entry is marked `force`.
- The 37 forced games above reproduced with the shipped host drafting them.

## Files

- **Scripts:**
  - `cells.py`: candidate wins per cell, by class.
  - `forced.py`: extracts and r8-scores the wins on disk and writes rbuild's `--extra` list and `classes.json`.
  - `costs.py`: the cost table.
  - `r8check.py`: the r8 signature and opening tests.
  - `extra.py`: the older `--extra` writer.
- **Work dirs** (in `~/tmp-offload/rbook-foreign/`):
  - `w4`: the verified forced batch; `w4/extra.tsv` is the list for the book agent.
  - `w3`: the exact entry on the rbook-ff host.
  - `c2/cands.json`: the candidates.
  - `rows/`: the capture pulls.
