# Two fd99 losses without Willow

2026-10-23. Existing published80 exports only; no new extraction, games, tooling or gameplay edits. Candidate fd99 versus a67, both four-pick P/Vesper/Marcella/HoR in both cells. These examples distinguish mechanisms, not map-selection rules. The reported four-pick4/16 and overall35/80 results do not establish one common cause.

## Rows A: conversion timing, not a demonstrated lost passing hit

Replay `041-00rows-12.repl26a`, source SHA `bb485f891944ae3ed739b91812c576d30ac48e4c0f87e5cd4b376bdb75042a16`; extracted `meta.json`, `events.jsonl.gz`, `rounds.json.gz` under `replays/willow-sustainable-crew-fallback-vs-a67-published80-20261023-v1/extract/bb485f891944ae3e/`.

Candidate loses578–1000 at1231, with **zero deaths on either team**. Candidate Prism0 has422 gems,112115 outgoing camp damage and no tribute completed; reference Prism4 collected/submitted414 and dealt118345 camp damage. Candidate teammates submitted134/243/201. Their roles and collection differ, so this is not a matched per-actor counterfactual.

Prism0 manually cancels/restarts recall at[26,7] during1157–1167 without an attack or movement. End-round HP remains1843.6, turn status is acted, and these end snapshots report no visible enemies. At1168 it moves[25,6], places a ward and continues routing. Reference Prism starts tribute1189 for42 turns; candidate starts1209 for43 turns. Candidate submitted score plus its own422 first reaches1000 at1224, **after it already began tribute**. Thus final capital1000 does not prove it ignored an already-winning bag earlier. Team communication could reveal other bags earlier; these exports do not contain the actor's received messages.

The concrete next decision question is whether the1157–1167 stationary work opportunity was still feasible before `closing` would force departure. `retaining_gems`653–687 explicitly stops retaining on winning/closing; `race_left` subtracts known/posted allied bags, and farm2319/2408 checks a candidate's clear/capture/altar horizon. A wait that can no longer finish within that horizon should not beat useful staging toward conversion. The saved events do not identify selected group, belief/respawn timing, accepted deadline or route legality, so this is a nomination rather than a proven branch bug. Do not assume cancel/restart recall is itself wrong: it is also the normal turn-ending stub.

Stationary1031 requires a fresh awake damaged group and a local working ally. Neither is demonstrated here. It might affect an earlier trajectory, but it is not a targeted repair for this observed conversion interval. Even recovering the eleven stationary turns alone would not erase the roughly21-turn tribute-completion difference under an otherwise fixed timeline.

## Hooks A: incomplete melee turns precede the collapse

Replay `067-01hooks-12.repl26a`, SHA `3e144a2bd232560b430dd536959ce81a230b9ef42579eaf684387fde9f655e48`; corresponding extract directory `3e144a2bd232560b`. Candidate loses22–1012 at962, with16 deaths versus2. This is not merely low camp-damage efficiency.

The early specific sequence is HoR3:35 attacks camp2 then moves[14,12]→[14,13];36 attacks then moves[14,14]. At end35 all four opponents are in its exported visibility list; this is prior-round observed information, **not a reconstructed actor-start view for later turns**. At37 a camp hits for60, Marcella casts120 and Vesper attacks55. HoR has no action and native `turn=6` (fuel rollover), ending495HP. At38 it dashes[14,14]→[16,16], damages/stuns Vesper and damages several camps; the turn again ends with status6. Enemy Prism subsequently stuns it. At39 it is stunned and ends33HP; camp3 kills it40. The other three candidate allies remain around[15,11]/[16,11]/[16,10] at the end of37–38, but that does not prove they could legally follow or that HoR expected them to.

The concrete issue to carry forward is completing a useful escape/engagement turn under the actual fuel limit, including whether the dash was the intended endpoint or an executed prefix whose follow-up never ran. The existing events prove the two rollovers and partial action; they do not identify the consuming function or a better legal route. A generic teamfight-policy rewrite is not justified. Use the already-running fuel/integration work to assess this concern rather than requiring a new trace pipeline now.

HoR is melee and this sequence has actual enemy contact.1031's ordinary-ranged, zero-modeled-threat tier cannot directly authorize a different HoR action here. Earlier ranged farming could change the battle, but that is an outcome hypothesis, not observed activation. These two losses support continuing the bounded stationary experiment while keeping conversion and completed-turn execution as separate concerns; they do not support claiming that it addresses the main published-panel regression.
