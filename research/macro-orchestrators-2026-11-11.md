# Macro refactor programme, 2026-11-11 (eight independent orchestrators)

Eight orchestrators each owned a macro refactor of `bots/charybdis` (19:00-23:00 UTC), in their own worktree from `81fc6f968`, without seeing each other's work. Rules: no draft or emblem changes; every A/B against a frozen copy of charybdis at 2x fuel (`--fuel 200000`), own drafts, 10k+ games on fresh `ladder-v2` suites (dev 5,120 maps, holdout 1,280 maps, seeds 81000-81199), confirmed on holdout and ladder/gen/gen-s1. Target 60%; none came close.

| Codename | Notes | Bot change (diff vs `81fc6f968` in `patches/final-charybdis.diff`) | Result vs charybdis, 2x fuel |
|---|---|---|---|
| ATLAS | [macro-atlas](macro-atlas/NOTES.md) | six safety/fight/retreat fixes (stun turn order, fight sim targets the asker, stun-then-cast lethality, retreat steps over casts, cooldown-return reach) + press a disarmed enemy; fuel floors | **51.8% of 19,200** (held out 52.2% of 8,960); **49.7% of 7,680 at 100k fuel** |
| BOREAS | [macro-boreas](macro-boreas/NOTES.md) | enemy Prism stun-burst lethality in our Prism's guard, steps and retreat | 50.7% of 18,688 |
| CALYPSO | [macro-calypso](macro-calypso/NOTES.md) | none | all ~25 designs/probes at or below 50.5% |
| DELPHI | [macro-delphi](macro-delphi/NOTES.md) | none | all at or below 50.3% at 10k |
| EREBUS | [macro-erebus](macro-erebus/NOTES.md) | none | 8 designs, 34 probes, none above level |
| HELIOS | [macro-helios](macro-helios/NOTES.md) | port of ocean 507 (comms slots carry teammates' tiles) | 50.25% of 29,440 (neutral) |
| ICARUS | [macro-icarus](macro-icarus/NOTES.md) | none | best ~50.1% of 24,320 (Monolith crew) |
| JANUS | [macro-janus](macro-janus/NOTES.md) | none | 8 candidates at 49.2-50.7% |

Every tested variant's diff is in its programme's `patches/`.

## What the programmes agree on (charybdis mirror)

- The Prism duel decides the game: the team whose Prism dies first loses 86-90%; the Prism makes over half the kills; the bigger bag wins nearly every Prism-on-Prism kill.
- The Prism's hoard is worth more as Focus than as score: every earlier-banking rule lost (1-21 points). Cancelled late tributes are the price of the weapon.
- Farm time is the binding resource: restricting where allies farm (pack, squad, escort, convoy) lost 5-13 points, roughly in proportion to how often it bound; caution that cut deaths cost as much in farm and position.
- Ablation values: crew operations ~20 points, Prism trips home ~17, chasing ~6, Willow/Prism pairing ~3. Most other subsystems are within noise.
- One-knob changes, soft re-pricing, shared-information records (they fit the 8 bytes in under 30% of games on 5-6 body teams) and coordination modes (rally, hub, gank, crew assignment, Monolith siege, game-ender convergence) all read level. The only gains were model fixes where bags are lost, about +0.5 each.
- Several programmes concluded that charybdis against itself is near an equilibrium and macro gains may need a non-mirror opponent (the teacher) to show.

## Open leads named by more than one programme

- A fuel pass on ATLAS's checks so its 2x gain survives at 100k.
- Compacting the comms layout before adding shared records.
- A Prism support request for teams without a healer (the support mailbox runs only for Prism+Willow).
- Re-planning the recall/spawn cycle end to end (~27% of alive time; half of recalls start at 90%+ health).
- Cassi & Issac cohesion under threat (66% of pair deaths with the bodies 6+ apart).
