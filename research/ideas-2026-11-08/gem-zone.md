# Gem-zone control (ocean, 2026-11-08; nothing merged)

The user's idea: extend the one-altar altar control (CHANGES 408, `economy/altar_guard.cc`) to maps whose gems all
lie in one small area, and heavily prioritise controlling it. Tools and patches: [gemzone-tools/](gemzone-tools/):
`gemzone.mjs GAP [--box] DIRS` (zones per map, JSON lines), `make_set.py OUT SUITES` (copies the zone maps),
`render.mjs MAPS` (ASCII), and `zone_stats.py` / `zone_detail.py MAP` over scrim replays (`GEMZONE_DIR` holding
`ladder.jsonl` from `gemzone.mjs 5 maps/*.map26a` and `ana/` from `tools/replay/extract.mjs --out` of the unzipped
`.repl26a`s).

## Which maps

A gem zone: the gem-bearing camp groups (gold clusters excluded) linked by gaps of at most 5, the cluster with the
most gems a round (gems over the group's respawn) holding 75%+ of the map's and at most 12 tiles across. By symmetry
it straddles the centre or the axis, so it is always shared.

- Ladder: 6 of 128 maps (00stampede, 00ribs, 01elk-arena, 03one-gem, 00vault, 00anvil; near misses 01hooks,
  00fragment, 04compass). `maps/gen` + `gen-s1`: 29 of 512. Fresh ladder-mix suites: 2.1-2.4%.
- ocean's `shared_gems` is not this (every non-Monolith gem group 70+ gems: the kite flag).

## Ladder evidence

Scrims v78-v86 (`research/ladder-scrims-2026-11-06`, Fish and Mite): 42% on the six maps (49/116) against 60%
overall and 65% on one-altar maps. The archive (8.2k games against the whole ladder, older bots) shows no gap (82%
against 80%), but its two worst maps are the same: 00stampede 65%, 00ribs 70%. Per map 28 scrim games, some of them
byte-identical rematches (252 distinct replays of 295).

Two failures, from the scrim replays (`zone_stats.py`, `zone_detail.py`):
- **00stampede** (one shared 160-gem elk and cluster group at the east edge, 53 from both spawns): Fish and Mite
  chip it from rounds 260-760, wake after wake (camps never regenerate), clear it at ~600-750 and recapture every
  100-150 rounds. They deal ~90% of its damage; we captured it once in 14 games, tributed 0 in 11, and died ~19
  times a game 35-50 tiles from it, in the gold fight in the west.
- **00ribs, 00fragment**: captures alternate from round ~30 and the deaths are 0-10 tiles from the zone; we lose
  those fights (00ribs: 8.8 of us killed there a game to 3.1, bag gems 42 to 10).

## A/Bs

All against `variants/oc-base25` (= ocean HEAD 9c8a7ae5b), own drafts (`--no-test-draft`), fast runner, real fuel.
Dev set `maps/suites/sets/gemzone-644`: the 724 zone maps of fresh-644000..644116 (29,952 ladder-mix maps), both
sides, 1,448 games. Confirm set `gemzone-664`: 691 maps of fresh-664000..664116, 1,382 games. Built with
`gemzone-tools/make_set.py`.

| Variant | Set | Win % | 95% CI |
|---|---|---|---|
| zone1: 2 guards farm only zone groups, hold stands by it, fight within 8 | dev | 31.7 | 29.4-34.1 |
| zone1, 3 guards | dev | 29.7 | 27.4-32.1 |
| zone1, 1 guard | dev | 44.4 | 41.9-47.0 |
| zone2: zone1 cheap on fuel, no Monolith zones, hold only while a capture is pending or a group is back within the walk + 5 | dev | 40.1 | 37.6-42.6 |
| zone2, 1 guard | dev | 42.5 | 40.0-45.1 |
| zone2, hold only | dev | 41.0 | 38.5-43.6 |
| zone2, zone-only farm only | dev | 41.4 | 38.9-43.9 |
| zone2, neither (chase and contest by the zone) | dev | 48.2 | 45.6-50.8 |
| zw15: farm weighs zone groups x1.5 (all bodies), nothing else | dev | 50.6 | 48.0-53.2 |
| zw20: x2.0 | dev | 49.2 | 46.7-51.8 |
| zw30: x3.0 | dev | 46.6 | 44.1-49.2 |
| zw15 | confirm | 49.6 | 46.9-52.2 |
| zw20 | confirm | 48.5 | 45.9-51.1 |

zw15 pooled: 50.1% of 2,830. Out-of-fuel turns level for zone2 and zw*.

- **Zone-only farm**: farm takes the zone's group however poor its value. 00stampede (traced): our two guards
  claimed the 6-elk group from round 2-3 and poked it alone ~690 turns each; we ended on 0 gems and 7.1k gold, the
  baseline took it at round ~535 with a 3-body crew (1,059 gems, 16.3k gold).
- **Hold**: idle guards cost the gold the baseline turns into shards. With the hold on through every respawn
  (01elk-arena, traced) two guards stood 1,496 turns and we lost 495-1006 on 10.1k gold against 16.7k.
- **Monolith zones** (mut-anvil 7%, Monolith-only 3% in zone1): guards skipped `siege()`. zone2 excludes them.
- **zone1's fuel**: an all-pairs detection and a per-tile scan of every camp member took round 1 to 878k at 100M
  (p99 +167%). zone2's (median-anchored detection, bitboard stands, no round-1 work) left round 1 unchanged.
- **Weight**: the bounds scale with it and the prefilters stay off while it is on, as for the comeback mirror pull
  (`MirrorPull::scaled`); bench.py at 100M: replays identical but for the two zone maps of 26. Heavier weights lose
  on kite maps (gen-shared-gems 45% at x2.0 and x3.0). mut-one-gem read high at every weight (zw15: 64% of 186
  across both sets) and mut-elk-arena low (43%), neither significant.

## Conclusion

In self-play, controlling the zone costs more than it wins, and weighting it is level. The ladder gap is against
teams that take the zone early, which no local opponent does (`bots/fish` reads 23.6% against astraeus), so a gain
there cannot be measured here. `bots/ocean` is unchanged. The two designs are `gemzone-tools/zone-guard.patch`
(zone2) and `gemzone-tools/zone-weight.patch` (zw15), each applying to 9c8a7ae5b.

Open: zw15 is level locally and replays identically off zone maps, so it is a low-risk ladder test; a local Fish
or Mite stand-in that chips 00stampede would make the 00stampede failure measurable.
