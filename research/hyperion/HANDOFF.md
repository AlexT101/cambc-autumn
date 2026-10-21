# Handoff: hyperion combat merge, 2026-10-21 (session 3)

Goal set by the user: merge hyperion's combat logic into ONE combat system (unification first), then cut out-of-fuel
(OOF) turns. A win-rate drop is a logic flaw to diagnose, not a reason to revert. TODO's "evidence to weigh" list
(step_guard, pursuit, threat_strike, sieges, kite) is not binding: rules should collapse into the shared pieces.

## Where things are

Branch `claude/dazzling-mccarthy-4kawix` (pushed). Tags were local only, so use the shas:

| Point | sha | Contents | A/B (582 games: ladder + maps/gen, both sides) |
|---|---|---|---|
| main | 55e0bdc | session start | |
| w0 | 2b7ea7e | orch/removals, add_unseen fix, Phase tracing (`debug_phases`, ab.py `--phases`) | 48.6% vs main |
| w1 | 36cf487 | Safety tile table (one unseen rule, exit_rounds), fight memo across invalidate, reobserve after a ward | 48.5% vs w0, OOF -11% |
| w2-merged | a9db454 | one fight engine `engage()` (FightKey memo, dominance), lazy `Safety::guarded()` replaces step_guard, want_home/prey/search on one verdict, unseen_bound | 52.4% vs w1 at 100M fuel; OOF +35% at the real budget |
| **w2fix** | **4280fa0** | + fuel fix (sim exits E1/E2, cut fights memoised, guarded() asked of the search's pick only, P1A, prey escorts, prey <=1 new fight per call) | **49.7% vs w1 (level): last known-good** |
| w34 | 604ca30 | + waves 3+4 (w4-int) + raw engine reads (rawbind) | **45.7% vs w2fix, OOF +86%** |
| tip | 2d1bb23 | w34 + records | |

Details: research/EXPERIMENTS.md (one entry per wave), research/hyperion/CHANGES.md 53-58,
research/hyperion/COMBAT-MERGE.md (plan, wave sections, W3-4 ownership table), OOF-ANATOMY.md.

## First job: waves 3+4 regress

- W3: retreat and chase are modes of the one strike search (prepare/price split, flee pricing with camp exit rule,
  caps C1 4, flee nodes 8, escape tightenings 3+3); flee_camps, danger(), threats_near, Hazard, dash_away deleted.
- W4: one mend() shield/heal valuer, the search owns casts (Valued/strike_after), recall/tribute/turn order on
  idle_turns and Safety's tile table, a "ghost" charge for hits from unseen enemies, census cleanups (take_hop safety,
  Heart of Ruin landings via landing_clear + tile worst, one Ren-retaliation helper).
- Known fuel problem: flee searches average ~24k (p99 ~62k) against a 12k/40k target. ~370 fuel per flee end tile is
  spent on setup before any row is read (~230 setup, 50 gain loop, 90 heap), so a 46-tile flee costs ~17k up front.
  Caps cannot fix that; fewer end tiles (only tiles that make progress or cut danger) or cheaper setup can.
- Not yet known: whether the 45.7% is fuel or logic. Run `py tools/ab.py <sha 604ca30> <sha 4280fa0> --suites
  ladder,gen --threads 4 --fuel 100000000` (logic only) and attribute the extra OOF turns (SRCH lines carry mode and
  fuel; a real-budget bench with `debug_phases` on gives paths via tools/fuel/oof_phases.py). Also suspect chase
  reprices, idle_turns/ghost on recall/tribute, mend.
- If it cannot be fixed: revert the w4-int merge (55adef3) but keep the raw bindings. rawbind was merged after it and
  touches W3/W4 code, so re-porting rawbind onto 4280fa0 may be cleaner than a revert (the port is mechanical:
  `claude/happy-franklin-nltty2` 3b2edbd; check byte-identity on 6-8 chosen games, not the full bench).

## Then

- Wave-2 logic fixes: first version 47.9% vs w2fix (OOF +18%). Attribution: "prey skips targets that leave us low"
  and want_home leaving on falls-only fights cost wins; exposed() ally check and guard_rule = lost || falls cost fuel;
  "fighting_allies drops leaving allies" and the ally check helped. The revised branch `lf2` (6be102c) and
  `w2/logicfix` were local only and are probably gone; redo from this description if needed.
- Wave 5 (designed, not built):
  - W5-A (event-driven sim core) was measured and rejected: saving bound 14-19% of sim fuel, under the 30% bar.
  - W5-B: outmatched/pack zone only when the here-verdict is not clean; the zone a no-go for carriers only; a
    pack_guard capped at 2 sims a turn. Ship only zone + pack_guard together (zone alone recreated walk-in deaths).
    The W2 loss diagnosis found outmatched causes 45% of retreats, 75% of them on turns the stand fight was won.
  - W5-C: avoid() stays the one routing board (camps + visible reach + unseen fields; retreat_home reads it);
    guarded() gains a "this tile kills us and is worse than here" rule; threat_strike becomes Safety-internal;
    enemy_area/square model deleted.
- Remaining OOF vs w1 (on w2fix): chase/prey escort fights (+380 turns per 582 games), farm's guarded() walks (+200),
  want_home sims (+70). The search's grow is the biggest single OOF location; World::track costs ~1.6k a turn.

## Working notes

- Setup: `pip install cambc`; its downloader rejects the proxy CA, so fetch wasi-sdk-33, cmake-3.31.8 and ninja-1.12.1
  with curl into ~/.cache/cambc/ (wasi-sdk-33/, cmake-3.31.8-linux-x86_64/, ninja-1.12.1-linux-x86_64/ninja). Add a
  `py` -> python3 shim.
- 4 cores: one ladder+gen A/B takes ~15 min; serialise every multi-game command with `flock /root/cpu.lock` and
  `--threads 4`. Subagent Bash calls stop at 10 min, so run A/Bs from the orchestrating shell in the background.
- run_batched/ab games are debug builds, so debug tags (SRCH, MEMO, VERDICT, SIMS, GUARD-RETRY, MEND, ...) are in
  team-*.stdout inside each replay zip. `--phases` costs ~1% fuel: use it for attribution, not for win rates.
- The 16-game bench cannot judge OOF (±20, and one map swung 74 -> 336); use paired A/B OOF counts.
- What worked: an interface commit with byte-identical stubs per wave, builders owning disjoint functions, an
  adversarial review per branch, and a cross-branch trial merge before integration (it caught the prey-escort flaw
  that the averaged 100M A/B hid). What failed: deleting fuel gates without making the work cheaper (W2, +35% OOF)
  and integrating W3 after its fuel test failed.
