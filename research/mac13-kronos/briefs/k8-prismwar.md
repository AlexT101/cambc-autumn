# Brief k8: a Prism-war doctrine (avoid when weak, hunt when dominant) - three variants

You are implementing a macro change to the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md`, `cambc-rules.yaml` (Prism, stun, abilities, death,
respawn, vision) and the two studies `research/mac13-kronos/s3/README.md` (the Prism war) and
`research/mac13-kronos/s2/README.md` (kill conversion). Work ONLY in `/home/ubuntu/wt/mac13-kronos`; do not touch
`/home/ubuntu/cambc-autumn` or other worktrees; do not commit. Never edit `bots/variants/chy-ref` or
`bots/charybdis`. Off limits: `src/draft/`, emblem choices. Each variant: `./copybot variants/chy-ref
variants/NAME` (never copy `.cambc/`), then the edit.

## Why
The game is decided by the Prism war: the Prism's carried gems give +1.5 Focus each (banking them early loses 15-22
points), 75% of Prism deaths are by the enemy Prism, the first Prism death decides 91% of games, a dead champion is
gone 60 rounds and its killer takes its whole bag. From s3 (1,024 mirror games):
- **The weak Prism walks into the strong one.** In encounters with a power ratio (Focus x health) >= 1.5, the weak
  Prism closed the distance in 50% (and died within 20 rounds in 57% of those); in farming encounters its farm
  target lay within 4 tiles of the strong Prism in 54% (within 8 in 79%). It saw the strong Prism 75% of the time.
- **The dominant Prism does not convert.** With Focus >= 2x the enemy Prism's held 10+ rounds, the dominant team
  wins 96% when its Prism later kills the weak one, 57% when it never does (406 of 719 games). The dominant Prism
  farms 62% of its mid-game rounds, sees the weak Prism 17% of rounds, and its engagements end at the chase gate
  in 63% (`preyable`, `combat/fight.cc:747`: a healthy target on its own ground with no bag is refused; the weak
  Prism is on its own ground 97% of those times). It knows where the weak Prism is only while it sees it
  (`params::track_horizon` 3 rounds).

## Design
Define, in one well-commented place (a small header or `combat/` helper), a duel model between two Prisms from
the rules, using the state the bot already keeps (our own stats; the enemy Prism's last-seen Focus, health, max
health, and gems/bag): a Prism's two-turn burst is stun 1.5 x Focus then ground 1.0 x Focus (the stun removes the
victim's next turn); apply the damage modifiers the code already models (Durability, shields) if the helpers exist.
- `prism_dominant_over(e)`: our burst covers its current health AND its burst does not cover ours (we win the
  exchange whoever starts).
- `prism_outmatched_by(e)`: the reverse (its burst covers ours and ours does not cover its).
Use the enemy Prism's latest belief; if it has not been seen for a long time its Focus may have grown: add 1.5 Focus
per gem it can have gained since (use what the code believes about its bag; if there is no such belief, use the
last-seen value) - keep it simple and say what you did.

1. **Avoid (variant `k8-avoid`).** While our Prism is outmatched by a living enemy Prism seen within the last
   `cambc::constants::capture_time` rounds (a capture's hold: what our Prism commits to at a group), our Prism's farm
   treats every group whose tiles lie within (enemy Prism's reach + the rounds since the sighting) of that sighting
   as dangerous: exclude it from our Prism's farm choices unless no other group is valid (then the cheapest-risk
   one as today). Reach = the Prism's cast range plus one step (the stun reaches 4, the ground spell 5: use the
   ability range constants). Do it inside the farm's existing machinery (where groups are skipped or weighted per
   champion, e.g. near the exposure / safety tests in `economy/farm.cc`), not as a new branch. Only our Prism
   changes behaviour.
2. **Hunt (variant `k8-hunt`).** While our Prism is dominant over a visible (or tracked) enemy Prism, `preyable`
   does not refuse that enemy Prism for being healthy on its own ground with no bag (the clause at
   `combat/fight.cc` ~756-759); every other test (enemy spawn edge, the fight sim, `escapes`, `pack_covers`, the
   chase verdicts) still applies. Also, for the enemy Prism only, keep its tracked belief a little longer when our
   Prism is dominant: up to `capture_time` rounds instead of `params::track_horizon` (3), so a chase is not dropped
   the moment it steps out of sight (find how `track_horizon` is used in `model/world.cc` ~2397 and make the
   longer horizon apply only to the enemy Prism and only for our dominant Prism's reads; if that is impractical,
   skip this half and say so).
3. **Both (variant `k8-war`)**: 1 + 2.

## Stop condition
1. All three build (release). 2. Spawn ONE read-only auditor subagent (tell it explicitly not to edit anything) to
check the diffs against this design and the rules (the duel model's arithmetic, no change when no enemy Prism or no
Prism on our side, the farm never left with no valid choice, prune bounds valid, release builds unaffected); fix what
it finds. 3. Smoke each in parallel:
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/NAME variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-NAME-smoke`
(256 ladder games each): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Also one `--debug` smoke of k8-war with a
debug-only trace line `PW <round> <id> dom|out <enemy id> <our burst> <its health> <its burst> <our health>` printed
once per turn when either holds, and report how often each fires per game. Delete the smoke batches afterwards.
4. Save diffs to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/NAME.diff`
(`diff -ru bots/variants/chy-ref/src bots/variants/NAME/src`) as soon as each builds (the orchestrator starts
screening from the diff's appearance; do k8-hunt's preyable half first if it is quickest), then audit and smoke.
Return what changed per variant, auditor findings and fixes, smoke results and the PW firing rates. No large A/Bs.
