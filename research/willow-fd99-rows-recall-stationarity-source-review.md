# fd99 Rows: recall stubs and a possible no-work retention gap

2026-10-23. Bounded source and saved-evidence review; no new extraction, tooling, implementation, build or runtime. Evidence binding is `research/willow-fd99-four-pick-loss-cells.md`, SHA `9e77a4979eadab1b04ab96a18d07ce8a5d90a036efac225bb74113e7b12a97f5`. The exact replay is `041-00rows-12.repl26a`, SHA `bb485f891944ae3ed739b91812c576d30ac48e4c0f87e5cd4b376bdb75042a16`, in `replays/willow-sustainable-crew-fallback-vs-a67-published80-20261023-v1/`; saved extract `bb485f891944ae3e`.

Prism0's manual recall cancel/restart at [26,7] during 1157–1167, constant end HP 1843.6, acted end status and absent end-visible enemies establish the action pattern. They do not establish start visibility, max HP fraction, modeled threats, camp belief, received bags, selected job or legal route. Candidate begins its 43-turn tribute at 1209; public score plus its 422 gems reaches 1000 only at 1224. This is not evidence that it ignored an already-winning personal bag. Eliminating eleven standing turns alone would not erase the roughly 21-turn completion gap to the parent's tribute.

## The channel flow is intentional and unchanged

fd99 and a67 have the same channel, retention and banking functions; their source difference is in farm. `decide` first clears banking when the bag is unbankable or Prism is retaining (`5167`), then handles recall/tribute before ordinary goals. `continue_recall` (`4196`) keeps a recall for a justified retreat, capture payout, banking, shopping, siege recovery or a crystal pocket. Otherwise it cancels. `act` later invokes `start_recall` (`5315`) at the end of normal turns. Restarting a fresh recall after cancellation is deliberate, so cancellation alone is not the defect.

`continue_tribute` normally keeps a safe channel and otherwise requires a reason to interrupt. The observed standing interval predates the actual tribute, so it cannot be attributed to repeated tribute cancellation. A large carried Prism bag is retained only while it is neither winning nor closing (`685`); closing depends on its team's estimated remaining race horizon, not hidden enemy capital (`656–682`). Bankability also requires a modeled usable altar (`625`), which absent end-visible enemies does not prove.

## Two concrete conditional traps, neither witnessed yet

The more direct macro hypothesis is a **no-work retention gap**. Closing compares the race horizon to current altar travel plus the full tribute plus 20 turns. A newly selected farm job must additionally fit approach, wait, clear and capture before its altar/tribute deadline (`2319`, `2346`, `2408`). Therefore every useful clear can fail its deadline while closing remains false. Retained Prism then bypasses `carry_bag`, reaches farm, and farm returns true with no selected job (`2459–2471`). fd99 may clear the positively rejected incumbent; it does not stage toward an altar or release retention on that result. The normal end recall is cancelled next turn when no independent recall-keep reason passes. Unchanged information can repeat the standing state until a camp, estimate or teammate capital changes.

This is a concrete source-possible gap between “too late to finish another job” and “late enough to force banking,” not proof of the Rows branch. A cheap profitable job, acceptable respawn wait, partial evaluation, retained old route or other higher-priority goal would change the diagnosis. The existing farm deadline already includes altar travel even for retained bags; there is no general missing-altar-deadline defect here.

A separate route trap is possible if banking or shopping is selected. `recall_to_bank` compares a recall trip against a finite terrain-only altar distance; shopping compares remaining recall time with the terrain-only spawn distance. Actual movement subsequently respects live camps, occupancy and guards. If the static comparison favors walking but the live route makes no progress, the same inequality can cancel every fresh recall while `bank_gems`/`step_safely` record no successful step or explicit failed-progress fallback. This source mismatch is actionable only if the witness shows banking/shop, rather than retained farming. Neither static distance proves that a live route exists.

## Smallest useful witness

Use Prism0/A's last stationary turn 1167 and first moving turn 1168. Record values at existing computation sites, without new visibility, Safety, pricing or route queries:

- The recall keep/cancel reason; cached banking flag, bankable bag, winning/retaining/closing results, race horizon and already-read altar travel/tribute terms.
- Final decision and group/claim/crew identity. If farm runs, evaluation count, selected tier/group or no-choice, incumbent rejection and existing deadline/wait rejection counts or values.
- Only for the actual movement branch, selected goal/field and attempted route/step result. A bankability refusal needs its existing altar-access/fire result, not a guessed enemy-free certificate.

This separates retained no-work, selected waiting, partial evaluation, blocked live routing and an intentional non-farm return. A no-choice result with closing false would nominate a small future fallback that stages toward conversion only after genuinely evaluated work fails; a bank/shop route failure would nominate a different repair. Neither justifies changing global Prism banking thresholds, enemy-race prediction or recall behavior now. The stationary-work arm is not a targeted repair for this Rows interval, and these four-pick games contain no Willow.
