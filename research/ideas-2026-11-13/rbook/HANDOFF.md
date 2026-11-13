# Replay book: handoff (2026-11-13 08:20Z)

Goal: a book of our recorded wins that the finals bot replays against Fish (and Mite), about 80% against each.
Lock is Fri 23:59Z; the seeding sim wants the book live by about 12:00Z. Report to the coordinator ("main").

## Constraints

- Never edit `bots/charybdis`, `bots/ocean` or `bots/baselines`. Work in `bots/variants/` (gitignored).
- Commit only paths under `research/ideas-2026-11-13/rbook/`, explicitly; never push.
- No uploads, no scrim quota, no edits to the live scheduler or queue: the coordinator's live agent does those.
- Uploads are unmasked now. Never print or commit `tools/livemask/livemask.key`; delete any masked copy after use.
- Games: fastrunner and the slot pool (rbuild and the scripts here already do). Never `pkill -f`/`pgrep -f` a
  pattern that matches your own command line; wait on done-files.
- Size: the platform rejects a compressed source over 5 MB. Target a `cambc bundle` zip of at most 4.9 MB.
- Keep token use low: one background waiter a phase, scripts for bulk work.

## Bots (`bots/variants/`)

| Dir | What it is |
|---|---|
| `chy-525` | The host: charybdis 525, frozen. |
| `chy-525f` | chy-525 + fuel patches `research/fuel-2026-11-13/patches/01,02`. Bench reference. |
| `rbook-525` | chy-525 + `host.patch` (the book code), older working copy. |
| `rbook-525f` | chy-525f + `host.patch` + the 169-entry d2 book. |
| `rbook-fish-d1` | Live v120 (masked upload), 193 entries. Frozen. |
| `rbook-fish-d2` | 169 entries with the camp-layout check. Frozen. |
| `rbook-ff` | **Fallback final, handed to the live side 08:15Z.** rbook-525f + per-body plain bit (below) + 245 Fish r8 entries, recorded priorities. |
| `rbook-ff2` | rbook-ff before the plain bit, 250-entry book (5.01 MB: too big). Base of rbook-prio. |
| `rbook-prio` | **Plain-priority candidate.** rbook-ff2's host + mark test in `comms.cc` + plain decode in `book.cc`; 257 Fish r8 entries, 2.97 MB. |
| `*-pup-fish`, `*-rec-fish`, `*-fb`, `*-fb-pup` | Made by rbuild / fallbacktest (puppet, recorder, traced copies). Rebuilt on each run. |
| `rbook-test*`, `rbook-ocean`, `rbook-mfb*`, `rbook-opp*`, `rbook-d1-mverify` | Old tests. Unused. |

`host.patch` is the book code against chy-525 (book.cc, book.h, draft.cc, main.cc, unity.cpp), without rbook-ff's
plain bit and without rbook-prio's two edits. Regenerate it from the bot that becomes the final.

## Data (`~/tmp-offload/rbook/`)

- `fish/`: `raw/KEY.repl26a` (every extracted live replay) and `ent/KEY.json` (extract.mjs output). Other work
  dirs symlink both. Also d2's book files.
- `ff/`: rbook-ff's work dir. `book_cells.json`, `book.jsonl`, `cells-ff.txt` (the kept cells), `final.out` (its
  check results), `fallback/` (fallback test replays), `bundle.zip`.
- `prio/`: rbook-prio's work dir. `build.out`, `cells40.json` (the live test cells), `final.out` + `final.DONE`.
- `bench/`: bench.py outputs, `BOT-100M.json`, `BOT-0.json`, `BOT-fresh-0.json`.
- `fresh_bench.txt`: the 300 fresh maps of the real-fuel bench. `freshids/partNN.json`: ids of 25,600 fresh maps.
- `hostcheck/`: which v119 wins a host build replays exactly (only meaningful for a masked host).
- `fp.json` in a work dir caches the recorded fingerprints by game key; copy it into a new work dir.
- `~/tmp-offload/rbook-foreign/w3/`: the foreign agent's files (not mine).

## Design

- **Entry**: one recorded win (map, our side, both teams' picks). Key `MAP-SIDE-vVERSION-MATCHID12`.
- **Match** (`book.cc start()`, cheapest first, on each champion's first turn): side and size table, tile counts
  per kind, number of draft rounds, both teams' picks, terrain hash (`map_id`), camp layout hash.
- **Play**: each champion replays its recorded actions per round. Each turn it first checks a 4-bit fingerprint
  of what it sees (champions in sight, own gold and gems, both tributes). On a mismatch, an action error or the
  entry's end it hands over for good and the host cold-starts (`play_turn(true)`). Recorded out-of-fuel turns
  spin to the round's end.
- **Draft**: the host's own draft makes the recorded picks (117, 118, 119 draft as 525 does), so forcing is
  compiled out (`force_draft = false`). `model_draft()` is always called first, as its first call must fall in the
  10M first draft turn.
- **Forced picks** (not approved by the user): `build_book --force KEYS|FILE` or `rbuild --force-versions V,..`
  marks entries; `book::draft_order()` then plays an entry's picks while the opponent's match. Code exists and
  was tested 8/8 on ocean 506 games under a 525 host. Cost: the forced pick is made blind, on every game on
  that map and side, whoever the opponent is.
- **Priorities, recorded format** (rbook-ff): on-book bodies publish the recorded values (masked ones, from
  masked live games). An unmasked host must not read them, so on a book game the shared-byte layout reserves one
  bit a body (`comms.cc`: `plain_on`, `plain_published`), set when a body first publishes its own priority;
  `payload_of` ignores allies whose bit is unset. Costs about 34 fuel a turn in every game.
- **Priorities, plain format** (rbook-prio, `build_book --prio plain`, `plain_priorities()`): each on-book body
  publishes `(k << 16) | 0xE000`, k its place in the team's order for the next round (0, 1, .. for positive
  recorded values, -1, -2, .. for negative, since an unset priority is 0). Bits 14-15 of the low half are the
  on-book mark: the host's own payloads never set them, and `payload_of` returns -1 on them
  (`on_book_mark = 0xC000`). The builder asserts the order, ties included, is kept every round. `book_data.h`
  carries `plain_prio`; a host with the plain decode needs a header that has it.
  The replay then differs from the live game in our priority values only: compare with `cmp2.mjs`, not `cmp.mjs`.
  Not yet shown: that Fish ignores the values (live test below).
- **Host cells**: an unmasked or fuel-patched host does not replay v119's masked live wins exactly, so every
  cell any of our versions won gets an entry (no `--host-version`).

## Commands (from the repo root)

```
R=research/ideas-2026-11-13/rbook
# Build a book into a bot, record what is new, verify, bundle (work dir: symlink raw and ent, copy fp.json, bad.json)
python3 $R/rbuild.py --host variants/BOT --work WORK [--prio plain] [--cells FILE | --cap N] \
        [--opp "Intercontinental Fish:r8" --opp Mite:r10] [--versions 117,118,119] [--extra EXTRA.tsv]
# Verify another build of a book (entries read from the bot's book_data.h)
python3 $R/rbuild.py --host variants/BOT --work WORK --verify-only [--prio plain]
# 100M identity and real-fuel benches against chy-525f (its files are in bench/)
B=~/tmp-offload/rbook/bench
python3 tools/fuel/bench.py run variants/BOT --set wide --jobs 32 --out $B/BOT-100M.json
python3 tools/fuel/bench.py run variants/BOT --set wide --jobs 32 --fuel 0 --out $B/BOT-0.json
python3 tools/fuel/bench.py run variants/BOT --maps $(cat ~/tmp-offload/rbook/fresh_bench.txt) --fuel 0 --jobs 32 --out $B/BOT-fresh-0.json
python3 tools/fuel/bench.py compare $B/chy-525f-100M.json $B/BOT-100M.json     # want "identical replays: 52/52"
# Fallback test (opponent leaves at round 150; --plain = unmasked host)
(cd $R && python3 fallbacktest.py --host variants/BOT --work WORK --plain)
# Fresh-map false matches
python3 $R/freshcheck.py WORK/book.jsonl ~/tmp-offload/rbook/freshids/part??.json
# Size: rbuild prints "bundle: N bytes"; or
rm -f OUT.zip; cambc bundle bots/variants/BOT --output OUT.zip
# A live version's book games against their recordings (and whether the opponent changed)
python3 $R/oppwatch.py --book-version N --book WORK [--book-cells bots/variants/BOT/src/book/book_data.h] [--book-plain]
python3 $R/oppwatch.py --opp Mite --refset r10
```

- `rbuild --opp NAME:REFSET` selects, per cell, our shortest win in games.jsonl with that `refset`; the tag is
  the name's last word (`fish`, `mite`), with a puppet per tag. Where two opponents pick alike on a cell the
  first `--opp` keeps the entry.
- `--extra` lines: `REPLAY(.zip|.repl26a) OUR_SIDE KEY MAP`, added to the first `--opp`.
- Pass criteria used so far: verify N/N; 100M bench 52/52 identical; fallback test with every game finished, no
  payload read from an on-book ally, off-book reads 100% valid; bundle at most 4.9 MB.

## Results so far

- rbook-ff: verify 245/245; 4,825,558 bytes; 100M 52/52; fallback test passed (126 bodies handed over, median 3
  rounds from first to last, max 25; 0 reads from on-book allies; 135,756 off-book reads all valid).
  Real fuel: 191/300 fresh games identical to chy-525f, winner flips 11 against 9 (the plain bit's fuel).
  Left out for size: `00interlock a`, `00ribs b`, `01fracture a`, `01starfish b`, `05burger a` and the 8 newest
  v119 wins. `adgato_gemcombat5 b` does not reproduce locally.
- rbook-prio: verify 257/257 with cmp2; 2,965,484 bytes. Benches and fallback test: see running jobs.
- Fresh maps (25,600): 11 share terrain and camp layout with an entry; 8 have another team size (rejected by the
  draft-rounds check), 1 is the ladder map, 2 (mut-keyhole, mut-horseshoes) are the ladder map with its camps
  listed in another order (the book would start there on matching picks and hand over at the first difference).
- The fallback test's "reader off, ally on-book" valid count under `--plain` includes bodies whose BKOFF trace
  line is missing from stdout; a read happens only once the ally's bit is set, so those are off-book.

## Traps

- `cambc bundle` does not overwrite an existing zip.
- The JS map holds the canonical half: `layoutHash` adds each camp's mirror.
- Any fuel overhead, even 100 a turn, changes about 8% of real-fuel games chaotically; judge by 100M identity
  and, if needed, fgate (d2 against chy-525 at 100k was level: 50.07% (49.91-50.24) of 40,960).
- rbuild copies the host's `src` to the puppet and recorder at its start and builds the host at its end: do not
  edit the host while it runs.
- Debug traces (`debug_block`) need a debug build: fallbacktest runs without `--release`.
- Mite changes every 1-2 hours; Fish has been r8 since 2026-11-12 13:59Z.

## Running now

- A `nohup bash` chain for rbook-prio: fallback test, then the three benches and compares. Output
  `~/tmp-offload/rbook/prio/final.out`, done-marker `~/tmp-offload/rbook/prio/final.DONE`, bench files
  `~/tmp-offload/rbook/bench/rbook-prio-*.json`. Read `final.out` when the marker exists and judge it by the
  pass criteria above (for the fallback test: "payload left unread, ally on-book" should be about 100 and no
  invalid reads).

## Owed, in order

1. rbook-prio's benches and fallback test (above): report to the coordinator.
2. The live test of 40 plain-priority cells against the Fish r8 pin (`prio/cells40.json`; the coordinator sends
   the version number): `oppwatch.py --book-version N --book ~/tmp-offload/rbook/prio --book-plain --since ...`.
   Every game must show "book same". If so, plain priorities become the format.
3. Then rbook-prio as the final: add Mite entries (`--opp "Intercontinental Fish:r8" --opp Mite:r10` once the
   r10 sweep is in games.jsonl: v119 on 340 cells, then v118 and v117 on its losses; r9 data exists, up to 285
   cells), rerun every check, regenerate `host.patch`, send dir + upload note
   (`Charybdis 525 + fuel 01-02 + Fish r8 / Mite rN replay book, plain priorities (N cells)`).
4. The stale-entry question: ask for one check group of 5 r9-book cells against current Mite, to see how far
   stale entries replay before handing over.
5. Size choices if it does not all fit: our wins on cells the host loses first, then v119's wins, then others.
6. A fuel-patch bundle against chy-525f may arrive by about 12:00Z: one host refresh, then rerun the checks.

## New inputs

- A verified other-team entry: `03contours b` (NEETCoders), files in `~/tmp-offload/rbook-foreign/w3/`, built
  with recorded priorities; rebuild it with `--prio plain` through `--extra`.
- The foreign agent reports the other-team game on `04keyhole a`, `c6c5aaa4cb1e`, is not Fish r8 (signature
  0.13): drop it from any build that uses it. No book of mine holds it.
- Forced-pick entries (31 + 8 candidates) are being re-verified by that agent and are **not approved by the
  user**. They need `--force` (see Design).
- `COMPRESSION-LEAD.md`: only relevant if plain priorities fail the live test.
