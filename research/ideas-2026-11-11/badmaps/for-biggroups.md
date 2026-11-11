# Handoff to biggroups: what badmaps already decoded (2026-11-11)

Big Golem / Monolith / herd groups go to Fish and Mite and not to us. Live evidence is v115's 512 pinned scrims
(256 each against Fish r2 and Mite r6).

## Data (read-only for you)
- `~/tmp-offload/badmaps/ext/`: extract.mjs output for all 512 v115 scrims (plus 8 repeats). Match ids are the
  `.repl26a` basenames in `index.json`; game rows (map, side, result, drafts) in `an/v115-games.json`.
- `~/tmp-offload/badmaps/extl/`: 506 against `spar-dvn1-Mt3q` and `spar-dvn1-Flp4`, 256 ladder games each, release
  builds (batches `replays/batch-20261111-0546*-ab-bm-506-vs-{Mt3q,Flp4}-ladder-ladder`, all replays kept).
- `~/tmp-offload/badmaps/an/`: `lib.py` (live loader, `find(map, opp, side)`, `acct`), `lib2.py` (local batches),
  `bygroup.py MAP [Mite|Inte]` (captures per group, with first capture rounds), `lsumm.py EXT MAP...` (the same by
  class for local games), `v115-class.pkl` (per game: captures and gems by (own|enemy|mid, class), first capture round
  per class and team, the map's gem supply per class), `scrim-bymap.json` (v105-v115 wins per map and opponent).

## Findings
- All v115 scrims: Fish and Mite take their first Golem far earlier. Median first Golem-group capture: us r440,
  Fish r283 (80 games on Golem maps); us r385, Mite r192. They are first in 64 of the 99 games where both take one.
  Golem captures a game: us 3.23, Fish 2.67; us 2.25, Mite 3.41. Monoliths: us 0.55 / 0.46 a game, Fish 0.84, Mite 0.49.
- 02geodes (0 of 4, v105-v115 2 of 46): each side has a geode nearer to it (Golem ringed by 8 gem clusters, 92 gems,
  160 gold, respawn 80; engine side label "mid"). Fish and Mite take theirs 5-6 times from r86; we took ours 0 times in
  all 4 games (Fish also took a 6th). Own-side Elk, Wolf and cluster farming is level. Our draft there is Vendetta,
  C&I, Prism, Varg, HoR. Locally 506 takes a geode 1-3 times a game against the bodies.
- 00rows (0 of 4): both teams farm their three wolf triples level (31-36 captures each); the game is decided by the
  double Monolith with 10 clusters (470 gems), which Fish or Mite captures once at r788-r839 and we never do. Zero to
  four deaths a game: no fighting.
- 02famine (1 of 4): the mid Monolith (200 gems) goes to them twice in every game, to us never.
- 00stampede (0 of 4): the mid Elk herd is the only gem source: they capture it 6-8 times (1,057-1,396 gems), we 0-1
  times, with 17-41 deaths of ours. Locally against the bodies it is the reverse (we 6-7, they 0-1), so this one is
  their play, not their draft.
- 04waves against Mite (0 of 2): Mite takes all Golems, ours included (10-11 captures to 0); against Fish we take 9
  and win both.
- 02fields (0 of 4): they take the Monolith on our side once (270 gems) and 1-3 Golems to our 1-2.
- Losses in which we never captured a Golem/Monolith group and they did, by map: rows 4, geodes 4, treasure_box 3,
  gold_rush 3, famine 3, guardians 2, twisty 2, fields 3, gap 2, waves 2.
- Not a general weakness in the win rate: v115 wins 66-71% on Monolith maps and 60-64% on Golem maps, against
  58-72% on maps with neither.
