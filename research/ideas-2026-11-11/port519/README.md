# comms + psafe-a on charybdis 519 (port519, 2026-11-12)

The combo programme's recommended stack ([combo/README.md](../combo/README.md): comms slots cm2-k3 + psafe-a, read on
517) ported onto `variants/charybdis-p3` (= bots/charybdis, CHANGES 519) and read against it at 100k on fresh maps no
gate had played. Nothing here touches `bots/charybdis`.

## Port

`c519-cmps.patch` and `c519-ps.patch` are against `bots/variants/charybdis-p3` (from inside a copy of it, or in
`bots/charybdis`, `patch -p2 < PATCH`). `../combo/cbx-cmps.patch` and
`cbx-ps.patch` applied to p3 with line offsets only; the code is unchanged from the 517 arms.

Overlap with 518-519, checked hunk by hunk:
- **Comms and crew:** 518-519 do not touch `comms.cc`, `comms.h`, `crew.cc` or `capture.cc`. The `main.cc` hunk
  (send gets `now`) sits on 516's `moved` test, unchanged in 519. 518's H1 (spin out under 100 fuel before
  `end_turn`) runs after `comms send` and does not change what is sent. 519's H2 (an unseen dead ally's priority)
  does not reach the claim slots, which post only living allies' claims.
- **psafe-a:** 518's A1 and 519's A2 are about the enemy's winning tribute: locks that spare our winning tribute only
  if it lands first, combined enemy wins (`enemy_tributes_win`), and which channel to stun. 518's B1 is Marcella's stop
  of an enemy game-ender. None of them covers our own Prism's winning channel, which is what psafe-a guards (go home
  to heal before starting it, while the enemy's clock runs past the trip). `finish_heal` reads `winning_bag`,
  `strike_of`, `recall_landing`, `tribute_turns` and `endgame_margin`, all with their 517 signatures; 518's B3/D1
  refinements to the strike model flow into its burst estimate unchanged. Its `finish_lead` guard counts visible
  enemy bags as carried, so A2's combined enemy wins are already within its clock; nothing is doubled up.

So the port is exact. The single-part arm `c519-ps` (psafe-a alone) was run alongside to see which part carries; cm's
share is the paired contrast `cm+ps - ps`.

## Maps

Pool batches 63-74, grown here from mapgen seeds 2448000-2448129 (`--mix ladder-v2`, 130 seeds, 32,794 of 33,137
maps new to the pool; the pool now holds 196,028, so batches 0-75 are whole; 75 is unplayed). No gate had played them.

## Results

`tools/fgate.py CAND variants/charybdis-p3 --fuel 100000 --first-batch 63 --max-batches 12 --ci 0`, unmetered Flp4
and Mt3q bodies, both sides, fastrunner. `run.sh` is the whole chain; `reads/` holds the pooled reads
(`../chyport/report.py`) and `contrast.py`'s paired contrasts.

Results against charybdis-p3 (519):

| arm | win% (95% CI) | games | Fish | Mite | OOF a game (REF 6.675) | LLR high / low | verdict |
|---|---|---|---|---|---|---|---|
| **c519-cmps** (cm + ps) | **50.31 (50.05-50.57)** | 245,760 | +0.23 ±0.35 | +0.40 ±0.38 | 6.728 (+0.8%) | -4.50 / +6.30 | **ZONE** |
| c519-ps (ps alone) | 50.24 (50.06-50.41) | 245,760 | +0.21 ±0.24 | +0.26 ±0.25 | 6.732 (+0.9%) | -12.25 / +11.42 | ZONE |
| cm given ps (paired) | +0.08 ±0.25 points | 30,720 maps | +0.01 ±0.34 | +0.14 ±0.38 | | | no detectable gain |

No failed games and no early losses. Ladder side read: cmps +0.62 ±1.15, ps +0.21 ±0.78.

Beside the 517 read (batches 51-62): cm+ps +0.27 ±0.26, ps +0.17 ±0.18, cm given ps +0.10 ±0.25. The parts hold
their size on 519: psafe-a grew a little, cm stayed small.

- **psafe-a carries the stack.** Its read is tight (CI 50.06-50.41, low SPRT +11.4) and it is the larger, more
  consistent part on both bases.
- **cm adds about +0.1 on both held-out reads**, never distinguishable from zero (+0.10 ±0.25 on 517, +0.08 ±0.25
  here). It is the larger code change (the shared-bytes layout).
- **Fuel is level.** Both arms run ~0.05 more out-of-fuel turns a game than 519 (+0.8-0.9%), cm adding nothing over
  ps. 517's read showed the same (+0.09-0.10). That is far from gp-race's +0.6 (+10%).

## Recommendation

Both are ZONE reads (above 50, below the 50.5 ACCEPT bar), so taking either is a judgement under the zone rule.
- **c519-cmps** has the higher point estimate (+0.31) and both parts are positive on both bases, with stated
  mechanisms and level fuel. Take it if the judgement is to take the best expected value.
- **c519-ps alone** is the conservative choice: a small, self-contained change (one guard in the tribute path and an
  enemy tribute-rate record) with the tightest evidence, +0.24 (50.06-50.41).

Either goes to charybdis only on the user's and teammate's decision, with the usual live pairing before.

## Files

- `c519-cmps.patch`, `c519-ps.patch`: against `bots/variants/charybdis-p3`. Variants `bots/variants/c519-cmps`,
  `bots/variants/c519-ps`.
- `run.sh`: map growth, both gates, the reads. `contrast.py`: the paired contrasts (from `../combo/additive.py`).
- Logs and maps: `~/tmp-offload/port519/`. Runs: `replays/ab/fbe501-c519-{cmps,ps}-{Flp4,Mt3q}-m2560b0{63..74}-fuel100000`
  and the REF's `fbe501-charybdis-p3-...-fuel100000`.
