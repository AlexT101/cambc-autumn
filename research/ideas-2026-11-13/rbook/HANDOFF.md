# Replay book: handoff (2026-11-13 09:00Z)

Goal: a book of recorded wins that the finals bot replays against Fish and Mite on the 170 ladder maps (340 cells
each), Fish and Mite roughly level ("80%-80% or 70%-70%", user). Lock is Fri 23:59Z. Report to the coordinator
("main", via SendMessage); it relays live actions and the user.

**Main line now: the exact format (`bots/variants/rbook-x`, work dir `~/tmp-offload/rbook/x1`). Its build and
checks are running; read `x1/stage.out` when `x1/stage.DONE` exists, then `x1/forcecheck.out` (`x1/go.DONE`).**

## Constraints

- Never edit `bots/charybdis`, `bots/ocean` or `bots/baselines`. Work in `bots/variants/` (gitignored).
- Commit only paths under `research/ideas-2026-11-13/rbook/`, explicitly; never push.
- No uploads, no scrim quota, no edits to the live scheduler or queue: the coordinator's live agent does those.
- Uploads are unmasked. Never print or commit `tools/livemask/livemask.key` (seeds.py reads it; nothing stores it).
- Games: fastrunner and the slot pool (rbuild and the scripts here already do). Never `pkill -f`/`pgrep -f` a
  pattern that matches your own command line; wait on done-files.
- Size: the platform rejects a compressed source over 5 MB. Keep a `cambc bundle` zip at or under 4.9 MB.
- Upload notes: 80 characters at most (the platform refused a longer one).
- Token use is tight: one background waiter a phase, scripts for bulk work, short reports at decisions only.

## What changed since 08:20Z

- **Fish reads our priority values** (v121 live test of plain priorities, 40 cells against the Fish r8 pin): 26
  replayed exactly, 14 diverged (rounds 49 to 992); 37 of 40 won (3 diverged and lost: 04duel_ring b, 02guardians b,
  01hooks a). Controls with recorded priorities: v120 21 of 21 exact, v122 (rbook-ff) 6 of 6. So an entry must
  publish exactly what its recording published; the local verify cannot see this (the puppet ignores our values).
  A plain-format Fish cell is worth about 0.92, not 1. Whether Mite reads them is unknown (stage 1 measures it).
- **How to compare a live version with its recordings**: `oppwatch.py` reads only the unpinned hourly checks. Use
  `python3 livecmp.py --version N --book WORK [--plain] [--bot variants/BOT] [--opp Mite]` (from this directory):
  every finished game of version N on a book cell, pinned or not; `--plain` for a plain-priority book. Takes a few
  minutes on a loaded box.
- **Mite r10 plays as r9**: all 40 r10 games of v119 that were in games.jsonl at 08:14Z equal v119's r9 game on the
  cell (picks, rounds, gems, gold, kills). So the Mite book is built from r9 (`--opp Mite:r9`): 268 cells have a
  win by v117/118/119, 267 reproduce locally. The coordinator reports a Mite change at 08:46Z; I have not looked
  at it (`oppwatch.py --opp Mite --refset r10`, and compare newer games with the r9 ones by cell).
- **Same-draft cells** (the user's classification question): the book key is order-sensitive (`book.cc start()`
  compares both teams' picks round by round). Fish r8 and Mite r9 draft the same team in the same order against us
  on 18 of 340 cells (32 if order is ignored). We hold a win against both on 7 (01broken_curve a/b, 02guardians a,
  03honeycomb a, 04mesas b, 05sweet_shop a/b). The builder keeps one entry a key (first `--opp`, Fish); against the
  other opponent the book replays the shared opening and hands over. Decision: no two-entries-per-key code.
- **Stage 1, `rbook-fm1`** (work `~/tmp-offload/rbook/fm1`), handed to the coordinator 08:50Z as a candidate:
  rbook-prio's host, plain priorities, 481 entries: Fish 230 (229 ours + `03contours b`, NEETCoders, exact draft,
  key v900), Mite 251. Left out for size by `pick_entries.py`: 28 Fish and 9 Mite entries on cells all our versions
  won; the 7 same-draft Mite entries; `adgato_gemcombat5 b` (does not reproduce locally). Checks: verify 481/481;
  bundle 4,808,789 bytes; 100M bench 52/52 identical to chy-525f; fallback test 24 games, 123 bodies handed over,
  150,865 off-book reads, 0 invalid; real fuel 232/300 fresh games identical; 12 of 25,600 fresh maps share terrain
  and camp layout with an entry (all `mut-*` copies of ladder maps). Note: `Charybdis 525 + fuel 01-02 + Fish
  r8/Mite r9 book, plain prio (481)`. Test cells: `fm1/cells40-mite.json` (Mite r10 pin), `fm1/cells10-fish.json`
  (Fish cells v121 did not play). The coordinator sends the version number when the games are in: run livecmp.py
  with `--plain --bot variants/rbook-fm1 --book ~/tmp-offload/rbook/fm1`.
- **Stage 2, `rbook-fm2`** (work `~/tmp-offload/rbook/fm2`): stage 1 plus 21 forced Fish entries, plain priorities,
  479 entries (Fish 239, Mite 240). **Held: not to be uploaded as a plain build.** All checks done: verify 479/479;
  bundle 4,837,090; fallback test 0 invalid; 100M bench 49/52 identical, the three that differ are forced cells
  (00expanse a/b, 00swirl a), as intended; forcecheck 21 cells, 0 bad (11 won against chy-525f).
- **Forced entries** (other teams' wins against Fish whose picks our draft does not make): files in
  `~/tmp-offload/rbook-foreign/w4/` (`extra.tsv`, fingerprints `fp.json`), write-up
  `research/ideas-2026-11-13/rbook-foreign/README.md`, `costs-w4.tsv`. Keys `-v901-` are forced (`rbuild
  --force-versions 901`), `-v900-` is the exact one. In the builds: the 15 the user approved (they displace no Mite
  entry: 00expanse b, 00the_line a, 00rows b, 00stampede a/b, 04gap b, 04two_kingdoms a, 05chiseled_brick b,
  05mineshaft b, 00galaxy a/b, 00swirl a, 00vault a, 01elk_arena a, 05runway a) and 6 the coordinator agreed (their
  Mite entry is a v117/v118 game: 00expanse a, 00elkring b, 04bowls b, 05border a, 05nest b, 05space_station b);
  the Mite entries on those 6 cells are dropped (`drop.txt`). The other 16 are not approved. `x1/extra.tsv` is the
  22-line list (21 forced + exact).
- **Forced-line test against Mite**: the coordinator is uploading `bots/variants/rbfor-prio` (all 37 forced, plain
  priorities) to play `~/tmp-offload/rbook/forced-mite/cells35.json` against the Mite r10 pin. Its wins are Mite
  wins on the forced draft: record them as Mite entries (`--extra`, forced; they are games of an unmasked bot, so
  they store as they are). Rule agreed: force a displaced cell if the forced line beat Mite there, and book that game.

## The exact format (`--prio seeded`), the main line

Why: recorded priorities replay exactly but our masked versions' values are half noise (245 entries filled the
bundle); plain priorities are small but Fish reacts to them.

Design:
- A masked version (v106-v120) published `rank << 16 | tag << 14 | (payload ^ mask)`, mask and 2-bit round tag drawn
  per round and body from a per-game seed (`tools/livemask/prio_stream.h`: `publish`, `mask_of`, `tag_of`).
- `game.seed = mix(mix(place ^ key[1]) ^ picks ^ key[0])`: place is the map's width, height, group count and our
  spawn centre; picks our side and body types. `seeds.py place` played a chy-525f copy that prints those facts at
  World's init and resigns, on all 340 cells: `place.json` (committed). `seeds.seed(map, side, picks)` then needs
  only the key file. **The bot holds the seed (8 bytes an entry), never the key.**
- `build_book.py --prio seeded`: each priority is xored with `seeds.word(seed, round, body)` (what the mask added
  to its low half) and coded as its change from the last unmasked value; the decoder xors the word back, so the
  value set is the recorded one bit for bit whatever the seed (a wrong seed costs size only). Seed 0 = stored as it
  was: other teams' games, puppets, and games of our unmasked versions (v121 and later).
- Host: `rbook-x` = `rbook-ff` (recorded format + the per-body plain bit in `comms.cc`, live as v122) with three
  edits in `book.cc`: `mask_mix`/`mask_word`, `Stream::{seed, body, round}` (round counted in `turn()`), and the
  `book_data::prio_seeded` branch of the priority decode; `start()` sets the stream's seed and body. `Entry` has a
  `seed` field; `book_data.h` carries `prio_seeded`. A header from this build_book works in the older hosts too.

Shown so far:
- `seeds.py check` on four entries (v117, v118, v119): the round tag comes out 0 on 100% of priorities and the
  unmasked low halves take 24 to 99 distinct values among thousands: the seeds are right.
- Size (sizes run, 539 entries incl. 21 forced + exact): blob 5,730,966, about 10.6 KB an entry (plain 8.9, recorded
  16.9). `pick_entries.py --blob 4130000 --balance` keeps 411: Fish 206, Mite 205; dropped 73 Fish and 49 Mite
  entries on cells our versions mostly won (expected cost 27.7 cells of 680).

Not shown yet (the running job answers the first four):
- Verify: `rbuild --prio seeded` compares with `cmp.mjs` (priority values included), so N/N proves the decode.
- Bundle size, fallback test (`--plain`, as for rbook-ff), 100M bench, real-fuel bench, forcecheck.
- Live: exact replays as for v120/v122 (livecmp.py without `--plain`). Other teams' entries have never been
  played live: their replay rests on Fish being deterministic against the recorded actions.

What other teams' priorities look like: plain small values (NEETCoders: 204 sets, 18 distinct) or structured
unmasked ones (a Mite game: 1,250 sets, 486 distinct). Stored as they are, so they replay exactly.

Known to be hard or open:
- Recordings of our unmasked versions (v121 plain book, v122, rbook-fm1, rbfor-prio): seed 0, no mask. A game that
  left a plain book mid-way publishes plain marks, then host payloads: store as recorded (seeded format, seed 0),
  never through `plain_priorities` (that rewrites the values). `build_book` picks seed 0 by the key's version
  (106-120 are masked): keep that rule true for new keys.
- A masked turn that set its priority after a rollover may carry the previous round's mask: it codes badly, exactly.
- Squeezing more: priorities cost about 1.8 KB an entry and fingerprints about 2.1 KB. A value cache would gain
  about 14 entries; not worth new decode code. The host's source is 598 KB of the bundle.
- A host swap (the user expects a newer charybdis before the lock): copy the new host, apply the book code
  (regenerate `host.patch` from `rbook-x` against its base: book.cc, book.h, draft.cc, main.cc, unity.cpp, and
  rbook-ff's plain bit in comms.cc/comms.h/turn_order.cc), then `PRIO=seeded stage.sh` with the same keys: verify
  fails on any entry whose picks the new draft no longer makes (those then need `--force` or are dropped).
  `host.patch` in this directory is still the 01:48Z one: regenerate it from the bot that becomes the final.

## Estimates (mine, not measured; per 340 cells)

- v122 as is: Fish 78%, Mite 66%. Stage 1 plain: Fish about 72%, Mite 75-80%.
- Exact build (411): Fish about 80% (206 exact + dropped cells at about 0.79 + cells nobody won at about 0.12),
  Mite about 76%. Assumes Mite still plays as r9.

## Decision rules agreed with the coordinator

- Stage 1 replaces v122 as REST if its 40 Mite cells come in at 90% or better, until the exact build exists.
- Forced and other-team entries go into the exact-format build, not a plain one.
- A sweep of a candidate over its own cells (to drop entries it loses) is deferred: exact entries make it unneeded.
- Balance Fish and Mite when size or forced trades bind (`pick_entries.py --balance`).
- A host swap must stay a quick scripted step (above).
- Report when the exact format verifies or hits a wall; hand over a stage as dir + note + cell list.

## Commands (from the repo root)

```
R=research/ideas-2026-11-13/rbook; W=~/tmp-offload/rbook/x1
ARGS=(--opp 'Intercontinental Fish:r8' --opp Mite:r9 --extra $W/extra.tsv --force-versions 901)
# sizes of everything, then the pick, then build + verify + bundle + fallback + fresh maps + benches (x1/go.sh does all)
python3 $R/rbuild.py --host variants/rbook-x --work $W --prio seeded "${ARGS[@]}" --no-build > $W/sizes.out 2>&1
python3 $R/pick_entries.py $W --blob 4130000 --opp 'Intercontinental Fish:r8' --opp Mite:r9 --balance \
        --drop $(cat $W/drop.txt) > $W/keys.txt 2> $W/pick.out
PRIO=seeded $R/stage.sh rbook-x $W $W/keys.txt "${ARGS[@]}"        # -> $W/stage.out, $W/stage.DONE
(cd $R && python3 forcecheck.py --host variants/rbook-x --opp variants/chy-525f --work $W)
(cd $R && python3 seeds.py check ~/tmp-offload/rbook/fish/ent/KEY.json)
(cd $R && python3 livecmp.py --version N --book $W --bot variants/rbook-x [--opp Mite])
```

- A new work dir: symlink `raw` and `ent` to `~/tmp-offload/rbook/fish/`, copy `fp.json`, `bad.json`, `extra.tsv`,
  `drop.txt` from `x1`.
- `rbuild --opp NAME:REFSET` takes, per cell, our shortest win with that refset; where two opponents pick alike the
  first keeps the entry. `--keys FILE` keeps only those entries (`--cells` cannot split a cell by opponent).
- `stage.sh` pass criteria: verify N/N; bundle at most 4.9 MB; fallback test with every game finished and 0 invalid
  reads; 100M bench identical except on forced cells (49/52 with these 21: 00expanse a/b, 00swirl a differ).
- `pick_entries.py`: an entry is worth 1 - (w + 1) / (n + 2) over our n versions that played the cell, kept by
  worth per byte; blob 4,130,000 gives a bundle of about 4.84 MB.

## Bots (`bots/variants/`)

| Dir | What it is |
|---|---|
| `chy-525`, `chy-525f` | The host (charybdis 525) and the same + fuel patches 01, 02: the bench reference. |
| `rbook-ff` | Live v122, REST: recorded priorities, 245 Fish entries. |
| `rbook-prio` | Live v121: plain priorities, 257 Fish entries. |
| `rbook-fm1` | Stage 1, handed over: plain, Fish 230 + Mite 251. |
| `rbook-fm2` | Stage 2, held: plain, + 21 forced. |
| `rbook-x` | **Exact format: rbook-ff + seeded decode; the book in it is the 411-entry pick.** |
| `rbfor-prio` | The foreign agent's: 37 forced + exact, plain; in the forced-line Mite test. |
| `rbook-placebot` | seeds.py's map-facts tool. Unneeded once place.json exists. |
| `*-pup-*`, `*-rec-*`, `*-fb`, `*-fb-pup` | Made by rbuild / fallbacktest. Rebuilt on each run. |

## Running now

- `~/tmp-offload/rbook/x1/go.sh` (nohup): the exact build's `stage.sh`, then forcecheck. Outputs `x1/stage.out`
  (done-marker `x1/stage.DONE`), `x1/forcecheck.out` (`x1/go.DONE`), log `x1/go.log`, benches
  `~/tmp-offload/rbook/bench/rbook-x-*.json`. At 08:57Z it was in rbuild's build and verify.
- Nothing else of mine runs; fm1 and fm2 are finished. No waiter is armed.

## Owed, in order

1. Read `x1/stage.out`: if verify is N/N and the checks pass, hand `rbook-x` to the coordinator (dir, note of at
   most 80 characters, e.g. `Charybdis 525 + fuel 01-02 + Fish r8/Mite r9 exact book (411, 21 forced)`, and a
   cell list that includes forced cells and Mite cells). If verify fails on some entries, look at whether they are
   masked-version entries (decode) or forced ones before anything else.
2. Stage 1's live games (version number from the coordinator): livecmp.py; report exact / diverged / won for Mite
   and Fish. 90% or better on the Mite cells makes stage 1 REST.
3. rbfor-prio's Mite games: record the wins as forced Mite entries, apply the rule above, rebuild the exact book.
4. The 08:46Z Mite change: how many r9 entries still replay (a small live check group, or compare new unpinned
   Mite games with r9's by cell).
5. Regenerate `host.patch` from the final bot; keep the host swap scripted.

## Traps

- `cambc bundle` does not overwrite an existing zip.
- rbuild copies the host's `src` at its start and builds the host at its end: do not edit a host while it runs.
- A sizes run rewrites `WORK/book_cells.json` with every entry; a `--keys` build rewrites it with the kept ones.
  `pick_entries.py` needs the sizes run's.
- Any fuel overhead changes about 8% of real-fuel games chaotically; judge by the 100M identity.
- The JS map holds the canonical half: `layoutHash` adds each camp's mirror.
- Debug traces need a debug build: fallbacktest runs without `--release`.
