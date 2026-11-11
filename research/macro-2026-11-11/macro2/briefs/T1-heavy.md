# T1: heavy-camp programme for Golems and Monoliths (`bots/variants/macro2-heavy`)

Read briefs/common.md (same folder) first and follow it. Candidate dir: `bots/variants/macro2-heavy`, created with
`./copybot variants/ocean-ref-b7c87cf variants/macro2-heavy`.

## Why (measured on 512 ocean-vs-ocean games)
- Value per champion-round (clear + walk-in + 6-round hold, crews included): Monolith 0.85 gems + 1.2 gold,
  Golem 0.53 gems + 1.9 gold, Elk 0.40 + 1.9, clusters 0.37 + 1.0, Wolf 0.22 + 1.4. Even charging a Monolith clear's
  ~4.3k camp damage as ~4-5 heal trips (~25 champion-rounds each), a full-crew Monolith is ~0.6 gems/cr vs a team
  average of ~0.23-0.3 gems per champion-round over a game. Monoliths: first hit at a median r567, never hit in 53%
  of Monolith games, 52-54% of respawn windows never captured. Golems: first hit median r259; 17% of own-side Golem
  windows uncaptured. Monolith clears that happen use 3.9 hitters on average, last ~41 rounds and take ~4.3k damage.
  In 36% of Monolith clears an enemy also hits it. Capture margin on these groups is the strongest late decider of
  games (more Monolith captures -> 91% win; Golem capture margin +-2 -> 85%).
- Hypothesised root cause: in `economy/farm.cc` a strong group's crew value counts only allies that are already
  claimers or "available" nearby (`crew.cc crew_available`: in sight, unclaimed or on harmless groups, within
  ~11 of the centre), so a heavy group far from where allies happen to be never looks good, nobody goes, and it stays
  idle until late (circular). A lone Monolith is valued 0 (`late` in farm_turn). Read farm.cc's crew branch,
  crew.cc (plan_crew, share_damage, crew proposals/bans), siege.cc (team sieges, used on Monolith-only maps) and the
  Monolith op code (mono_group, mono_engage, mono_gather_share) before designing.
- Priors (research/EXPERIMENTS.md): "Monolith sieges on any map when their rate beats the team's" lost 48.3%
  because they started ~r320 and never cleared in time; team sieges from r400 lost (other camps' gems fell);
  eris's any-side Monoliths gained +4.4 on Monolith maps; solo chipping lost. So the programme must launch only when
  the crew it will actually get clears the group in a bounded time, and must not strand the rest of the farm.

## Design goals (you decide the specifics, grounded in the rules and the existing code)
1. Team-throughput valuation of a heavy group (Golem/Monolith-containing group): the crew that would actually come
   (allies by their walking distance, health, current commitments as visible through claims/comms), its output,
   the clear rounds `hp_left / output` (camps never regenerate: count damage already done), the camp damage taken
   (each awake monster hits only the nearest champion each camp phase, so damage = sum of awake members' strength x
   rounds, absorbed by whoever stands nearest), the heal trips that damage forces, everyone's walk-in, the hold.
   Gems + gold value per champion-round of that plan, compared with what those champions earn otherwise (their own
   farm values). Launch when the heavy plan wins; the clear must fit a bounded number of rounds.
2. Make allies converge without a rigid summons: e.g. when a champion's valuation says the heavy op wins, it claims
   the group and the crew-expectation logic counts the allies whose own valuation would also pick it (so every ally
   computes the same answer from the same inputs and comes on its own), rather than only allies already near.
   Reuse the existing proposal/claim/crew/mono-staging mechanics where they fit; extend instead of duplicating.
3. Execution: stage just outside reach before waking (existing mono_engage/heal_before_waking); the highest-HP
   member tanks (stands nearest; others at their max attack range so the camp targets the tank), a tank near its
   recall line steps back so the next-healthiest becomes nearest, then recalls/heals and returns (or not, if the
   remaining crew still clears in time). Golems can be done by 2-3, Monoliths need most of the team.
4. Safety: don't launch while visible/credible enemy force near the group would beat the crew; the existing
   retreat logic (want_home) stays in charge of leaving.
5. Debug traces in debug_block (compiled out in release): launches, crew size, expected vs actual clear rounds.

## Not in scope
Draft, emblems, combat micro, banking thresholds. Don't retune unrelated constants. New constants: named in
params.h with a short rationale; prefer quantities derived from rules (camp hp/strength/range, recall turns) or the
bot's own measured stats.

## Done when
Builds; three local games run to completion without bot errors, including at least one map with a Monolith (e.g.
`maps/00monolith*` or a generated map from /home/ubuntu/wt/macro2-maps/s-200001/ whose name or contents show a
Monolith) and one with a Golem; the auditor's findings are addressed. Report what you built and where.
