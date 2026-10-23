# Public Lost World loss: economic split and bounded view request

2026-10-23. Read-only review of saved extraction; no engine, extraction, script, build or gameplay changes. The CLI identifies Pantheon as A and procless as B in match `32a2bf5f-cab7-4574-b183-f3920cf50942`, group `9c0fd9aa-8e62-4011-98d6-c098ef210f67`, map `00lost_world`, engine1.0.3. It exposes no uploaded source/version. Neither roster contains Willow: A Prism/Vesper/Marcella/Ryth/HoR; B HoR/Vesper/Ryth/Marcella/Vendetta. This is a single-game loss diagnosis, not evidence against the new Willow package or proof of any current source branch.

Evidence resides in the **old worktree**, `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-prism-development/replays/public-procless-lost-world-20261023/`: `match-cli-response.json`, `loss-summary.{md,json}`, `analysis/7b5e880af2f99412/{meta.json,events.jsonl.gz,rounds.json.gz}`, and `analysis/reports/`. Replay SHA `7b5e880af2f99412b7dbc23670cc9ed98b51dbb0e763ceb1ccf4057643c82d59`. Extractor validation passes with soft earned-gold discrepancies for Marcella2 (derived840/engine1600) and Marcella8 (1488/2906). Engine gold totals are descriptive; derived payout events do not completely explain them. The corrected first tribute is **A32, B174**.

## What the aggregate supports

B won1000–720 at946. A completed more captures (69–57) and group clears (75–53), but earned2512 gold against4488 and spent2490 against4170. A led submitted gems279–44 at200 and412–44 at275. A's early clearing volume therefore did not imply comparable capital development: by250 earned gold was456–709, before the large Prism death.

The capture-event ledger contains79 gold paid to A versus791 to B; these are only recorded capture payouts, subject to the validation limitation above. A's only gold-bearing capture event is Vesper's group24 payout79 at543. B records several early capital captures, including HoR's80 gold at115,100 at130,60 at153 and90 at226. A HoR's final100 gold, Ryth's200 and Prism's400 equal their respective kill income in this replay. This supports an economic composition problem to investigate, rather than simply too few work actions. It does **not** establish that any particular gold camp was known, safe, accessible, or superior for an A actor.

The largest discrete transfer is A Prism's218-gem death at293, ultimately banked as part of B Marcella's246-gem tribute at361. A Prism collected246 and submitted0 over the whole game. Retaining gems also produced407 Focus in this episode, so zero submissions alone is not a banking defect. No earlier safe bank trip or profitable alternative is established by the global log.

## Primary own-view request: A Prism0, rounds286–293

Export these eight actor turns, including turn-start native state and all action/view refreshes. This covers the escape progression, reversal and ensuing control/burst without requesting a broad match export.

- Rounds286–288: Prism retreats21,14→20,13→19,12→19,11, cancelling and restarting recall each round. End288 HP319.2/700,218 gems. Enemy movements in the global log are locators only.
- Round289: Prism acts first, returns19,11→19,12, then Ryth7 casts from14,16 onto18,13 for100 damage and stun; Marcella8 later casts from19,16 onto19,12 for120. EndHP99.2. The actionable question is what threat origins, cooldowns, terrain and alternative endpoints Prism actually knew **before** reversing; the later hit does not prove an earlier safety error.
- Round290: native stun consumes the turn. At291 Prism casts407-damage AoE and basics Marcella for35 from19,12, then recalls. At292 it moves back19,11. Assess whether attack, move and recall choices were legal and useful from each actual view; do not assume an escape existed.
- Round293: Marcella moves21,13→20,12 and kills Prism with a basic, reset and second basic before Prism's own turn, collecting218 gems. This may be a genuine pursuit/control outplay; the view must distinguish it from an avoidable known-threat step.

This is the sole priority export. Check Prism's visible/tracked enemies, actual next-turn order, native movement/cast availability, terrain/LOS and known alternate endpoints. The source is unverified: do not attach a current-source branch explanation or claim an exact puppet reproduction. If no safe alternative is supported, record the outplay rather than inventing a repair. No opponent own-view is needed initially.

## Secondary: real HoR fuel interruption, not yet a branch diagnosis

Native statuses confirm A18 versus B1 out-of-fuel turns, no bot errors. AHoR4 accounts for17:32,35,363–375,427–428; APrism269 accounts for the other. At362 HoR moves to13,16, attacks and starts recall. At363 it manually cancels recall before OOF. It remains13,16 through375; one basic succeeds at369, so the interval is not wholly actionless. HP stays1000 through370, then falls to510 by375. At376 it attacks, dashes, moves and recalls successfully. It has no gems during this episode and survives it.

Thus the stdout chain corresponds to a material native interruption, but neither its source routine nor the whole loss can be attributed from it. If later authorized after the Prism view, a secondary **AHoR4 rounds362–364** window is enough to inspect the transition into repeated exhaustion; there is no need to export all13 stalled rounds. The global recovery actions at376 are already recorded. Keep this secondary to the eight-turn carrier-loss review and current Willow qualification.

## Completed Prism own-view review

Read the authorized eight-turn export in the old replay folder, `actor-windows/prism-actor0-r286-293.json`, independently verified SHA `3e4358ad659a55a7c6238f968affcb9a850127eccaff87cbc0d9297b3cbdd990`; adjacent provenance SHA `9875becd9d9ec90bc38fccc522f6b883dc3c012281eb5bb63f6dce583a529b9c`. These are **actor turn-start** snapshots, not end-of-round snapshots. The export has no optional before/after action snapshots, native `can_move`, policy memory or private threat fields. Snapshot cast flags do not override channels, stun or slot cooldowns. Public source remains unverified.

| Round / turn | Prism at turn start | Actual local decision and known threats |
|---|---|---|
|286 /7|21,14;319.225HP;CC/AoE7/5;recall4|Ryth16,17 (AoE2), Marcella17,18 (both slots0) visible. Cancels, walks20,13, recalls.|
|287 /6|20,13;sameHP;6/4;recall4|Ryth15,17 (AoE1), Marcella17,18 visible. Cancels, walks19,12, recalls.|
|288 /7|19,12;sameHP;5/3;recall4|Ryth14,16 (0/0), Marcella19,16 (0/0) both visible. Cancels, walks19,11, recalls; sets next-round priority16.|
|289 /0|19,11;sameHP;4/2;recall4|Same two visible enemy origins/readiness. Cancels, walks19,12, recalls; sets next-round priority19. The later Ryth100/stun and Marcella120 occur after this own turn.|
|290 /1|19,12;99.225HP;3/1;Stun1;no channel|No legal ordinary action during stun; only sets priority−64. Marcella19,16 visible, damage cooldown7; Ryth no longer visible.|
|291 /8|19,12;99.225HP;2/0;no channel/stun|Marcella21,14 visible at1700HP,50Strength,reset0/damage5. Prism casts AoE at20,13, basics Marcella, recalls, sets priority23.|
|292 /1|19,12;99.225HP;1/7;recall4|Marcella still21,14, now1258HP,reset0/damage5. Cancels, walks19,11, recalls, sets priority−64.|
|293 /8|Dead;0HP;no gems;cooldowns reset|Death already occurred before this snapshot. Shopping/priority actions are post-death; these zero cooldowns are not evidence that a live defensive cast was declined.|

### Reversal: known additional exposure, not a safe-recall witness

At289,19,11 is already within Ryth's effective ground-AoE radius5: Ryth at14,16 can target18,12 within4 and hit19,11 within the radius1 splash. Keeping recall there cannot be certified safe. Moving to19,12 **also** enters the visible, ready Marcella's direct range4; she cannot combine her walking-exclusive damage spell with a walk. Thus the reversal adds120 immediately available damage from this visible pair compared with staying, while not escaping Ryth's stun. The actual220 combined damage matches that exposure. This is a concrete one-activation comparison using known origins and rules, not a proof that staying survives the encounter or was the best complete retreat.

Terrain restricts the alternatives:18–20,10 and20,11 are holes;18,11 and18,12 hold visible live120HP gem members. Of the eight neighbors at19,11, only19,12 is demonstrated traversable by the actual move.20,12 is a static camp location whose dynamic occupancy is omitted here, so it must not be called an available safe exit. The current tile is a pocket, and enemy control of its exit is a credible outplay. Earlier path selection into that pocket may matter, but this window does not establish a safe longer escape or private threat ranking. Repeated cancel/recall alone is consequently not enough to authorize a kept-recall fix.

### Round291: evaluate the exclusive cast choice, not a missing post-cast move

The AoE was ready and legally executed; CC was still cooldown2. Prism's exclusive AoE forbids walking afterward. The subsequent basic is legal but also spends the ranged walk.407+35 leaves Marcella at1258HP, and the AoE neither stuns her nor clears the adjacent camp blockers. Marcella is stun-immune in any case. The observed sequence trades relocation for442 damage against a healthy pursuer; it does not prove an omitted legal move after attacking.

Before committing the cast,18,13 is a terrain-open neighboring candidate with no occupant shown in this export, and sits distance3 from visible Marcella21,14. That is outside her one-walk melee/reset reach; her damage spell is cooling down. This is a useful **candidate to compare**, not a certified escape: native `can_move`, full occupancy/visibility and remembered threats from now-hidden Ryth/others are not exported. No hidden enemy position should be imported from the global replay to validate or reject it. The current source could suggest how this tradeoff is evaluated, but cannot identify the uploaded branch.

The292 priority−64 takes effect in293 and places Prism after Marcella in the observed order. This creates an additional timing question, not a standalone priority fix: an earlier turn at19,11 still has camp/terrain restrictions, and an available CC would not stun Marcella. Earlier action is not proof of survival.

### Support and disposition

All four allies are identity-only in every living Prism snapshot286–292; no allied position, health, cooldown or channel is exposed. There is no Willow in the roster and no evidenced nearby heal, shield or peel. Shared/private communications are absent from the export, so neither promised help nor abandonment can be inferred. The two visible pursuers successfully combine control and burst; their successful execution should be credited even while examining Prism's choices.

The strongest supported follow-up is a bounded **pre-cast retreat comparison at291**, with289's current-versus-destination exposure as a second check, after source attribution or an independently qualified reproduction. It must observe original branch/score decisions, current native availability, remembered enemy threat inputs and existing candidate endpoint safety, before any exclusive cast. Do not execute a current-source harness and label it the historical decision without source/parity evidence. This review authorizes no new export, instrumentation or gameplay change; no bank, recall, support or priority repair is yet proven.
