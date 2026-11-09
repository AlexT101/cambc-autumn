**Combat behavior investigation and proposed lab programme — 2026-11-08**

Investigation and planning only. No bot, runner, analysis script, build, simulation or test was changed or run for this investigation. This document is the only new artifact. Source inspected: `bots/ocean` at HEAD `238185742b6ce74cd100de2d238d57a831edeaa8`, with `test_draft = false`. Existing uncommitted research was read, not edited. Numbers below are previous recorded measurements, not new results. Code observations establish what the implementation represents; they do not establish the frequency or win-rate cost of a failure.

The programme target is a substantial combat improvement, aiming at **55% or better against a frozen current ocean**, with improvement checked against other opponents. This is a working definition of the benchmark, not a prediction. A small statistically significant gain would be an intermediate result, not completion. The teammate's reported ~53% is encouraging but cannot be compared or added to another gain without the code, reference and evaluation conditions.

**1. Main conclusion**

Ocean has a sophisticated single-turn action search and detailed immediate reach calculations. Its largest representational gaps sit around them: deciding which complete tactical behavior to attempt, preserving alternatives that matter after this turn, and predicting how both teams respond to those alternatives.

The useful question for the lab is: **from the same information and history, does this executable sequence improve our team's continuation compared with what ocean actually does?** Predicting incoming damage, matching another bot's cast rate, or reducing retreat oscillation is evidence about an intermediate quantity. None is itself the objective.

The strongest initial candidates are:

1. Route-aware disengagement and pursuit, including escape cutoffs and controlled counterattacks.
2. Evaluating safety after the proposed attack/stun/move sequence, with an explicit next-turn continuation.
3. Feasible team responses: who can actually strike whom, in which order, and what happens to allies when an enemy chooses us instead.

Camp control and fog/history behavior should be studied within these encounters. They are not adequately tested by adding a flat camp-damage bonus or a generic extra-danger penalty.

**2. What the earlier experiments establish—and what they leave open**

| Recorded result | Supported conclusion | Question still open |
|---|---|---|
| Lab experiment 1: hindsight best of nine alternatives gained +0.84 reward/decision; cross-opponent same-frame correlation 0.33–0.35. Reweighting score components gained at most about ±0.005 held out; a fitted selector correlated only 0.03–0.06 with gains. | The tested alternatives contain opportunities, but those features did not select them reliably. | Can route, timing, target-access and response features explain particular families of gains? Which useful actions were never offered? |
| Experiment 2: forced retreat from a stay decision was learnable at roughly +0.04–0.05 lab reward/decision; its full-game value was left open. | Some conditional decisions could be improved under the lab reward. | Does the improvement survive the lost work, recovery travel and subsequent objective contest? |
| Reply model: danger log loss 0.42 versus 0.64; gated lean model approximately 49.9% over 30,720 full games. | That predictor and its insertion into the existing score did not improve play. | Can predictions of complete responses choose better tactics, rather than just reprice the current leaves? |
| Phase 2: shadow computation alone lost around a point; consistency changes were level with +16–20% out-of-fuel turns. Later migration steps were skipped. | Query-dependent cost and the tested consistency intervention failed. | Multi-turn response selection, retreat options and the skipped later behavior changes were not thereby disproved. |
| Older ranged retreat shooting: extra damage was paid back in deaths; a step that still admitted a worst-case hit often stopped the actual exchange. | “The bound is no better, so shoot” is an inadequate decision rule. | Which routes force pursuit movement, spend its cast, break sight or buy an ally's response? |
| Old reach play-out calibrated better but added 15–22% out-of-fuel turns; reach alone did not win. | More detailed stand prediction is not enough, especially at that cost. | Can a short exact local continuation improve a particular decision and then be distilled cheaply? |
| Camp-aggro variants stayed around 50% across large samples, including cheaper and weight variants. | Crediting incidental wake damage was not a successful programme. | Can position, turn order and camp fire jointly force an escape route, save a teammate or control a capture? |

Sources: [EXPERIMENTS](../EXPERIMENTS.md), sections “Combat lab experiments 1-2”, “Reply model”, “Ranged retreat steps and shots”, “Fight play-out with reach”, and “Camp aggro”; [phase-2 plan and status](../reply-model/PLAN2.md).

Several earlier interpretations go further than their evidence. Similar observed cutoff-step rates do not show that selecting a different cutoff would have no effect. A reduction in A–B–A movement without a win-rate change does not establish that every oscillation is harmless. A measured rate gap to another bot is neither a causal effect nor an upper bound on achievable improvement. These remain useful diagnostics, not reasons to close a behavior class.

Also avoid resurrecting obsolete gaps. [The recent fight-execution study](../ideas-2026-11-08/fight-execution.md) records that CHANGES 464 closed much of the earlier double-turn disadvantage; it also finds substantial existing focus fire and no observed overlapping-stun problem in its sample. Its spell-rate intervention subsequently increased casts without increasing kills materially. The next programme must find current counterfactual failures, not reuse historical symptoms.

**3. What current ocean actually does**

In [bot.cc](../../bots/ocean/src/bot.cc), `decide()` resolves channels and free actions, asks `want_home`, handles support, and branches into retreat before the normal strike search. Otherwise it installs a step guard, runs `plan_strikes`, and spends remaining actions on capture, banking, shopping, guard/chase or farming. Thus `want_home = false` does not mean “fight here”; a refusal to chase can hand movement to farm. A strike can also be followed by another goal's movement.

The [strike search](../../bots/ocean/src/combat/plan.cc) enumerates legal within-turn walk/attack/reset/dash/spell sequences, handles kills opening tiles, retaliation, linked bodies, stuns, heals and shields. It is bounded (`max_nodes = 12`, `max_exact_queries = 6`), and uses an immediate score plus endpoint danger and goal progress. This is a strong base to retain.

[Safety](../../bots/ocean/src/model/safety.cc) places immediate enemy reach on terrain with visibility, dash constraints and turn windows. Its longer fight model is different: nearby fighters enter after arrival delays, each side acts as a block, damage is pooled onto its weakest opponent and excess damage spills to the next. Stuns are a count assigned to the strongest eligible opponents, rather than the actual recipients of particular casts. Healing likewise lacks a continuing spatial relationship after arrival. These are intentional approximations, not engine rules.

Coordination already includes `team_pressed`, [own kill bids](../../bots/ocean/src/model/follow.h), [turn-order bids](../../bots/ocean/src/model/turn_order.cc), and a [Willow/protected-mate protocol](../../bots/ocean/src/model/support_mailbox.h). There is no general executable joint combat plan in these paths. In particular, `side_damage()` adds possible ally strikes for a kill bid; the bid binds our own subsequent damage, not every contributing ally's action.

Enemy memory is also already substantial. [World::update_champion](../../bots/ocean/src/model/world.cc) retains observed Strength, Focus and emblem modifiers through fog; tracks possible positions and earliest cooldown readiness; handles recall feints, shield expiry and respawn. “Remember enemy emblems” would duplicate existing work. Consumer assumptions still deserve investigation, as described below.

**4. Behavior investigations, in priority order**

**A. Escape routes and pursuit cutoffs**

**Code evidence.** `retreat_step()` in [fight.cc](../../bots/ocean/src/combat/fight.cc), around line 178, primarily ranks immediate damage, stun risk and distance home. A farther-from-home option is admitted only if `Safety::touched()` is false, and farther options are considered only when no clear non-longer option exists. `HomeWalk` examines a limited homeward continuation; `flee_camps` examines camp exits. These are useful exceptions, but neither is a general pursuit/escape comparison. `chase()` around line 776 heads to attack range of the target's current position, or its possible tiles if unseen. `chase_aim` and search progress mostly reward reducing current distance.

**Hypothesis.** Ocean can miss a survivable route requiring one initially exposed step away from home, or chase directly when a different approach denies the enemy's escape. This is a candidate-generation gap as well as a ranking gap.

**Lab alternatives.** At a pursuit decision, compare ocean's continuation with short options: take the direct route; go around either relevant obstacle; enter a sight-breaking bush/corner; reserve or spend the dash; stun then disengage; attack while retreating; approach an exit before the fleeing target reaches it. Plan roughly 2–4 own turns initially, extending only when a named event such as a dash becoming ready or a camp phase requires it. Reassess after each observation; do not force a stale plan for 30 rounds.

**What must be represented.** Opponent walking can cost a ranged attack; casting an exclusive ability can surrender pursuit movement. Turn order can buy two moves or two hits across a round boundary. An escape destination is useful only if its next exits and visibility survive the opponent's response. A cutoff must cover actual legal escape paths, not simply stand closer to the enemy spawn. King movement permits diagonal gaps; dash paths and landing occupancy differ. A melee enemy may continue attacking while pursuing.

**Team effects.** Escaping toward an ally may transfer lethal pressure to it, block its only firing tile, or make it abandon a capture. Chasing around a structure may consume the time the enemy needed to bank or reinforce. Those consequences belong in the comparison.

**Evidence to demand.** Saved deaths and converted kills on paired continuations, time until pursuit is broken, useful hits before the target's escape, team gem/score change, and time until useful work resumes. Include cases where the apparent escape becomes a trap. Fewer steps home or fewer immediate hits is not sufficient. The old “shoot instead of a doomed walk” and passive haven bonuses are controls, not the proposed mechanism.

**B. Safety of an action sequence, rather than of an untouched tile**

**Code evidence.** [step_guard](../../bots/ocean/src/combat/guard.cc), around line 501, determines excluded endpoints from the pre-action roster. `Search::offer()` then applies `ends &= ~guarded` before evaluating that leaf's removed enemies. The search's subsequent danger price does remove enemies killed or stunned, and it opens killed units' tiles, but a guarded endpoint has already been discarded. At the outer search radius, `safety.lethal(p)` is also evaluated without that leaf's kill/stun overlay. These are specific places to audit, not proof of a missed winning move on every such tile.

**Hypothesis.** Some legal attack-and-exit, kill-through-blocker, stun-and-step, or temporary-exposure sequences are rejected because the endpoint is evaluated before their effects. Conversely, accepting a good immediate exchange without an exit can create a losing continuation.

**Lab alternatives.** Preserve a separate diagnostic set of legal sequences excluded by these policy guards. Replay the complete sequence and its replies. Compare: original guard; the same guard after the sequence's actual kills/stuns/cooldown use; and a short continuation comparison. Do not globally remove guards or lower danger.

**Important distinctions.** A stun removes one actual future turn, not every attack before our next turn. Killing Cassi/Issac removes both bodies; damaging Ren can kill the actor; hurting Heart of Ruin can strengthen its reply. A camp death opens a tile and may change capture state. A move off a capture resets progress immediately even if the champion returns later that turn. The action can also reveal a blocker and invalidate the rest of the sequence.

**Evidence to demand.** An explainable set of currently excluded sequences that actually improves continuations; report counterexamples and the reason for acceptance. Track both directions: profitable actions recovered and newly accepted traps. The prior “make guards agree with want_home” intervention did not ask this same question.

**C. Team fights with feasible replies and commitments**

**Code evidence.** In [safety.cc](../../bots/ocean/src/model/safety.cc), `Side::hurt`, `act`, `stun_skips` and `simulate` discard much of the geometry and individual order after roster construction. `walk_allies_in` uses distance-based arrival, and an unseen opponent makes the distance delay zero. `fighting_allies` uses visible proximity. In [turn_order.cc](../../bots/ocean/src/model/turn_order.cc), `side_damage` counts available allied output without ensuring those allies will choose that target or remain in reach. [Front::admit](../../bots/ocean/src/combat/plan.cc), around line 309, can discard a lower immediate-score sequence with the same removed-enemy set even when it damages a different target and enables a later ally kill.

**Hypothesis.** The opportunity is to coordinate executable conversions, protection and access. Merely increasing a focus-fire bonus or including more allies in a roster repeats previous failed approaches.

**Lab alternatives.** Compare natural independent play with a short coordinated option: one champion pins or stuns, another closes an exit; a durable ally occupies the threatening tile while the carrier leaves; a caster holds a shot until a teammate supplies the missing damage; a healer stays in actual sight/range; an attacker takes a different target to preserve a teammate's kill without overkill. Each action is executed at its actual seat, and the plan updates if someone moves or declines.

**Enemy response representation.** Predict or enumerate complete legal action sequences. An enemy cannot independently apply its maximal single-target attack to every ally, but it can basic-attack one target and cast at another, reset for another hit, or hit several with an area effect. Keep those joint constraints. Evaluate the entire resulting team state: lower damage to us can mean greater damage to our ally; accepting a hit on a durable body may be advantageous.

**Access and cooperation.** Model which opponent each ally can reach and see after movement, not just who is near. Count a guaranteed ally response only when it follows from available actions and an actual commitment; otherwise branch on fighting, retreating, healing, banking or remaining at work. Reuse existing bids/support messages where possible. Any new protocol must fit the eight shared bytes or visible priority payload and their real timing; it cannot use global sight.

**Evidence to demand.** Earlier confirmed kills, survival of the intended protected champion, team output preserved, and objective retention. Report the cost of concentrating too much damage, vacating a valuable position, and optimistic ally predictions. A higher same-target rate by itself is not progress.

**D. Camp control as part of a fight**

**Code evidence.** `Search::read_camps` considers direct camp targets for Vendetta resets or Varg splash. `Search::wake` explicitly awards no value for a hit on an enemy. Sleeping Monolith wakes and several ally-risk cases are prohibited; Heart of Ruin landings touching sleeping strikers are removed by `land_bad`. Awake-camp estimates choose nearest champions from the current snapshot, whereas the next camp phase follows the remaining champion turns.

**Lab alternatives.** Use a camp as a threat controlling an exit; wake before a held enemy's next camp phase; move so the enemy becomes nearest; stun a dangerous member to buy an escape; kill a blocker to open a route; preserve a blocker that prevents pursuit; finish or contest a capture while the other side is forced away.

The first-hit recipient can be certain when an enemy already acted or is held, but later recipients depend on both teams' movement. Respect per-monster sleep, group wake, stun skips, damage mitigation, shields, priority ties and camp respawns. Camp-killing an enemy destroys its carried gems rather than transferring them to us; kill reward and capture reward must not be conflated. An enemy can sometimes benefit from the wake by clearing/capturing sooner. Include allied channel interruption and lost holdings.

Start with demonstrated positional consequences, not another wake-damage multiplier. The old incidental-aggro null is strong evidence against repeating that implementation, not against all camp tactics.

**E. History, fog and conditional enemy behavior**

**Code evidence.** [ChampionBelief](../../bots/ocean/src/model/world.h) retains emblems and known stats. However, `make_fighter()` in [safety.cc](../../bots/ocean/src/model/safety.cc), around line 256, includes a remembered shield only while the champion is visible/self; `effective_hp()` can still include the remembered shield. `possible` explicitly does not model unseen teleports. Fog damage, hidden shopping and intervening casts make some remembered quantities uncertain rather than exact. These cases need explicit semantics at each consumer.

**Lab alternatives.** Compare continuations after identical visible observations with different legitimate earlier histories: shield seen versus never seen; a revealed enemy shop visit; a dash recently spent; persistent pursuit versus repeated disengagement; an opponent choosing a weaker ally instead of us. Keep policy inputs limited to what that champion legitimately observed or received.

Do not “fix” uncertain shields by assuming they remain full, or assume every unseen enemy is newly upgraded. Preserve exact information, expire effects on actual turn timing, and represent plausible changes as uncertainty. For response learning, prefer target/action/continuation labels conditioned on our proposed move over independent per-victim hit probabilities. Learn from revealed sequences and retain uncertainty when several causes fit a health drop. A few non-attacks do not prove an enemy will never attack.

Online history is a possible extra signal, not the first implementation requirement. First demonstrate that it changes the ranking of a profitable tactic on held-out games/opponents. This investigation found no general learned pursuit/target policy in the inspected combat paths; the existing recall-feint recognition already handles one specific pattern.

**5. The lab must expose the right experiment**

The [current scenario implementation](../../tools/fastengine/runner/src/scenario.rs) and [runner documentation](../fastengine/RUNNER.md) distinguish two things:

- Initial scenarios reconstruct a board and create fresh bots for fighters only. Memories and team shared bytes start empty; non-fighters idle on spawn. Original tributed totals, channels, locks, capture progress/timers and several other states are not restored. Warming tables improves cost but does not recreate tactical history.
- Alternatives *within that reconstructed rollout* already have a fork mechanism preserving engine, host, live bot and rollout state. This is useful infrastructure. It is not a snapshot of the original full game.

For history-sensitive experiments, the preferred extension is to run a real local game prefix with all champions active, then fork its live engine and bot state at the desired decision. Preserve memory, shared/draft bytes, priorities, cooldowns, wards, channels, camps, scores and fuel/resumption state. Reuse the existing snapshot machinery; do not start by writing another combat simulator. [Native GuestSnap](../../tools/fastengine/runner/src/native.rs) is tied to the same live guest and contains stack pointers: arbitrary swapping to a different candidate executable at a checkpoint is not valid. Lab controls in one executable can select different continuations; production variants are then evaluated from game start.

This extension needs a continuation-identity check before it supplies causal labels. Restoring a snapshot and making no intervention must reproduce the same actions, engine outcome and fuel behavior. Document unsupported states explicitly. An instrumented prefix can be faithful to its own executable while differing from an uninstrumented release bot; those are separate checks. The earlier lab's hooks changed real-budget games even though high-budget replays agreed.

Keep reconstructed scenarios for inexpensive geometry/unit-mechanism work, with a declaration of which state they preserve. Do not let the infrastructure become an excuse to postpone every useful investigation. But do not infer the value of a memory, capture or reinforcement behavior from scenarios that remove its defining state. If true prefix forks prove impractical, use bounded, fully replayed prefixes and state exactly what history remains missing.

The alternative interface needs widening too. [lab_banned](../../tools/combatlab/lab.h) distinguishes endpoint, cast-kept flag and removed-enemy set; it does not identify the exact target/action sequence. It bans candidates only after the search has already applied guards, dominance and node caps. Consequently, `--alt 8` cannot establish optimality over actions excluded earlier. Add lab-only intervention points for complete sequences, retreat destinations, pursuit waypoints and short multi-champion tactics. Record why an alternative was absent: illegal, policy-guarded, dominated, capped, or never generated. Preserve target identity and resulting health/cooldown/position differences when those define the experiment.

**6. Sampling and outcome evaluation**

The existing [frame extractor](../../tools/combatlab/frames.py) anchors on fights that actually produced damage and selects core fighters using subsequent participation. It skips many channel/respawn cases. That is suitable for its original fight bank, but it does not sample peaceful encounters where a different policy could profitably engage, aborted pursuits, or all mid-fight turning points.

Build the future investigation bank from current ocean decisions across:

- First contact, including contacts that never produce damage.
- Pursuit/retreat transitions and loss/reacquisition of sight.
- Ally arrivals/departures and changed target access.
- Cooldown readiness, stun windows and round-boundary order changes.
- Camp wakes/sleep transitions, contested captures and channels near fights.

Select using information available at the decision; future outcomes may label it but must not define the candidate's inputs. Sample representative encounters as well as failures. Include successes as negative controls. Keep all champions active in natural continuations; don't decide the roster from who happened to join the original fight.

Split by source game and map/seed family, keeping every frame and alternative of an encounter together. Hold out opponent policies as well. Experiment 1's recorded hashed-frame split deserves a grouping audit before reuse; the reply experiment explicitly split by game. Deterministic reruns supply no extra evidence. Statistical resampling must operate at game/map-pair level, not pretend each nearby turn is independent.

Use several horizons: immediate reply window; the next few tactical turns; 10/30 rounds for comparison with old work; and continuation through recovery/objective resolution or full-game end for selected cases. Avoid treating “apart for three rounds” as automatically terminal success: a retreat can merely postpone death or abandon a winning objective.

Record an outcome vector before compressing it into a score: deaths, linked-body loss, kills and actual kill reward, carried/transferred/destroyed/tributed gems, capture outcomes, team gold, health/shields, cooldowns, position, and time out of useful work. The original [alt_report reward](../../tools/combatlab/alt_report.py) counts normalized HP, deaths and carried gems; it omits banking and work opportunity cost. Later reply experiments added tributes, so this criticism does not apply identically to every run. Neither reward alone measures game value. Cassi/Issac lose two bodies but award one kill reward: retain both facts rather than mechanically doubling the kill value.

The learning target is the **difference between complete continuations from the same state**, not predicted fight outcome alone. If a scalar is useful for ranking, validate its relationship to actual game outcomes and show sensitivity to its weights; retain the components so a new score cannot conceal why a tactic appears to win. Hindsight-best gain is an opportunity estimate, not a deployable policy result. Report what a held-out, observation-limited selector actually captures.

**7. Concrete execution sequence after this planning stage**

| Stage | Deliverable | Decision it enables |
|---|---|---|
| 1. Freeze and audit | Frozen current ocean; inventory of lab state fidelity and action-hook coverage; small identity-checked full-prefix fork path for the behaviors needing it. | Which measurements are trustworthy for each question? |
| 2. Current decision census | Representative encounters with branch reasons, candidates retained/excluded and true continuations. A set of annotated positive and negative examples for A–E above. | Which mechanisms have demonstrated reachable gains and which are still conjecture? |
| 3. Tactical counterfactuals | Paired complete alternatives for escape/pursuit, action-dependent guard decisions and feasible team responses; camp/fog cases embedded. Natural continuations plus explicitly labelled adversarial stress cases. | Is the mechanism effective, and under what observable preconditions? |
| 4. Observation-limited policy | A small C++ behavior/rule or bounded local search selecting useful options on unseen encounters. Confidence/abort conditions for changing information; old behavior as fallback. | Can the opportunity be captured without hindsight? |
| 5. Fuel and full-game validation | Release variants at real fuel, fresh suites, opponent panel, interaction checks and outcome decomposition. | Does the complete bot improve substantially? |

Do not launch all ideas as blind toggles. For each, first write a short mechanism card: what ocean chooses, what state it loses, the proposed alternative, why the opponent's best plausible replies still leave value, and one nearby counterexample where the tactic should not apply. Ablations are useful later for attribution, not a replacement for that reasoning.

Use expensive lab search as an offline teacher. Ship only the smallest behavior that reproduces a demonstrated advantage. If runtime search is necessary, budget its total work per turn before spending it, preserve a complete executable fallback, and account for setup plus query-dependent cost. Measure p95/p99 encounter cost, action truncation and lost turns, not only mean fuel. A shadow arm must match where/how often computation occurs; the earlier flat mean-cost burn is not an adequate substitute for a query-scaled cost distribution. Higher-budget runs diagnose behavior versus cost; they cannot establish production strength.

Initial full-game checks follow AGENTS.md: directory bots against a frozen reference, release builds, fast runner, both on their own drafts (`--no-test-draft`), and the canonical 1,280-game suite as an initial check. Confirm substantial candidates on unused `ladder-v2` suites, both sides, with predeclared stopping rules and distinct SPRT seeds if used. Include a fresh varied suite and paired performance against multiple opponent policies/compositions. A deliberately mixed own/test-draft panel is a separate ladder-composition experiment and must be labelled as such.

Report confidence intervals and map-family/opponent heterogeneity. A 55% point estimate is not proof that the true rate exceeds 55%. Do not convert saved deaths or historical net-kill correlations directly into claimed win-rate points. Compare the final combination directly against the frozen starting ocean; component gains are not additive. Once the teammate's changes arrive, test overlap and interaction against that concrete bot as well.

**8. What would change this plan**

If route alternatives repeatedly produce no useful advantage on representative cases, investigate access, timing or the decision to disengage rather than tuning route weights. If action-aware guards recover attractive immediate trades but lose after reinforcement or objective resolution, the continuation evaluation is incomplete. If a joint plan works only with allies obeying information they cannot possess, it is not implementable. If enemy-response models improve calibration but not action ranking, stop fitting that label. If lab gains vanish in natural stateful continuations, audit the intervention and scenario before escalating sample size.

None of those outcomes justifies declaring combat optimal. They identify a failed mechanism or experiment. The programme ends when the complete current bot demonstrates the substantial held-out improvement, not when an intermediate predictor becomes accurate or a small A/B becomes significant.
