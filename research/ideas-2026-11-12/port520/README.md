# psafe-a (and comms + psafe-a) ported to charybdis 520 (port520, 2026-11-12)

The port519 stack ([port519/README.md](../../ideas-2026-11-11/port519/README.md)) moved onto `variants/chy-life`
(= bots/charybdis, CHANGES 520). It was read against chy-life at 100k on fresh maps no gate had played. Nothing here
touches `bots/charybdis`.

**Recommendation: take `c520-ps` (psafe-a alone) into charybdis.** It reads 50.27% (50.11-50.44) of 245,760 games
against 520. Comms adds nothing on 520 (-0.07 ±0.24), so leave it out. The patch is `c520-ps.patch`; from inside
`bots/charybdis`, run `patch -p2 < .../c520-ps.patch`. It dry-runs clean on bots/charybdis as of 0c34a2613. It is
queued live at priority 89 as `variants/c520-ps`.

## Port

`../../ideas-2026-11-11/port519/c519-ps.patch` and `c519-cmps.patch` applied to chy-life with no conflicts: two
`fight.cc` hunks moved by one line, and the rest applied exactly. The ps code is byte-identical to c519-ps's.
`patch` left `fight.cc.orig` backups in both variants. They were never compiled, and I removed them after the gate and
before the queue; the mask dry run was repeated on the clean copy.

Overlap with 520, reasoned from both mechanisms:
- **Its own fall (fight.cc `stand_lost_at`, guard.cc `step_guard`).** 520 makes the Prism leave a stand, and keep off
  a tile, where it would fall even if the team wins the fight there. psafe-a's `finish_heal` is a separate term OR'ed
  before `stand_lost_at` in the retreat test. Its trigger is narrower: the winning bag, below one round of every
  living enemy's best strike, and the enemy's clock longer than the trip home. Its effect is wider: it also refuses
  to *start* the tribute (`can_tribute_safely`, bank.cc), which 520 never reaches. Both send the Prism home, so where
  both fire the result is the same, and neither changes the other's inputs. No resolution was needed.
- **Health shards first (shop.cc).** A sturdier Prism stands above `finish_heal`'s burst line more often, so psafe-a
  fires less. That is the intended interplay (more health is what the heal buys), not a conflict.
- **Carry-pick fuel test (farm.cc, capture.cc, pathing).** It is unrelated to both parts. The comms hunk in
  `capture.cc` (`recent_tile`'s slack) sits apart from 520's `prism_eta` and `leave_for_prism` edits.

## Maps

- Pool batch 75 was unplayed.
- Batches 76-86 were grown here from mapgen seeds 2471000-2471129 (`--mix ladder-v2`, 130 seeds; 32,744 of 33,118
  maps were new to the pool). The pool now holds 228,772 maps, so batches 0-88 are whole and 87-88 are unplayed.
- No gate had played 75-86.

## Results

The gate was `tools/fgate.py CAND variants/chy-life --fuel 100000 --first-batch 75 --max-batches 12 --ci 0`, against
the unmetered Flp4 and Mt3q bodies, both sides, on fastrunner. `run.sh` is the whole chain. The pooled reads come from
`../../ideas-2026-11-11/chyport/report.py`, and `contrast.py` gives the paired contrasts.

Results against chy-life (520):

| arm | win% (95% CI) | games | Fish | Mite | OOF a game (REF 6.752) | LLR high / low | verdict |
|---|---|---|---|---|---|---|---|
| **c520-ps** (ps) | **50.27 (50.11-50.44)** | 245,760 | 50.29 (50.06-50.52) | 50.26 (50.02-50.50) | 6.811 (+0.9%) | -12.04 / +13.58 | **ZONE** |
| c520-cmps (cm + ps) | 50.20 (49.95-50.45) | 245,760 | 50.06 (49.73-50.40) | 50.34 (49.98-50.70) | 6.804 (+0.8%) | -6.52 / +5.06 | ZONE |
| cm given ps (paired) | -0.07 ±0.24 points | 30,720 maps | -0.22 ±0.33 | +0.08 ±0.36 | | | no gain |

There were no failed games and no early losses. The ladder side read is ps +0.10 ±0.80 and cmps -0.72 ±1.09.

psafe-a on its three bases, held out each time: 517 +0.17, 519 +0.24 (50.06-50.41), 520 +0.27 (50.11-50.44). It held
its size on top of 520's Prism-survival change, which it partly overlaps in purpose. On 520 comms is level or slightly
negative (+0.10 on 517, +0.08 on 519, -0.07 on 520), never distinguishable from zero.

### Mechanism

`mech.py` (from `../../ideas-2026-11-11/prismsafe/`) was run on 5,120 games a bot: pool batch 0 parts p0-p3 (1,280
maps, both sides, both rt bodies), 100k, with replays. A winning bag means the Prism's gems plus our score reach 1,000.

| | chy-life | c520-ps | c520-cmps |
|---|---|---|---|
| games with a winning bag | 2,619 | 2,611 | 2,641 |
| Prism deaths carrying it | 115 (111 games, 4.2%) | **83 (80 games, 3.1%)** | 75 (74 games, 2.8%) |
| winning-bag games won | 95.9% | 96.3% | 97.1% |
| big-bag (40+) Prism deaths a Prism game | 0.196 | 0.189 | 0.206 |

- psafe-a cuts the winning bags lost by about 28% on top of 520.
- On REF's 2,619 winning-bag games, 111 bags were lost under REF and 66 under c520-ps.
- These 5,120 games are only a mechanism read. Their win level (ps -0.04 points, cmps -0.14) is noise at this size.
- The paired net-wins split by REF's winning bag is biased by selecting on REF's own trajectory, so it is not read.

## Recommendation

**c520-ps.** It is a ZONE read with the tightest evidence: the CI is above 50 and the low SPRT is at +13.6. It is the
same small, self-contained change on all three bases (a guard in the retreat and tribute paths, plus an enemy
tribute-rate record). It has a stated mechanism, shown directly (fewer winning bags lost), and level fuel (+0.06
out-of-fuel turns a game).
- c520-cmps is no better and carries the larger shared-bytes change, so leave it out.
- chy-life itself is the fallback if live disagrees.

For the teammate: apply `c520-ps.patch` to bots/charybdis (`patch -p2` from inside it). It touches `bot_parts.h`,
`combat/fight.cc`, `economy/bank.cc`, `model/world.{cc,h}` and `params.h`. `params::finish_heal`, `finish_lead` and
`finish_no_prism` are the guard's switches.

## Files

- `c520-ps.patch`, `c520-cmps.patch`: against `bots/variants/chy-life`. Variants are `bots/variants/c520-ps` and
  `bots/variants/c520-cmps`.
- `run.sh`: map growth, both gates, reads, mechanism games. `contrast.py`: the paired contrasts. `mech.py`: the
  winning-bag metrics.
- Logs, maps, extracts and the mask dry-run workspaces: `~/tmp-offload/port520/`. Runs:
  `replays/ab/fbe501-c520-{ps,cmps}-{Flp4,Mt3q}-m2560b0{75..86}-fuel100000` and the REF's
  `fbe501-chy-life-...`; mechanism runs `replays/ab/p520-mech-{ref,ps,cmps}-{Flp4,Mt3q}`.
