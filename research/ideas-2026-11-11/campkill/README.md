# campkill: champions kill camp groups they then don't capture (2026-11-12)

User, verbatim: "on maps like this one: <viewer link, replay 01a1c56f-d4f4-7157-bbbb-9fd60b307ca3> our champs hit the
middle one gem camp groups but dont capture it (too low value?) they kill but don't capture. perhaps test fixes / guards
to prevent this behavior as it seems like a waste of time."

Base and REF: `variants/charybdis-cb9f86d` (= bots/charybdis, CHANGES 517). Nothing here touches bots/charybdis.

## The replay

Ranked game 2026-11-10 12:30 UTC on `02treasure_box`, BattleCats (A) vs us (B, "stellar best girl"), live v108
(ocean line); we won 1056-206 at round 549. The centre is 16 single-gem-cluster groups (7 gems, 120 health) two tiles
apart round the one altar. We cleared 66 of them; 35 were captured within 8 rounds of the clear, 29 later (up to 170
rounds later), 2 never or by the enemy. Our Cassi did 45 of the 66 clears. Her cycle, rounds 119-170:

- From range she hits cluster X with a basic attack, then her damage spell (200) would overkill X's 90 left, so
  `camp_cast` sends it to another harmless group in range ("A unit cast overkilling a harmless group's last health
  goes to another harmless group in range", combat/abilities.cc). That kills Y outright; X takes three more basics.
- She walks onto X and holds it. The hold needs no turn, so `hold_capture` (economy/capture.cc) hits more groups in
  reach: another basic kill Z, and the spell again.
- After the payout the farm loop takes one of the cleared groups; the rest wait. Kills outpace captures (two per
  five-round hold), so a backlog of cleared, unheld clusters builds up and is worked through later.

So the kills are not a valuation bug ("too low value"): the groups are captured later, mostly by us. They are hits the
bot makes because they cost nothing at that moment.

## How often (charybdis-cb9f86d, 200k, against the Fish and Mite bodies)

Metric (`tools/ck.py`): each clear of ours is an episode; outcome **prompt** (our hold starts within 8 rounds of the
clear and pays us; the clear-to-hold gap is 1-4 rounds in 93% of our clears), **late**, **lost** (the enemy captured
it) or **never**. Cost = our champion turns whose attack or cast damaged the episode's camps, split into turns taken
from a capture tile (free: the holder stands still anyway) and the rest.

| suite | games | our clears/game | non-prompt/game | their attack turns/game | of which free | all our camp-attack turns/game |
|---|---|---|---|---|---|---|
| treasure-box x16 seeds | 64 | 65.0 | 18.9 (gem clusters 16.3) | 48.1 | 24.9 | 791 |
| fresh ladder-v2 (seed 5310001, 256 maps) | 1,024 | 61.0 | 3.6 (clusters 2.6) | 26.7 | 3.7 | 785 |

- On fresh maps the non-free turns are ~23 a game, about 0.5% of ~4,200 champion-rounds; on treasure-box ~23 too
  (fewer rounds). Cluster episodes are concentrated: 24 of the 256 fresh maps (mut-gem-caverns, mut-gem-rush,
  mut-lines, mut-one-gem, mut-gold-rush, gen-shared-gems, some gen-ladder) hold 46% of them.
- Why, from debug-build traces (`D` lines, `tools/why.py`) on those 24 maps + treasure-box (128 games): of the
  non-prompt cluster clears, the killer's next turn was
  - holding a capture and moving on afterwards (`hold_capture`'s free hits): 4.9 a game, 0.4 attack turns a game
    off a capture tile;
  - farming, its claim another group (a one-turn hit or cast in passing, 97% on a group that was never its
    claim): 2.1 a game, 3.3 turns;
  - claim kept, but the enemy took it or a fight, bank or retreat came first: ~3.5 a game, ~11 turns (contests,
    not abandonment);
  - an ally claimed it: 1.0 a game.

## Arms (cause fixes, no constants)

- `ck-cast`: the overkill redirect does not fire when the cast finishes the group (its last live member): finishing
  starts our hold now, where the redirect delays it by the basics left. On treasure-box it moves 3.2 clears a game from
  late to prompt (+22 gems a game captured promptly).
- `ck-pass`: while our claim is a cleared group nobody holds and we are off it and not holding a capture, a ranged
  champion makes no hit in passing (it spends the walk onto the claim), and no hit replaces that claim. Rarely fires
  in charybdis (hold_capture already resets the claim to the held group).
- `ck-both`: both.

## Results against charybdis-cb9f86d (200k, paired games: same maps, noise seeds, sides and bodies)

| CAND | suite | win% CAND / REF | diff (95% CI) | games | games changed | Fish / Mite diff | OOF turns/game CAND / REF | verdict |
|---|---|---|---|---|---|---|---|---|
| ck-cast | heavy: 24 fresh + treasure-box, x16 seeds | 77.8 / 79.4 | -1.62 (+-1.88) | 1,600 | 236 | -2.62 / -0.62 | 0.259 / 0.249 | loses where it acts |
| ck-pass | heavy | 78.8 / 79.4 | -0.56 (+-0.61) | 1,600 | 25 | -0.75 / -0.38 | 0.235 / 0.249 | level/negative |
| ck-cast | fresh f1 | 83.0 / 82.9 | +0.10 (+-0.88) | 1,024 | 21 | -0.20 / +0.39 | 0.030 / 0.026 | no effect |
| ck-pass | fresh f1 | 82.8 / 82.9 | -0.10 (+-0.33) | 1,024 | 3 | 0.00 / -0.20 | 0.028 / 0.026 | no effect |
| ck-both | fresh f1 | 83.0 / 82.9 | +0.10 (+-0.88) | 1,024 | 21 | 0.00 / +0.20 | 0.032 / 0.026 | no effect |
| ck-cast / ck-pass / ck-both | treasure-box | 87.5 / 85.9 / 85.9 vs 87.5 | 0 / -1.6 / -1.6 | 64 | 4 / 3 / 5 | | 0 | no effect |

Mechanism on the heavy suite (cluster groups, per game; base / ck-cast / ck-pass): prompt clears 76.0 / 77.2 / 76.0,
gems captured promptly 305 / 311 / 306, late 7.7 / 7.1 / 7.7, lost 3.1 / 3.1 / 3.1, attack turns on non-prompt
episodes 35.7 / 35.1 / 35.9 (12.5 / 12.7 / 12.6 of them from a capture tile). ck-cast does what it says (+1.2 prompt
clears, +6 gems a game) and still does not win: the redirected kill was worth about as much as the rounds it cost.

No fresh-map fgate was run: on fresh maps the arms change 0.3-2% of games, so the expected fgate effect is a few
hundredths of a point, far below what 300k games resolve, and where they do act (the heavy maps) they read negative.

## Verdict

The kills are worth it or free: hold-time hits cost no turn, passing hits are one turn each and the groups are mostly
captured later by us; a pre-cleared cluster loses nothing (its respawn clock starts at payout either way, and the enemy
would clear 120 health in a turn or two). The one real delay (the cast redirect) is not a loss either: removing it loses
on the maps where it acts. Closed; no candidate. Nothing went live.

## Files

- `ck-cast.patch`, `ck-pass.patch`, `ck-both.patch` against `bots/variants/charybdis-cb9f86d`; variants
  `bots/variants/ck-cast`, `ck-pass`, `ck-both`.
- `tools/`: `ck.py` (episode metric), `why.py` (D-trace join), `story.py` (one game's episodes), `paired.py`,
  `mksuite.py` (mechanism suites: map copies, a body noise seed each), `mech.sh`, `dbg.sh`, `m1.sh`, `m2.sh`.
- Fresh maps: mapgen `suite --seed 5310001 --mix ladder-v2` (in `~/tmp-offload/campkill/gen/`); suites under
  `replays/campkill/` (tb, f1, hv, hv16); extracts under `~/tmp-offload/campkill/ext/`.
