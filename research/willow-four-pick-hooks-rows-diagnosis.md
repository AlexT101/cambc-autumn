# Native four-pick Willow: Hooks and Rows

2026-10-23. Existing exports only; no engine, new extraction, or gameplay changes. This compares fixed P/V/M/W `157f5f79…` against P/V/M/HoR `a00fff45…`; the sole source difference is the fourth draft pick. Actual native rosters are audited in `replays/willow-four-pick-157f5-vs-a00fff/batch-run-01-release-published4p/actual-native-rosters.json`. Unlike the earlier public policy-wonk/Fish losses, source association is known. Four games nominate mechanisms; they do not establish a selector.

## Evidence binding

All paths below are relative to that batch. Each `analysis/<hash-prefix>/` contains `meta.json`, `events.jsonl.gz`, and `rounds.json.gz`.

| Replay | Analysis prefix / replay SHA256 | Candidate result |
|---|---|---|
| `013-01hooks-12.repl26a` | `04283153a9fc5049ac42e255981c66d7cebe136198ce2b14c37f751502c2459d` | A 1012–264, r1406 |
| `014-01hooks-21.repl26a` | `8dea754410e813c2cd0dbed942783d53ce5a7f47e1c55861ae7768ef31439032` | B 1012–22, r983 |
| `007-00rows-12.repl26a` | `184099596fb8d036ae3a3cab1fd85b385979035105346f842fc64eea10f7f81c` | A 434–1000, r1231 |
| `008-00rows-21.repl26a` | `c1bbb31ad9286642476a167a68d4774c575d84d027eaed03b5614ed8747641ea` | B 434–1012, r1258 |

Use physical team and actual roster from each metadata file: batch `results.json` winner is a bot index, whereas the analysis winner uses physical team. Round-series scores are indexed `[team][round-index]`. Global events establish actual actions and outcomes, not the complete information available to a decision.

## Rows: conversion race, not absent combat control

Both sides dealt **zero champion damage and suffered zero deaths in both Rows games**. Candidate collected 1012 versus 1000 gems as A, and 1019 versus 1031 as B. Candidate Prism held 578/566 at the end, submitted none, and dealt 133991/145044 camp damage; reference Prism collected and submitted 414/491. The candidate had substantial farming output, but its largest bag finished conversion later. Missing HoR combat burst or control cannot explain these particular losses.

| Candidate side | First global team capital ≥1000 | First public score + own Prism bag ≥1000 | Prism tribute start | Scheduled finish | Enemy win |
|---|---:|---:|---:|---:|---:|
| A | 1178 | 1199 | 1198, bag578, 58 turns | 1256 | 1231 |
| B | 1217 | 1228 | 1211, bag566, 57 turns | 1268 | 1258 |

“Global capital” includes other allies' bags and is not a claim that Prism knew all of it then. In A, Marcella's r1178 capture raises team capital to1000; she starts her19-gem tribute1197. Prism starts before that payout, then keeps the long channel. Reference Prism starts1189 with414 and wins on completion1231. In B, reference Prism starts1194 with491 and completes1244, bringing its score to986; HoR's26-gem tribute starts1255 and wins1258. Candidate Prism already channels from1211; Vesper's later12-gem capture1217 and payout1228 complete the candidate's winning capital. Neither losing Prism demonstrably ignored an already-winning personal bag.

Exact source: `bots/variants/willow-audit107-ready-heal-work/src/bot.cpp:421,653–688` subtracts public score, own native bag, visible pending ally tribute, and then visible/posted other ally bags for the race estimate. `closing` compares own-team estimated remaining time with altar walk + full tribute +20. `world.cpp:1958` estimates the ally tribute rate over the latter half of elapsed play. This is an own-team completion estimate, not a forecast of hidden enemy bags. Earlier banking needs its own information/cost witness; final bags alone do not establish a bad branch.

A more concrete nomination precedes the final channel: A Prism0 stands at19,5 from1137 through1158, cancelling and restarting a fresh recall every turn. Group0 pays1143, then has35 respawn turns still remaining at1158. Prism stays940/1000HP with no further damage. Willow3 is nearby through1147, completes recall1148, and leaves; Prism first walks20,4 at1159. No blocked Prism action appears in that interval. Capture holding explains the initial turns, not automatically the subsequent15 rounds. Ordinary farm waiting, stale work, and route/closing transitions remain alternatives. The60HP deficit is not evidence of valuable recovery, and the duration exceeds the bounded four-turn local recovery loop. Minimum nominated own view: actor0/A1155–1161. Need current known camps, claims, route and channel state before naming a defect; an exact branch witness would be needed if that view remains ambiguous.

Even eliminating all15 post-payout stationary turns would not alone erase A's25-round scheduled-finish deficit; a different route could change more or less, but is not established. Replacing the tribute-rate estimate with total capture-capital growth is also unjustified: once Prism leaves, its own high-output farming stops. Any eventual estimate of teammates finishing the remaining win must exclude that departing carrier's future production and use information actually known to it.

HoR's economic role still matters: reference HoR dealt37453/45983 camp damage and submitted250/149 gems versus Willow15890/15661 damage and39/27 gems. Willow healed8216/5529 and candidate Prism's output exceeded reference Prism's. These totals show redistribution, not the marginal productivity caused by healing or proof that HoR would independently recover the candidate's late conversion.

## Hooks: actual early Marcella service, followed by productive work

Willow's first two heals target Marcella in **all four games**: Hooks A r28/36, Hooks B24/32, Rows A16/24, Rows B16/24. The fixed Prism formation does not prevent ordinary early Marcella healing in these examples. `local_support` uses Prism eligibility but enumerates every eligible ally (`bot.cpp:4880`); generic `heal_ally` also ranks all allies (`self_abilities.cpp:423`). A persistent-workmate proposal must demonstrate missed access beyond this existing behavior.

Hooks B gives a particularly clean productive sequence. Willow7 at18,20 heals Marcella6 at15,20 for360 on r32 step4182, then still basics camp3 for55 (4183). Marcella attacks camp5 twice with reset that turn (4208–4210), continues basic attacks33–37 without a completed recall, clears it37 (4871), and captures43. Willow's heal costs that turn's cast and therefore any reset opportunity; it does not cost her stationary basic. This is actual service followed by work, not yet a counterfactual proof that Marcella would otherwise have recalled. Minimum nominated own view: Willow7/B30–37 to certify current visibility, readiness and competing output.

Hooks A cautions against a simple “healing beats burst” explanation. Willow heals Marcella240 at28 and360 at36; reference HoR7 nevertheless kills Marcella at13,12 on44 with dash/cast (step5744, allied assists), and later captures the group2 Marcella had cleared (r97,22 gems/108gold). The candidate ultimately wins with6 deaths versus16 and141817 versus39143 camp damage. Hooks B wins with0 deaths versus13 and127400 versus16875 camp damage. Those full-game differences are compatible with sustained support and territorial conversion; they do not isolate a single heal or invalidate HoR's real early kill/capture contribution.

## Draft and next-step implications

Public map exports supply legitimate draft-time features: Hooks is31×31 with one altar15,15 and the gem-bearing Elk groups clustered around the middle; Rows is50×50 with two altars15,16 and34,33, three mirrored outer Wolf rows, and a central470-gem mixed Monolith group. These are known static facts, not a rule to select by map name. Compact overlapping work areas could make one healer service multiple workers; separated farming routes and long conversion trips could reward independent fourth-worker throughput. Verify path distances, safe service stations, actual work overlap and conversion time across held-out maps before fitting that hypothesis. Previously revealed enemy picks are usable; the opponent's simultaneous final pick is not.

Priority: finish the fixed-arm qualification; inspect the two nominated local windows; pursue the concrete Rows work/conversion delay if known-state evidence supports it. Do not replace the current all-ally healing with a new permanent Marcella pairing based on these games. Forecast injury from visible current work and nearest-target geometry may legitimately value a formation station, while safety admission must still use current health and cannot borrow a future heal. No new mailbox, item policy, or draft selector is justified by this four-game slice.

Qualification update from root: fixed arm finished **136–194/330** (published8–8, gen1023 70–80, gen1024 58–106), caught errors0. Thus this universal HoR replacement is rejected; the Hooks wins cannot support a named-map selector. This does not reject Willow's five-pick role alongside HoR, nor shared support/farm/conversion improvements. A different displaced role needs its own opportunity-cost argument before another arm.

## Actor-own follow-up

Both authorized Release/default-fuel windows are now inspected. Setup/source pins: `replays/willow-four-pick-157f5-vs-a00fff/actor-window-export-setup.json`, SHA256 `3a7166d2f4610d04748e068c11701ddb80f86ed5e96f49e06f6853034ff50ba2`. Window directory is the batch's `actor-windows-four-pick/`.

- `rows-a-prism0-r1155-1161.json`: SHA256 `7dbbfbc58958f48c1e90565dedb914027017091793cf8e9bcfac72f6b0298159`; replay payload `035812f28c7e7a82903d7d3c5af36c542b0eef3118641e105ba6c110d448a089`.
- `hooks-b-willow7-r30-37.json`: SHA256 `d246e8ed0b9c2e2f950300e912860c0cfab17edc936447fa5777afab27eb9638`; replay payload `a728a8b1159a1ad9932c3d0584039f58079189a4c34883485976f09c1f21ca03`.

Rows: at the start of every observed turn1155–1161, Prism has940/1000HP,578 gems, both spells ready, and a fresh recall with timer4. Only Marcella is visible: full2500HP, walking20,4→26,4. Willow and all enemies are identity-only. Prism cancels then restarts recall1155–1158;1159 adds the successful move19,5→20,4, followed by eastward steps1160–1161. The exporter does not expose native movement readiness, the selected group, comms claims, remembered camp state, or altar-usability evaluation. Its `attack_ready:false` is a start-of-turn channelling snapshot, not proof of an attack already spent that turn. `turn_end` is ordinary end-turn throughout.

The absent Willow rules out a newly admitted visible-healer recovery: `local_support` at4853 returns false when its fixed healer is invisible; any historical recovery/reentry state can request retreat, not a new indefinite recovery station. A60HP deficit also fails the ordinary heal-worth threshold at94% health. Do not call the repeated recall itself a defect: `start_recall` at5207 deliberately starts a free recall every end-turn and cancels next turn when work remains. Its repetition is a symptom of no intervening work here.

Ordinary profitable waiting is also unproven. Global group0 is respawning with38 turns left1155 and34 left1159, while farm's `max_wait` is5 (`params.h:62`, `bot.cpp:2235`). If that state is correctly remembered and fully evaluated, the local group cannot be the newly selected nearby wait. Other candidate groups, remembered work/partial evaluation, and route choice remain possible. Marcella occupies the eventual first step20,4 at1155, but it is free by1156; that one occupancy does not explain all four observed standing turns. No rejected Prism move is logged, so there is no demonstrated native hidden-blocker failure.

A suspected deadline omission was checked and **not found**: although retained bags omit immediate bank economics from `known.walk`, `too_late` at2251 separately populates `known.to_altar` and uses it for the full capture-plus-tribute deadline. Both claimed and ordinary candidate paths call it. A truly unreachable altar or incumbent fallback can still bypass a useful deadline, but neither is established here. Do not patch route pricing on the mistaken premise that every retained candidate skips this check.

Smallest remaining witness is a paired branch record for1158 and1159: final decision, `closing/retaining`, `farm_group/claim/crew`, and—only if farm executes—evaluation count, selected group/value/wait and attempted walk result. This separates no-admissible-work/early fallback from selected waiting and route failure. A move-only intervention is not justified until that distinction is known; no new trace implementation or runtime was performed.

Hooks: r32 Willow knows Marcella at15,20 with480/1200HP, heal ready, and distance3; Prism at17,22 has520/700HP, and Vesper is full. Marcella's missing720 supports the full360 heal; Prism's missing180 is below the216 normal worth threshold. Willow heals, then basics, and sees Marcella at840HP next turn. **Correction to the generic opportunity-cost description above:** Willow's reset has3 turns remaining at32, so this particular heal displaces no ready reset or movement. It consumes the cast allowance, but the available basic is preserved. Marcella's next observed HP is660 at37 after continuing the clear. This establishes informed useful service and continued work; it does not prove that subtracting the360 heal alone would have forced recall (the corresponding raw remaining HP would still be300 before behavioral changes).

Willow herself is340/700HP at32 after taking camp hits and sees the approaching enemy HoR at15,12; she does not move to obtain this heal. Thus the example supports stationary all-ally service, not permission to relax safe-station admission or assume a frontliner will continue tanking. No new permanent Marcella pairing or recipient protocol follows from it. The earlier negative recipient-rendezvous result remains negative.
