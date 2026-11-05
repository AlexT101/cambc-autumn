# Top teams' micro from ladder replays (2026-11-05)

Data: every downloaded ladder replay, 10,850 games (ranked, engine 2.0.0, groups of 2026-10-29 to 10-31), plus 125
post-patch games (engine 3.0.0, 2026-11-05, top 12, still downloading into `replays/ladder-post/`). "newer team" in the
2.0.0 games is us (Pantheon).

Pipeline (all in this folder):
- `decode.mjs` replays every game in the game's own engine and writes each champion input step (walk, attack, cast,
  priority set, shop, sell, ward, channel, lock, teleport, blocked walk, rollover) with the actor's state before and
  after, plus every champion's state at each round start: `replays/micro/{ladder,post}/<group8>-<n>.json.gz`
  (2.8 GB; ~15 games/s on 28 threads). `mklist.py` makes its list from group folders.
- `detect.py` (shopping, priority cadence, blocked walks, channels, kiting), `detect2.py` (lock and stun snipes on
  channels, teleport and ward targets, what each priority value means), `tavi.py`, `prio.py` / `prio_decode.py` /
  `prio_target.py` / `prio_scan.py` (priority bit layouts), `legality.py` (exploit scan), `report.py` (tables).
- Outputs: `out/` (2.0.0) and `out-post/` (3.0.0): `report1.md`, `priority_values.md`, `tavi.md`, `summary*.json`
  with example citations (`<group8>-<n> r<round>`).

## Claims checked

**Mite buying and selling health shards: not seen.** No team sold anything in any game, 2.0.0 or post-patch (no
`Sell item` step, and no shop step raised gold). Selling is Tavi-only (`invalid_action_sell_not_tavi`) and the SDK
has `invalid_action_sell_already_sold`, so it is likely once per turn. What everyone does, Mite included, is buy
Health on spawn while hurt, which heals by the amount bought; buying and then walking off spawn in the same turn
("heal-buy then leave") is 1-4 a game for every top team (Mite 2.2, Fish 1.5, policy wonk 3.9, us 1.0).

**Tavi buying right before attacking: yes, but not banked.** Tavis carry ~8 gold on average and the same when they
hit a champion: nobody hoards gold for a surprise spike. They spend as gold arrives, including mid-turn: kill or
capture gold, buy Strength shards in the field, then hit again after the attack reset (e.g. hello `0448cb5c-4 r736`
121 gold -> 3 Strength, Strength 170 -> 190 before the hit). Turns with a field buy then a champion hit: hello 378,
Mite 195, German Empire 135, policy wonk 133, us 57 (ours are mostly Health/Focus; theirs mostly Strength).

**Priority as a comms channel: four other teams pack data; one is decodable.**
- Ad Astra: bits 24-29 turn order, bits 16-18 a mode, bits 0-15 a tile (`y*W + x + 1`). Mode 5: the champion's
  destination (it reaches it within 30 rounds 94% of the time). Mode 3: the enemy it targets (an enemy stands on the
  tile 64% of the time). So **a visible Ad Astra champion tells us where it is going or whom it is hunting.**
- :3, Supaswag, Nyx and (later games) Univardisty carry payloads that are not tiles (`prio_scan.py`); undecoded.
- Priority reads fail out of sight (our `world.cc`), so these payloads only reach allies in vision, and enemies in
  vision read them too. Ours (claim and support intents in the low 16 bits) is equally readable by them.

**Priority for fight-time turn order (common, worth comparing with ours).** Most teams use a few values keyed on
fight state (`priority_values.md`):
- T1: -1 idle; with an enemy within 4, 1 + missing health / 10, so the most damaged champion acts first.
- Intercontinental Fish and "prism best girl" (identical tables: the same bot): positive (1-4) with an enemy within
  4, negative otherwise, +-100 while channelling.
- NEETCoders: 140-160 within 4 of an enemy, -40 to -60 within 8, 40-60 otherwise; hello: 2095-2099 when carrying a
  big bag in a fight, 97-99 in a fight without gems.
- German Empire and Trzy Kwaterki: priority from health fraction every turn.

## Other micro worth trying

- **Lock sniping:** place a carried lock on an altar the moment an enemy starts tributing there; it cancels the
  channel and blocks that altar for them. hello: 95% of its locks are snipes (0.51 a game, 81 enemy gems caught a
  game); Claudus Maximus 0.74 a game (118 gems); policy wonk 0.32 (104 gems). We place 4.5 locks a game but only
  0.23 are snipes (50 gems).
- **Stunning tributes:** Univardisty stuns tributing enemies 1.15 times a game, Claudus 0.80; most teams 0.2-0.5, us
  0.26.
- **Bush probing:** walk into a tile, get blocked by an unseen unit, then attack that tile in the same turn
  (the block reveals it). print dont int 1142 times in 1400 games; T1, Univardisty, German Empire, us ~300.
- **Wards:** per 1000 turns, German Empire 65, Trzy Kwaterki 59, Mite 43, NEETCoders 35; us 26 (40 post-patch for Mite,
  17.5 for us). The cap is 100 (one per champion every 10 rounds).
- **Recall feints** (start a recall at turn end, cancel next turn): Mite, print dont int, Sponge, policy wonk, SSSA,
  Trzy Kwaterki and us on 2.0.0; post-patch Fish (119 -> 797 per 1000 turns) and Univardisty (101 -> 758) adopted it.
- **Fuel:** Mite and Trzy Kwaterki lose ~6-8 turns per 1000 to fuel exhaustion; most top teams ~0-1.

## Exploits

None found. Across 101.8M turns (2.0.0) and 1.3M (post-patch) no champion walked twice, attacked more often than
1 + its attack resets, cast twice or acted while dead (`legality.py`); no bot error steps, no tribute with 0 gems.
The only "ally damage" on an attack (13 cases) is Fish's (and prism best girl's) Cassi or Issac hitting a Ren while
low, dying to the reflection and taking its partner with it: a Fish weakness, not an engine bug.
