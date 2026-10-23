# Willow published-panel loss windows

2026-10-23. Read-only nomination from the existing 80-game published-map panel, not a policy diagnosis or map-selector proposal. No source, extraction, engine, build, tooling or EXPERIMENTS changes.

## Evidence boundary and provenance

Batch: `replays/willow-upstream-presence-vs-8be8eaa/batch-run-01-release-published40/` (abbreviated `B` below). Frozen candidate aggregate `db5b37d5e5c609c2c616d3a39c0f1eb7f5adebf401dcd1be8848e0eede237ab8`; frozen latest-main reference `d8d3cc1da72aaf62eb65fc5de8402b9c3a98a8aade1fabeb5cd9841b3ff01e2c`. Corrected v3 `economic-capture-summary.json` was rehashed as `aac4f53620484fa0e875f2c9c31ab7b023fad7cde804ff4b9de9f3ff047cc948`. Event `t` is turn index, never team; actor metadata and explicit capture `team` establish allegiance.

The panel is 43–37 overall, 30–22 in the 52 five-pick games. These are different native rosters, so outgoing healing and other team totals do not isolate Willow's causal value. The existing 22 five-pick losses were screened through cached metadata, then selected event/round windows were read. Elkring loses from both physical sides and supplies two related Willow retreat nominations. The 52 games do not justify fitting a map draft rule.

`events.jsonl.gz` establishes actual actions/results. `rounds.json.gz` is an end-of-round global locator, **not** the actor's start-of-turn own observation. No own-view window was available/read for these nominees. Visible enemies, safe alternate steps, branch decisions and remembered threat state therefore remain to be checked. Ordinary four-turn recall starts/cancellations are the bot's routine stubs, not evidence that it tried and failed to complete a recall.

## 1. Highest priority: 385-gem retreat after abandoning tribute

- Replay `B/012-00elkring-21.repl26a`; SHA `ea197672d811ef5ccbe56b77c7180f0861ffc6fa75fd312f282cc48d05aa1503`.
- Cached extraction `B/analysis/ea197672d811ef5c/`; candidate physical B, Willow actor **8**.
- Request actor-own rounds **665–673**, with later 674–675 only as outcome context. Core decisions: tribute cancellation 667, stationary 668, and the reversal 669.

Actual global sequence: at r658 Willow's basic kills enemy Marcella at `(20,0)`, transferring **385 gems** to Willow at `(23,1)`. She spends r659–663 breaking the enemy altar lock at `(26,3)`, walks twice, then starts a **39-turn tribute** at `(25,3)` in r665. At r667 she manually cancels it with 37 turns left, steps to `(25,4)`, and starts the ordinary recall stub. R668 cancels/restarts the stub without a move. R669 moves back to `(25,3)`, then r670–672 proceeds `(26,2) → (27,1) → (28,0)`; r673 reverses one tile to `(28,1)`. R674 reaches `(29,0)` and takes damage; enemy Vesper kills her in r675 and receives all **385 gems**. No Willow heal cast occurs in this interval. This was the entire difference between Willow's whole-game 429 gems collected and 44 submitted.

The global rows show 520/700 HP through r673, and a pursuer closing from the interior. Prism is dead through r672 and only returns at the opposite corner in r673. This is not a nominated missed-Prism-heal window. Those rows cannot establish which enemy position or pursuit history Willow actually knew before cancelling the tribute. Continuing a 37-turn channel may already have been untenable; the cancellation itself is not declared a bug.

Why inspect: the large bag makes a locally stationary or reversing escape decision economically consequential. The source's Willow escape comparator first minimizes current local exposure, then uses economic/home field progress only at later ties. That is a plausible explanation for a safe-for-now edge sequence that loses longer-term escape options, but the actual branch and nine candidates have not been witnessed.

## 2. Repeat pattern without a bag: post-bank boundary stay/alternation

- Replay `B/011-00elkring-12.repl26a`; SHA `e83919807ccb5ae811c5e47f6787a942c701214b665481f646315686306c717f`.
- Cached extraction `B/analysis/e83919807ccb5ae8/`; candidate physical A, Willow actor **3**.
- Request actor-own rounds **305–313**, emphasizing r306, r309–310 and r313. Death at r317 is outcome context.

Willow completes a 22-gem tribute at `(2,25)` in r305 (team score becomes 253). In r306 she manually cancels/restarts the recall stub without moving. After enemy damage she steps `(2,25) → (1,24) → (0,25)` in r307–308. She stays in r309–310, steps to `(0,24)` in r311, returns to `(0,25)` in r312, and stays in r313; the stationary turns again contain manual stub cancellation/restart. She leaves the boundary in r314–317 but dies to enemy Vesper in r317. End-of-round HP is 700 at r306, 565 at r307, 430 through r314, 295 at r315 and 25 at r316. No Willow heal cast occurs in the nominated interval.

Why inspect: this repeats the stationary/reversing escape shape on the opposite side without the 385-gem tribute complication. It can distinguish a general local escape ranking/legality issue from an unusual large-bag bank choice. It does **not** prove that a safe improving step existed, or that standing was worse under Willow's information. Prism is globally far away during the core window; a hypothetical rescue is not credited.

Both replays have **zero Willow native rollovers for the entire game** and zero native Bot Error turns. Their candidate-side single rollovers belong to Heart of Ruin (actor4 in 011, actor9 in 012). The batch's sole caught code-5 action error is a different Elk Arena game at r696 with unresolved actor; it does not explain these windows.

## Source question and minimum follow-up

Current frozen `bots/variants/willow-upstream-presence-work/src/bot.cpp`:

- `continue_tribute` (4047) may cancel an unsafe tribute when home/retaliation/prey considerations favor acting. Its `tribute_ok`, `want_home`, `attack_target` and `prey` short-circuit results must be separated; the r667 cancellation alone does not identify the reason.
- `continue_recall` (4076) cancels the routine stub unless a real keep condition passes. `recall_outruns` (3267) deliberately refuses to keep it against a recent enemy that can reach before arrival. Stub cancellation is consistent with this safety policy.
- `decide` (4884–4894) runs `willow_economy_or_escape` before local support. In its escape branch (4411–4478), the nine-station comparator prefers safe status, survival, stun avoidance, imminent/camp-exit cost, imminent damage and damage before economic/home progress; current tile is eligible and a current-tile win stops movement. No route history or multi-turn escape commitment is represented there.
- `willow_step_guard` (4323) builds the actual legal/static/blocker and threat information for those stations. A globally open-looking tile may be blocked, guarded, camp-exposed or disfavored for a valid known threat. The escape path alone may temporarily remove the guard for its least-bad chosen move; this is not permission to relax safety elsewhere.
- `start_recall` (4984) and act-tail ownership (5061) explain the routine stubs on R/B/S/P turns. They do not establish a recall-plan bug or missing heal readiness.

First use actor-own data to reconstruct the enemy beliefs, acted/readiness/channel state, current health/bag, `can_move`, channel cancellation and actual legal neighboring tiles at the core rounds. If that still leaves the choice unexplained, ask runtime for an exact, no-extra-SDK diagnostic of the **executed** branch plus existing nine station records (position, legality, safe/enemy/camp/stun, damage/imminent/camp exit burden), forced/leave/bank/shop flags, chosen candidate, and the already-used field values/tie reason. Do not add speculative path searches or evaluate all unseen enemies globally.

The hypothesis is falsified as an avoidable ranking defect if all alternatives under the actor's information were illegal, no safer or more survivable, or if these decisions used another justified branch. A source change should wait for a known-safe, materially better admitted step and must retain current strict camp/enemy restrictions. Neither window supports a generic retreat threshold change, tank borrowing, future-heal credit, or map-specific draft adjustment.

## Service/capital context and rejected third nominee

Actual outgoing heal recipients, parsed from Willow's `heal` arrays and checked against metadata totals (rounding):

| Replay | Prism | Vesper | Marcella | Heart of Ruin | Willow deaths | Willow camp damage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 011, Willow3/A | 1,074 | 3,254 | 558.6 | 3,437 | 4 | 9,513.9 |
| 012, Willow8/B | 2,238 | 2,160 | 2,664 | 1,140 | 2 | 9,994.1 |

These are service delivered to others, not health Willow received. She cannot self-heal. The two global death windows therefore concern retaining the healer and capital, rather than simply finding another missing heal. No claim is made that retaining these amounts would reverse either result (011 final A583:B1089; 012 A1375:B319).

Elk Arena also loses both ways and Willow delivers roughly30–32k outgoing healing with low team gem conversion. Its A-side Willow final-hits group0 at r40, then group1 at r43; the opponent collects group0's 72 gems/180 base gold in r52. However, opponent Ryth and Prism already cast into that area in r40. The available events do not establish that Willow or her allies could safely secure the hold; this is **not** a third nominated avoidable window. It illustrates why clear counts or healing totals alone cannot diagnose failed capital conversion.
