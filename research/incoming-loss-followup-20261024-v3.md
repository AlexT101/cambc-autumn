# Incoming ranked losses: the Willow-first anomaly recurs

2026-10-24 UTC. **Twenty new ranked games finish 8–12, but five losses belong to a separate Willow-first batch. Normal Prism-first play finishes 8–7. Opponent adaptation remains unproved; draft execution/deployment identity is the most urgent new question.** The initial intake used no engine; the subsequently authorized 100-step Gemfight prefix is recorded below. No match, submission, bot build, native summary or gameplay change was performed. EXPERIMENTS and previous reports remain untouched.

Read the Cambridge Battlecode rules, the initial adaptation review, follow-ups v1/v2, and `incoming-loss-own-view-review-20261024-v1.md`. Evidence root is `replays/incoming-loss-followup-20261024-v3/`; `SHA256SUMS.txt` pins this intake and the three downloaded replay archives/raw files. CLI SHA-256 remains `69617aa6a074415bd8ba8e254d1584df3392d95d1f9e2e2d46db66ff6e187171` at the pinned 3.0.5 path. Team UUID remains `547efb5b-57e5-4355-8501-3b331f506d62`, willow best girl.

## Frozen intake and comparison

One read-only `cambc matches list --team me --kind ranked --limit 100 --json` finished at **03:41:38Z**. Its oldest creation is 00:30:14.008Z, below the previous cutoff 03:00:12.590Z. `new-ranked.json` retains the 20 creations after that cutoff through **03:40:12.979Z**, all finished. `prior-ranked-190.json` deduplicates the original 150 plus v1's 25 and v2's 15 by match ID; `duplicate-match-ids.json` is empty. This is a creation-based freeze, not a recheck of previously unfinished games. No new unranked or fixed public samples enter the rate. In particular, the older Big World public/UR byte-identical replay remains one behavioral sample.

| New group | Our side | Record | Our ordered drafts |
|---|---|---|---|
| Fish, 03:10 | A | 1–4 | Usual Prism-first map-sized drafts |
| policy wonk, 03:20 | B | 4–1 | Usual Prism-first map-sized drafts |
| :3, 03:30 | A | 3–2 | Usual Prism-first map-sized drafts |
| Univardisty of Shingtonwash, 03:40 | B | 0–5 | Willow-first, varying later picks |

The normal 15 contain nine five-pick `[5,1,6,7,11]`, three four-pick `[5,1,6,11]`, and three three-pick `[5,1,11]` games. Neither the pooled 8–12 nor normal 8–7 is a controlled rate change against v2's 12–3; opponent/map/side mix differs and both teams' submission/source identities remain unknown. Authored Khaos_v33/server44 is not a live attribution.

## The five anomalous losses

All five share group `de606e1f-49c5-45b4-b8c7-dd2ae874113b`, creation 03:40:12.979Z, our physical B. Numeric entries below are **draft types**, not actor IDs: 0 Ryth, 1 Vesper, 2 Vendetta, 3 Cassi & Issac, 4 Stellar, 5 Prism, 6 Marcella, 7 Willow, 8 Ren, 9 Varg, 10 Tavi, 11 HoR.

| Map / match | Our ordered draft | Opponent ordered draft | Our actor IDs implied by roster |
|---|---|---|---|
| Elkring `1da0fc56-abba-4783-b02d-9b829caeab36` | `[7,4,9,10,8]` | `[6,11,2,7,8]` | Willow5, Stellar6, Varg7, Tavi8, Ren9 |
| Gemfight `32571b83-f603-4939-bdd5-79cc17991c7f` | `[7,10,4,8]` | `[6,11,0,7]` | Willow4, Tavi5, Stellar6, Ren7 |
| Rushbait v2 `97a5cb2d-a51e-4cca-b7a8-6e488cd32ede` | `[7,10,3,8]` | `[2,0,3,4]` | Willow5, Tavi6, Cassi7, Issac8, Ren9 |
| Broken Curve `086a8a0f-854d-4f5d-a9cb-c3c02040e32f` | `[7,9,10]` | `[6,11,2]` | Willow3, Varg4, Tavi5 |
| Packs `98493b50-42d0-4cce-ab9a-d63d9a359000` | `[7,9,8]` | `[6,2,7]` | Willow3, Varg4, Ren5 |

The earlier Claudus group at **23:30:09.534Z** was also five losses, all our B. Its maps/drafts were Split `[7,9,3,4,8]`, Gemfight `[7,10,4,8]`, Corridors `[7,4,3,8,9]`, Lanes `[7,8,10,9,4]`, and Broken Curve `[7,9,10]`. Thus **Gemfight and Broken Curve repeat our exact anomalous order on the same map and side against a different opponent**. Prior IDs are `1d2fdf2d-eeef-4256-8d5a-2554a818fd58` and `f0aa7fc1-8452-4f61-805c-67bdb2078103`. The full ten rows are frozen in `anomalous-draft-comparison.json`.

This recurrence makes opponent-specific counterdrafting insufficient to explain our own roster changes. A deterministic missed-pick fallback, different selected artifact, or deliberate draft policy are hypotheses. The rules say a draft turn ending without a pick makes that and all later picks random and stops further draft-bot calls. The existing native audit for the older **Lanes** anomaly records zero own draft rollovers/errors; that neither proves accepted explicit picks nor rules out a voluntary missed pick, and it says nothing native about these new matches. Repeated arbitrary drafts do not certify identical code or the engine's random seed.

Gemfight/Broken Curve ZIPs contain replay, own stdout/fuel/debug files, with no submission manifest. Gemfight `matches show --json` exposes the same public fields as history and no source identity. Printable Gemfight stdout only records a **play** turn rollover at r126→127; Broken Curve has no printable diagnostic. These are not native draft audits. File-only inspection of frozen Khaos_v33 finds `test_draft=false`, a Prism-first default, and no Willow-first row even in its test-composition tables (`draft.cpp` SHA `2efb8a0cf7c10789c253e738f8659724672987dbc4fce4c2c60fc94c0d0dd9d2`, `params.h` SHA `3234d52aea6001674030d35e2f05c646da72f23dc6d6a929ae5e66844b08390f`). Merely enabling that file's `test_draft` is not a supported explanation. Do not patch frozen v33 or claim it ran here.

## Normal-roster losses and controls

All Fish and :3 ordered opponent sequences already occur in the 190-row history. All five new Univardisty sequences are absent from that freeze, but this opponent already varies drafts heavily; own-draft changes and different map comparisons prevent an adaptation claim. The other new sequence is policy wonk's Broken Curve `[11,6,1]`, a game we **win**. Novelty is defined by opponent UUID plus exact ordered draft, not by code identity.

| Fresh result | Relevant prior result with both ordered drafts unchanged | Interpretation |
|---|---|---|
| Fish Split A loss `76da1856-5d39-4179-86b0-01f7bedb30da` | A loss `a6ccef40-adb2-49f3-ae2e-dc6435304e5a` at20:30; B win `45564bf1-1e9f-4ec6-aba5-39ffc6269090` at00:10 | Repeat same-side failure; opposite-side result remains a confound. |
| Fish Corridors A win `6f0af115-aee0-4bf0-b66e-2464cd2a67d6` | A win `e4210e03-ab61-422d-8305-4ab3d07cd0dc` at21:40 | Matched-map/side/draft control recurs. |
| Fish Gold Rush A loss `58a8288d-a729-4106-81ed-6dfbf76c190c` | B loss `776d2ecf-8c02-4c04-8bdc-6307f887452d` at01:10 | Loss occurs on both sides; source/behavior change unmeasured. |
| :3 Concentrated Wealth A loss `1ac0c6a9-3cdb-439a-923a-a74cda06a87e` | A loss `9c18044a-b821-4984-a9de-8bfb87ece39b` at00:30; B win `739c59ac-e837-4cd7-bf24-6c765eafa552` at22:10 | Another recurring map/side split. |
| :3 Gold Rush A win `22f78beb-646f-4a30-95e6-7f9a0bc19a4e` | B win `2c2dff95-ef23-4079-a6d8-2ecbb42888dd` at02:30 | Same own three picks can win this map against another opponent composition. |
| policy wonk Starvation B win `d4ea9f48-744b-42ef-9288-5fe1c41a929a` | B win `be2e0f8f-7d64-4419-8b7a-bdb5de073a7e` at22:00 | Same-side control recurs. |
| policy wonk Fracture B win `e4e4be73-c5de-49b4-b504-ac342b27d818` | B win `ec179bfd-92bf-42a7-be72-1fc6f0a01889` at23:02 | Same-side control recurs. |
| policy wonk Contest B loss `f6e5b9e9-fb5a-4656-b433-20b87c24c353` | B loss `d847664f-7ce2-4b94-bd2b-852482635603` at23:02 | Same-side failure recurs. |

Fish Shortcut and Rushbait losses, and :3 Rushbait loss, have no same-opponent/map prior in this freeze. New map pairings are not behavioral-change evidence. Gold Rush's :3 win is not an action-level control for the Fish loss: enemy rosters differ (`[1,2,10]` versus `[1,11,2]`).

## Known-info consequences and precise worker handoff

No new frame-level cause is asserted from results. Existing own-view evidence still establishes: Gold Rush Vesper's nonlethal exchanges beside a visibly enemy-occupied cleared gold group; Starvation Prism's movement-spending basics before pursuit and a heal readiness/range mismatch; Fracture Willow's real heal followed by camp/pursuit exposure and recall cancellation/restart. It does not establish that a teammate ignored a ready heal, a safe escape, or the live source branch. Farm's known camp-phase survival witness remains distinct from these cases. Do not turn fresh totals into blanket aggression, banking, Focus, Health, permanent-follow or map-name gates.

**First pending task: draft diagnosis, minimum one new replay.** Use `raw/anomalous-gemfight/replay.repl26a`, SHA `42dd558e9a9f66ce78aa5204067d41ddf5f85310620cf3f0aa3405d11e3ba71d`, our B. Ask Luna for a fresh data-only wrapper with source/submission unknown, map `maps/00gemfight.map26a`, then existing `audit_native_status.mjs --compact` under the sole heavy-worker grant. Inspect own draft rounds **0–3**, accepted pick events, native rollover/error/end status, and whether the bot is called again after a missing pick. The existing status counter alone counts errors/rollovers; it cannot distinguish clean explicit picks from a no-pick yield. If its outputs lack accepted picks/termination evidence, Luna must prepare the smallest bounded exporter extension before any execution. Do not infer all five matches from one audit. Existing older Lanes audit is a comparison, not a replacement.

If a second draft witness is necessary, `raw/anomalous-broken-curve/replay.repl26a`, SHA `408aaecc3e3ff2e53fbf6bbf557de974f5421a49a2d56cb2722d0257c2311f9e`, our B, draft rounds **0–2**, adds a three-pick same-map/same-own-draft recurrence. A source identity receipt is still needed to connect either mechanism to code.

**Second pending task: one bounded Fish economic window.** `raw/fish-gold-rush/replay.repl26a`, SHA `47970b1c959f77498dafd325b8bc2a272252ac39f35fc9045e3febd2e4a7a29b`, our A/Vesper actor1, **rounds10–24 inclusive**, via the existing own-view exporter and `--public-source-unverified`. This matches the existing Gold Rush opening observation interval, not a claim that the same events occurred. Inspect actual ordered move/dash/basic/recall actions; visible camp state and holders; attack/move/cast readiness; contact and clear-to-occupancy conversion. Compare against v1's source-unverified Vesper1 opening, retaining the different opponent draft. If contact/clear timing lies outside this window, report that rather than widening arbitrarily or inventing an alternative. Known legal occupancy versus nonlethal combat is the hypothesis; no fresh source-proven gameplay patch follows yet.

Root was notified of these paths/hashes and queued the minimum Gemfight audit after the current worker. This report ends at the frozen intake; no additional engine, summary, match or submission was run.

## Authorized Gemfight draft-prefix follow-up

After the coordinator released the sole heavy-worker slot, this exact existing-tool command completed with exit0, approximately0.087 seconds, from the repository root:

```sh
nice -n 19 node tools/replay/harness/dumpsteps.mjs replays/incoming-loss-followup-20261024-v3/raw/anomalous-gemfight/replay.repl26a 0 100 > replays/incoming-loss-followup-20261024-v3/metadata/draft-prefix-v1.log 2> replays/incoming-loss-followup-20261024-v3/metadata/draft-prefix-v1.stderr.log
```

The end bound is exclusive: exactly snapshots0–99, with all four draft rounds complete by snapshot16. Tool SHA `a7551a5558277171903d2bd76d253a917dd8e897562633d8957a0bd4630d4e93`; imported `engine.mjs` SHA `f0f3c870c5331b13bad2f0950fed7fa09d65235a9b8f77d6867072b62c99c2c6`; replay SHA unchanged above. Output SHA `b0de021e0e966ef8f46dc50265e3c3b2766388807bcf72e5214e5b24f6dc7c94`; stderr empty, SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Draft phase12 contains eight alternating **Input → Draft champion** pairs, and no End turn, Turn rollover or Bot error. Our B's input snapshots3/7/11/15 precede draft events4/8/12/16, covering rounds0/1/2/3. The snapshot header after a pick identifies the next team/round; do not assign that completed pick to its post-action header team. This is stronger than a zero-error count and shows no visible missing-pick termination in the draft-step sequence.

However, `dumpsteps` does not print raw input kind/payload, chosen champion, or a draft-bot-disabled/fallback marker. It therefore cannot by itself prove the replay's draft event was an explicit submitted bot action rather than a materialized automatic choice. A precise file-only helper request was sent to Luna: decode only the first16 replay inputs, report kind/payload and pre-action team/round, and identify any available fallback marker. If the recording format omits bot-call provenance, that limitation must remain. Neither new whole-game audit nor Broken Curve engine prefix was run. The heavy-worker slot was returned immediately after this single prefix.

### Subsequent bounded helper evidence supplied by Luna

The coordinator-authorized helper results are in `provenance/incoming-loss-draft-prefix-helper-20261024-v1/`, outside this intake manifest. Receipt SHA `624fa2018188b1ad870323ee894f6fc41564e610a9aa24d4c33d052b42065fbb`; corrected Gemfight `run-gemfight-v2/draft-prefix.json` SHA `c0236ef5d3c2ddb2d2c3d7ee20370cd72596f345f2ace5617049935c81d7bead`; Broken Curve output SHA `4f98aa81729407c1470baca63f84d80e9a547516799e4433a0f6961c4b78b841`. Hashes independently checked. The earlier exploratory `run-gemfight/` output is invalid for input/pick delta attribution; use the corrected v2 output only.

Gemfight records17 draft steps, eight input/pick pairs each advancing exactly one team's draft count; own B picks are `[7,10,4,8]`. Broken Curve records13 steps and six such pairs; own B picks `[7,9,10]`. Neither prefix contains a draft rollover/error. The helper compares the post-input draft state against the immediately preceding snapshot, recovering accepted draft changes rather than guessing from the next header's team. This strengthens evidence for a clean recorded draft sequence in these two matches. Native snapshots still omit raw payload/bot-call provenance; source identity and explicit-versus-automatic origin remain unproved. Do not generalize these two clean prefixes to the three uninspected games or label an engine fallback as confirmed.

## Fish Gold Rush own-view follow-up: approach oscillation, not the earlier duel

The coordinator-authorized bounded export is now complete. Match `58a8288d-a729-4106-81ed-6dfbf76c190c`, physical A/Vesper1, rounds10–24, remains **source/submission unknown**. Own ordered draft is `[5,1,11]`; Fish's is `[1,11,2]`. Read-only review used `metadata/public-source-unverified-goldrush-10-24-v1/actor-windows-v1/goldrush-actor1-r10-24.json`, SHA `f21674a4f514062d66c0a97cbec30339d29530c2d3d180cf0271ff4323e00b48`; enclosing `receipt.json`, SHA `e2e4aba6fa9e3da139fd62227bea2ddd90ff0efcdc7a72f798880bde65623355`, records the exact exporter argv and replay/map/tool hashes. These nested outputs are separately receipted, outside the original intake manifest. No additional engine pass was run for this review.

Vesper has1000/1000HP,55Strength,100Focus,0gold and no items throughout these15 start-of-turn observations. Every turn begins with recall timer4, then cancels it and starts recall again after the listed action. Read the Cambridge Battlecode rules: ranged walking/basic attack share the movement resource, recall may legally start after acting, and capture needs all group monsters dead followed by uncontested occupation of an actual camp tile. The recall pattern therefore does not itself prove waste; the successful intervening actions matter.

| Round | Own position and successful actions between cancel/restart | Own-view evidence relevant to the choice |
|---|---|---|
|10–11|`(12,9)`; basic/reset/basic10, basic11|No enemy position visible. Camp18 at `(13,12)` falls from120HP at10 to10 at11; export does not identify basic targets.|
|12|Walk `(12,9)→(13,10)`|Other group1 members remain visible/alive.|
|13–17|Hold `(13,10)`, one basic each round|Known group1 camp16HP90→35, camp33HP120→65→10 across later observations. Fish Vesper3 stays `(16,16)` at1000HP; HoR4 `(15,18)`, Vendetta5 near `(16,17)`.|
|18–19|Hold `(13,10)`; basic/reset/basic18, basic19|Camp11 `(14,13)`HP120 at18,10 at19. Camp4 `(13,14)` remains120. Fish Vesper moves southwest toward `(14,17)` by20; Vendetta reaches `(13,18)`.|
|20|Walk `(13,10)→(13,11)`|Camp4 remains visibly120HP, distance4 before the walk.|
|21–23|Walk `(13,11)→(12,10)→(13,11)→(12,10)`|Camp4 remains visibly120HP at each start. At21 and23 it is geometrically within ranged distance3. Vesper3 remains `(14,17)`, Vendetta5 `(13,18)`; HoR4 is also visible at `(12,17)` from22. All visible enemy HP values are1000.|
|24|Dash `(12,10)→(10,8)`, walk `(9,8)`|Fish HoR4 is now visible `(13,15)`. Camp4 has only a static-map row; this export does not certify its death or current state.|

The strongest observed issue is **two repetitions of the same approach/retreat edge with no damage taken or camp4HP reduction during20–23**, followed by retreat24. It nominates a mismatch between approaching a farm objective and evaluating danger once in attack range. It does not establish that attacking was safe, that the same threat field was used in both directions, or that either move was caused by a particular source function. Initial attack-ready flags are false while recalling; the export lacks post-cancel native `can_move`, hidden-blocker attempts, shared claims, and internal goal/threat scores. Geometric attack range is not a complete legal/safe counterfactual. Likewise, `static_map_only` for an earlier camp is not a certified death event.

This differs materially from the earlier source-unverified Gold Rush window against prism best girl: there Vesper reached `(15,13)` by17, dashed to `(17,15)` at18 and exchanged attacks with an enemy holder, losing HP by20. Here he never reaches that area during10–24 and never fights a visible enemy in the exported actions. Our HoR2 also remains around the western approach in this window instead of the earlier group's occupation. The common map/side/own draft is useful context, but opponent composition and unknown source identity prevent treating these as controlled before/after trials. Do not claim the Gold terminal-value candidate fixes this Fish loss; its intended cleared-group combat state is not witnessed here.

**Next narrow source-known question:** can the selected farm objective keep choosing `(13,11)` from `(12,10)` while the post-approach attack/danger policy immediately sends Vesper back? Preserve threat safety and test useful progress, not simply fewer retreats. Exact discriminating public frames, only if a worker grant is later issued, are actions2323–2325 (round21) and2547–2549 (round23), with pre/post cancel and move snapshots. A source-matched trace would additionally need selected goal/group, proposed basic target, native post-cancel readiness, failed/revealing attempts, and risk/route values at both endpoints. Public source identity must be recovered before attributing this to cb61eaa, Goldv2, Band or any released build. The existing window suffices to nominate this question; no further extraction or gameplay change is requested merely to extend the narrative.
