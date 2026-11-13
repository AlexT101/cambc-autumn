# C2 `duel`: Prism duel discipline from one matchup model

You implement one candidate for the RHEA macro programme on our Cambridge Battlecode bot charybdis (C++). Work only in
`/home/ubuntu/wt/mx-rhea` (git worktree; never push, never touch /home/ubuntu/cambc-autumn or other worktrees; do not
commit, the orchestrator does). Read `AGENTS.md` first, then `cambc-rules.yaml` (engine-verified rules; the Prism, stun,
abilities, turn order and tribute sections matter most), and the C++ API (`docs/api/cpp.md`, `sdk/cpp/cambc.h`) as needed.

## Setup
`cd /home/ubuntu/wt/mx-rhea && ./copybot variants/chy-ref variants/c2-duel`. Edit only `bots/variants/c2-duel/src`.
Never edit `bots/variants/chy-ref`. Leave `draft/` and emblem choices alone (off limits).

## Evidence (charybdis mirror, 1,020 games; the Prism duel decides the game: first Prism death loses 92%)
- Hunts: when our stronger Prism S (Focus >= 1.2x and hp >= 60%) sees the weaker enemy Prism V at 5-9 tiles
  (4.2 times a game), S closes within 4 only 33% of the time. When it closes, V dies 17% (Focus ratio 1.2-2),
  31% (2-3), 53% (3+); S dies < 1%. V's death rate rises with net bodies near V (ours minus theirs within 8):
  8% at -2, 13% at 0, 19% at +1, 26% at +2; V that reaches its own spawn dies 2%. S on farm closes only 31%.
- First Prism deaths: 35% are a weaker Prism that met the stronger one while farming (it had usually seen it, and
  started retreating 2 rounds after first contact; died a median 8 rounds later); 20% a stronger Prism that was
  outnumbered (enemy-minus-ally bodies >= +1 in 75%, Focus edge small); 21% branch E: our weaker Prism with a median
  528-gem bag running "whatever the risk" (combat/fight.cc `game_ender` / `stop_game_ender`) at an enemy carrying a
  winning bag that is mostly NOT tributing (retreating or walking); the bag goes to the killer and the team wins 7%.
  game_ender counts a visible non-channelling carrier with pair_gems >= need (off its spawn) as a game-ender.

## Design: one model, three uses
1. `DuelEdge duel_edge(const World&, const ChampionBelief& ours, const ChampionBelief& theirs)` (new file
   `combat/duel.{h,cc}`, add to `unity.cpp`), from what is visible (Focus, health + shield, max health, the damage
   factors already kept on beliefs: dealt / taken, Durability, Skirmish; and for ourselves the exact own reads):
   the rounds each side needs to kill the other with its stun cycle (Prism: stun 1.5 x Focus then ground 1.0 x Focus,
   plus basic Strength a turn; a stun costs the target its next turn), counting which slots are ready now
   (`ready_round`). Express it as `ours_kills_in` / `theirs_kills_in` (turns) and a verdict: `favoured` (we kill
   first with margin: ours_kills_in < theirs_kills_in), `disfavoured`, or `even`. Add a body count helper:
   net bodies near a tile (our living visible allies within 8 minus visible / tracked enemies within 8, Cassi and
   Issac as one body each). Reuse existing helpers (safety.h Strike / one_turn_reach, champions.h facts, the fight
   code's damage functions) rather than new formulas where they exist; keep it O(1) per pair.
2. Hunt (our Prism only): when an enemy Prism is visible, we are `favoured`, net bodies near it >= 0, it is not on
   or within a step of its spawn region (`map.near_enemy_spawn` or similar), and we are not tributing a winning bag:
   chasing it is worth its bag x (1 + the enemy's premium if one exists; else plain gems) + kill gold, over the
   rounds to close (distance - 4). Feed that into the existing chase decision (bot.cc `chase_with_guard`, `prey`,
   combat/ chase pricing) so it can beat the farm, rather than adding a separate branch; the step guard and safety
   checks keep applying.
3. Spacing (our Prism only): when an enemy Prism is visible (or seen within the last few rounds, its possible tiles
   bounded) and we are `disfavoured`, the farm and hold choices treat tiles within its two-turn stun reach (its stun
   reach + 1 walk + 1 for a turn-order double move; derive from Strike / ready_stun_reach rather than a constant) as
   off limits for the job (skip or heavily price groups whose work tiles lie there), and the retreat/want_home
   decision fires on sight within that reach + 1 rather than after the fight starts. When `even`, require net bodies
   >= 0 to stay. Nothing changes when no enemy Prism is in sight.
4. Game-ender restraint: in `game_ender` / `stop_game_ender` (fight.cc), a visible enemy carrier that is NOT
   channelling a tribute only counts as a game-ender for us when (a) our bag at stake (bag_at_stake) is small
   (<= max(40, its bag / 3)), or (b) we are a Prism `favoured` against it (or it is not a Prism and our local bodies
   are >= 0), or (c) its tribute could land before we can reach stop range once it starts (it is within tribute
   range of an altar and our intercept steps exceed its tribute turns). Otherwise our body shadows: it keeps within
   intercept range of the carrier's likely altar but outside the carrier's (and its escort's) two-turn reach, and
   farms or holds as usual if it can do so there. Channelling enders are unchanged.
5. Debug lines (debug builds only): `DUEL <round> <handle> <enemy handle> <verdict> <ours_kills_in> <theirs_kills_in>
   <net>` when the verdict changes for a visible enemy Prism, `HUNT ...` when the hunt drives a chase, `SPACE ...`
   when spacing skips/retreats, `ENDR ...` when the restraint turns a game-ender into a shadow.

Make two copies when done: `variants/c2-duel` (all four pieces) and `variants/c2-duel-ns` (the same without piece 3,
spacing), so the orchestrator can ablate the piece most like earlier losing "Prism avoids Prisms" designs.

## Build, audit, smoke
- Build: `cd /home/ubuntu/wt/mx-rhea && source ~/venv/bin/activate && cambc build bots/variants/c2-duel`.
- When done, spawn ONE read-only auditor subagent (general-purpose), told explicitly not to edit any file. Give it
  this brief and the diff (`diff -ru bots/variants/chy-ref/src bots/variants/c2-duel/src`); ask it to check against
  the design and cambc-rules.yaml: kill-turn arithmetic (stun timing, exclusive casts, cooldown 8, shields,
  damage factors), turn-order assumptions, Cassi/Issac counting, the E restraint's cases, stale beliefs of unseen
  enemies, fuel blow-ups. Fix what it finds.
- Smoke each copy: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-rhea && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c2-duel variants/chy-ref --no-test-draft --fuel 200000 --name mx-rhea-c2-smoke`
  (256 ladder games; also `-ns` with `--name mx-rhea-c2ns-smoke`). Required: no failed games, no DRAFT-UNFINISHED /
  PLAN-CHECK, out-of-fuel turns reported for both sides. The smoke win rate is noise (±6): do not tune on it.
- Optional trace check: a few hundred debug games on `maps/suites/mx-rhea/study` (`--suites maps/suites/mx-rhea/study
  --debug`) to count DUEL / HUNT / SPACE / ENDR lines a game. No large A/Bs; the orchestrator runs them.

## Stop condition and report
Stop when both copies build, auditor findings are fixed and both smokes pass. Report concisely: files and functions
changed, design decisions you had to make (e.g. thresholds and how you derived them), smoke results (win %, OOF both
sides, failures), trace counts if run, and anything suspicious. No further experiments.
