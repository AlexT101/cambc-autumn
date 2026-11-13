# Brief k3: soft team gravity in the farm choice (three probe strengths)

You are implementing probe variants of the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md`, `cambc-rules.yaml` and what you need of `docs/api/cpp.md`.
Work ONLY in `/home/ubuntu/wt/mac13-kronos`; do not touch `/home/ubuntu/cambc-autumn` or other worktrees; do not commit.
Never edit `bots/variants/chy-ref` or `bots/charybdis`. Off limits: `src/draft/`, emblem choices.

## Why
Fights in this game are decided by local numbers (kill share ~0.35 two bodies down, ~0.65 two up) and initiative.
charybdis farms dispersed (nearest ally ~4-5 tiles). An earlier hard "pack" (allies may farm only near the Prism's
work, else walk to it) gained kills +30%, cut deaths 18% and gave the Prism +23% gems, but lost 11 points because
allies idled or walked back when nothing was in the pack, captures fell 16% and team tributes 30%. Masks and escorts
that restrict where allies farm all lost in proportion to how often they bound. Untested: a *soft* pull, a term in
each champion's own farm value that prefers groups near teammates without ever forbidding a group, so a champion
with nothing near the team still farms where it would.

## Design
In the farm loop's valuation of a candidate group g (`economy/farm.cc`, where each group's priced value/rate is
formed; find the single place where the final comparable value is set so every mode is treated alike, after
exposure/home weight), multiply the value by `1 + lambda * s(g)`, where s(g) in [0, 1] measures teammate support at g:
- For each living teammate (not self) with a known tile (visible, or `recent_tile`/`comms::told_ally` as
  `economy/capture.cc` does), take its "work point": the centre of the group it claims (`comms::claim_of`) if any,
  else its tile. Support from that teammate = max(0, 1 - d / R) with d the Chebyshev distance from g's centre to the
  work point and R = 8 (champion vision radius: an ally farther than its sight can neither see nor answer a fight).
- s(g) = min(1, sum of supports / 2) (two supporting teammates saturate it).
- Our Prism (Prism passive) counts double as a work point for the others (protecting the team's carry); the Prism
  itself uses the plain sum.
- Healers (Willow) are unchanged by this term (they follow their mate already).
- No effect on the opening plan's steps, sieges, contests, banking or the carry picks' own tests beyond the value.
Prunes that bound a group's value must stay valid: scale their bounds by (1 + lambda) (the most s can give).

Variants (each `./copybot variants/chy-ref variants/NAME`): `k3-g10` lambda = 0.10, `k3-g25` lambda = 0.25,
`k3-g50` lambda = 0.50. Implement once with lambda as a constexpr in params.h (`team_gravity`), then copy and change it.
Add a debug-only trace (`debug_block`): every 50 rounds per champion print `GRV <round> <id> <s of the chosen group>
<changed>` where changed = 1 if the chosen group differs from what lambda = 0 would have chosen (if that is cheap to
know; else omit the field).

## Stop condition
1. All three build. 2. Spawn a read-only auditor subagent (tell it explicitly not to edit anything) to check the diff
against this brief and the rules (prune bounds, every mode priced, told tiles, fuel); fix what it finds.
3. Smoke each: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/NAME variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-NAME-smoke`
(256 ladder games): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK.
4. Save diffs to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/NAME.diff`. Return what changed, the
auditor's findings and fixes, and smoke results. Do not run dev A/Bs.
