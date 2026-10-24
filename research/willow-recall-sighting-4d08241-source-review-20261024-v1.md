# Recall + sighting: integration source review

2026-10-24. **Source-ready for the combined build/comparison; no concrete integration blocker found.** Source-only review, no build, test, game, extraction or gameplay edit. Component evidence does not establish combined behavior or strength. Willow-first manipulation batches are excluded.

## Verified exact union

Child `bots/variants/willow-recall-sighting-4d08241-work` manifest SHA/aggregate is `29ac1251ddc63c1b3e824d9c1d6182df57890e62b3757d5e362fe15be3a91e60`; all29 manifest entries independently verify. Full patch `research/willow-recall-sighting-4d08241-source-v1.patch` SHA is `83433f94747168e0b64eb7223022944a61a12db8bf9ede147e195c1fa0fe660e`.

Direct byte comparisons confirm:

- `bot.cpp` equals the reviewed finishing-recall child (`781fe364…` aggregate), file SHA `12b287870f0e516829ccd0ce47765391e273729af1529fdc3df2f719da060d46`.
- `comms.cpp` and `comms.h` equal reviewed sighting v3 (`a439a6c2…` aggregate), file SHAs `c048d09fd718e21b3d46258533d157ee4a196d40a20e037444ae2bfac9a1b77a` and `dd7501edf853dc00cf3d6c5535eb5dd54a62c7e177e314868a82385c41fa0249`.
- The other26 files equal frozen f599 parent (`f599a31faa0251321beb97a726918286e266218ceb3e183b8271e41c5c84718c`). No integration-specific policy or interface change was added.

## How the components interact

The unchanged turn pipeline receives comms before deciding (`main.cpp:125–139`), while publication happens after the actor's decision (`152`). `World::note_sighting` (`world.cpp:1271–1283`) updates an unseen living enemy only for a newer fix; it does not overwrite direct current visibility. Position, health fraction and tracked possibilities change, but the message does not convey a new exact cooldown or complete combat snapshot.

These beliefs legitimately affect the same turn's pack boxes (`bot.cpp:2641–2707`), nearest-enemy payout relaxation (`2810–2818`), threat assessment and `recall_outruns` (`3334–3343`). A fresher nearby sighting may make the actor want home, make payout relaxation cease, or make a recall fail its interception check. A corrected farther/weaker fix may do the reverse. None of those directions is an integration defect by itself. The scalar at `want_home:2854–2861` records the pack suppression actually evaluated from those beliefs; it is not inherited from a previous actor, turn or message.

The new recall keep (`4176–4186`) still needs normal home=false, suppressed pack, an early-arriving held-capture recall, a non-winning top-up and the existing safety/tribute/interception checks. It does not make improved threat information advisory or bypass it. Ordinary home=true and game-ending intervention keep precedence; a failed contextual keep retains the normal cached home answer. Fresh sightings may therefore prevent the component's known738 keep or cause a different earlier trajectory. Identical behavior to either standalone component is neither expected nor required.

No additional cache-invalidating hook is needed for this union: receipt precedes first decision queries; pack boxes are keyed by round, and normal mid-turn decision re-observation reconstructs Safety and forgets pack boxes (`bot.cpp:2710–2718`). The sighting sender's selected native confirmation does not mutate World. Its optional post-decision observation remains the already-reviewed component behavior, not a new recall-phase refresh.

## Cost, protocol and qualification limits

Recall scalar plumbing adds no queries; its rare new keep path runs existing checks. Sighting arbitration retains the reviewed bounded roster work, optional permitted observation and selected native confirmation. Better-delivered enemies can also activate existing pack/subset or threat work that previously did not run, so combined fuel cannot be inferred merely by adding standalone measured means. No new simulation, field, allocation or fuel gate was introduced in the union.

All teammates in a combined run must use the same new sighting wire interpretation. Do not inject a combined actor among old-protocol teammates or treat old raw sight-count bits as new logical fixture state. Existing component fixtures qualify their respective mechanisms; combined native comparisons must establish actual first divergence, errors/rollovers and useful action consequences. Parent-reported unchanged outcomes from recall extensions do not substitute for that combined evidence. No additional policy or test framework is requested by this review.
