# v47 generalist drafting: map economy and revealed-prefix experiment

2026-10-24. Source/design only, after the current hop/connected-escape work. No draft implementation, new map extraction, browser, build or game by this reviewer. The user wants a generalist draft with economy-sensitive edge cases and opponent adaptation; Willow-first ladder-manipulation batches are excluded. This is a small candidate experiment, not a fitted winning selector.

## Rules change the proposed binary tests

“No gold clusters” is not “no Vesper income.” Wolves/Elks/Golems supply40/90/160 base gold, Monoliths300; Vesper's33% bonus applies to eligible income, not merely gold-cluster rewards. Capture gold belongs to the actual payout holders and splits among them. No specific champion is promised it at draft. Our extracted Gem Fields map has **zero gold clusters but600 ordinary base gold** from four Elks/six Wolves. Its known replay has substantial enemy Vesper and Marcella income. Removing Vesper solely for missing gold clusters is contradicted by this public layout and the rules.

Prism scales from **all carried gems**, including ordinary monsters and steals, not just gem clusters. At base stats with no items, Prism unit raw damage is `1.5*(80+1.5g)=120+2.25g` versus Stellar140; integer g=9 exceeds it. Ground damage is `80+1.5g` versus Stellar98, equal atg=12. These are mechanical crossovers, **not draft thresholds**: Prism has a stun,35 basic/700HP versus Stellar30/650, while Stellar has stronger empty-bag spells and different growth. One unsplit15-gem Elk capture can pass both crossovers without any gem clusters. Conversely dispersed or contested gem income may never reach the intended Prism, and banking resets carried-gem scaling. A mere map-total gem count does not establish that ramp.

Cassi&Issac is **one draft pick, two bodies**, not two pick slots. Five selections yield six champion actors. Extra turns, independent bags and ranged/melee work can cover dispersed jobs, but if either dies both die and both bags are lost to the killer. Their bodies require separate health, items, routing, fuel and support; do not count their combined base HP as one tank or grant both free funding. The extra-body order also changes activation/aggro ties. Their opportunity cost is the displaced single pick plus these coordination/liability costs.

Rules: `cambc-rules.yaml:21–29,58–64,68–102,160–173,204–211`. These are locally engine-verified rules; no new external source is needed.

## What the frozen baseline actually does

Use exact f475 source `provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7/src/`.

`draft.cpp:244–262` caches the entire choice list on first invocation. Five picks with `willow_draft=true` are always Prism/Vesper/Marcella/Willow/HoR. Four picks use the teacher list but swap HoR ahead of its fourth worker; three use `params::draft_preference`. The teacher's `3*members>10*groups` switch is a previously provisional Ryth/Vendetta separator (`draft_selection.h:31`), not a gem-income, support-access or opponent-counter criterion. Do not reuse that cutoff to decide Prism/Stellar/Cassi.

A genuine later counterpick cannot live in that first-call static initializer. Cache the public map summary, but select the remaining role at the actual draft turn using completed allied and enemy picks. Preserve `ensure_picked`, typed enum values, duplicate handling, reserve for pick/write, and writing draft memory before pick (`draft.cpp:281–304`). A missing/unavailable opponent record means use the map/default preference, never wait or infer a future pick; a missed pick causes every later pick to be random. Opponent picks are not bans on ours.

## Cheap public map summary and candidate roles

Extend the existing bounded packed-camp scan concept (`native_draft_counts`, draft.cpp:18–27; `count_draft_camps`, draft_selection.h:12–26), not a new global solver. Keep ordinary versus Monolith rewards separate. Useful interpretable features are:

- Ordinary base gems/gold by group and camp type; low-health resource HP and damaging-camp HP/reach. Include respawn periods, since repeated cheap payouts differ from one distant boss total.
- Local static grouping: mixed-resource groups, number of damaging members, and attainable3×3 cluster coverage around member coordinates. A cheap layout indicator nominates AoE value; it is not a promise of legal safe casts or all-team commitment.
- Existing public spawn/altar geometry and disconnection/crossable terrain. Use only a deterministic completed summary, or raw static descriptors in the first prototype; do not let partially finished draft fields silently change the chosen roster based on fuel timing.
- Potential support demand/access: damaging ordinary work and whether a healer could in principle stay within heal4 while avoiding the camp. Actual Willow service requires visible recipients, useful missing HP and legal casts; no ideal45HP/round subsidy is added to a draft score.

Candidate roles: Prism for attainable gem ramp plus control; Stellar for immediate ranged spell output when ramp access is weak; Cassi&Issac for independently useful split work/control when linked-body exposure can be managed. Vesper's comparison is against another independent worker (initially Vendetta as a clear/reset control), using actual ordinary gold access and route economics. Keep Marcella/Willow/HoR common in the initial five-pick substitutions so their support/frontline opportunity cost is visible. This is experimental isolation, not a permanent ban on adapting those roles.

Do not invent a weighted all-purpose score before controlled data. First test fixed role substitutions on predeclared map families; their treatment differences reveal whether a simple public feature is predictive. Zero gem/gold clusters can be an **evaluation stratum**, never an automatic replacement rule. Positive loot totals, cheap carry crossovers, or a single loss are not sufficient selector thresholds.

## Existing concrete map contrasts

These are whole-layout initial ordinary rewards, neither team-owned nor guaranteed collectible:

| Map / existing extracted JSON | Ordinary gems / gold | Layout contrast |
| --- | --- | --- |
| Gem Fields / `.../khaos-v34-ladder-intake-20261024-v1/extracted/maps/d22495f1f242da29.json` |364 /600|40 gem clusters,0 gold clusters; four Elks/six Wolves. Dense mixed groups, holes affect walking; no-gold-cluster negative control. |
| Fracture / same directory `8f17d2cbf1d64f77.json` |444 /2720|20 gem/32 gold clusters,16 Elks/16 Wolves, plus two excluded Monoliths. Mixed heavy groups and connected-escape problem. |
| Big World / `provenance/willow-phased-solo-boss-4d08241-v1/extracted/maps/c890c7d4607bc45c.json` |376 /2160|32 gem/28 gold clusters,8 Elks/22 Wolves, plus two excluded Monoliths; long ordinary conversion routes. |

The isolated known Big World economics and Fracture/Gem Fields losses demonstrate route/allocation constraints, not that changing a champion cures them. The current Gem Fields exact trace even retains g4 for Prism; its special approach spell gate may explain missing contribution before any draft-value change. Keep that gameplay issue distinct.

## Counterdraft only from revealed picks

Both teams choose simultaneously each round. At our pick k, only completed opponent picks1..k−1 are visible; no same-round or future pick is available. Both physical sides obey this. Team name/UUID is not a runtime draft input. Saved histories describe uncertain behavior/source identity, not a hidden lineup oracle.

Examples from existing saved normal histories:

| Observed ordered prefix | Earliest usable choice | Legitimate interpretation |
| --- | --- | --- |
| Vesper/Vendetta/Ryth (Mite's common five-pick opening) |Our fourth|Revealed mobile/reset economy plus Ryth control. It does not reveal Tavi/Marcella yet. |
| Vesper/Vendetta/HoR (Fish patterns) |Our fourth|Different third body; fourth/fifth have varied, including Cassi or Varg continuations. Mite and Fish are indistinguishable from the first two picks alone. |
| Vesper/HoR/Vendetta (Claudus five-pick opening) |Our fourth|Known early order differs; late Tavi/Marcella cannot be assumed. |
| Prism/Marcella/Ryth or Prism/Marcella/Vendetta (prism best girl patterns) |Our fourth|A visible scaling carrier and stun-immune worker, with differing third role. No guarantee of the fourth/fifth roster or enemy micro. |

Mite refresh `provenance/mite-history-refresh-20261024-v3/ranked-first30.json` records21 five-pick rows Vesper/Vendetta/Ryth/Tavi/Marcella, five three-pick rows Marcella/Vendetta/Tavi and four four-pick rows HoR/Vesper/Marcella/Vendetta. These are saved descriptive counts, not proof of one deployed binary. Prefix matches must be typed SDK enum names; API replay numeric draft IDs are not SDK enum ordinals.

A map-sensitive first pick can choose Prism/Stellar/Cassi **without opponent information**. To condition that carry choice on revealed picks, deliberately delay it: a candidate order Marcella/Vesper/HoR/Willow/flex exposes the first four enemies before flex. Compare an otherwise identical delayed-Prism control, because simply moving Prism/HoR changes IDs, default order, remainder allocation and early routing. Do not attribute the reorder's effect to counterpicking. No claim that Stellar/Cassi is a proven counter to any named team follows from this note.

For the first counter experiment, the observable prefixes stratify results and choose which candidate matchups to compare; they do not require a hard-coded team classifier. Immediate ranged burst/control versus known mobile melee, or extra linked bodies versus dispersed economy, are falsifiable roster hypotheses. Marcella's stun immunity and pair death coupling constrain such hypotheses. A bot executing a forced Mite-like draft with our frozen opponent code is a **roster proxy**, not Mite's program.

## Small evaluation matrix, including combinations

Complete the currently authorized micro/macro factorial first; retain exact source identities. Then:

| Stage | Arms | Cells / question |
| --- | --- | --- |
|Map-role screen|Fixed baseline P/V/M/W/H; S/V/M/W/H; C&I/V/M/W/H; P/Vendetta/M/W/H|Gem Fields, Fracture, Big World × both physical sides against one frozen reactive opponent:24 games before reuse. Existing exact baseline cells may be reused when pins match. Tests carry alternatives and Vesper opportunity cost without an invented selector.|
|Edge stratum|The relevant carry or Vesper substitution plus baseline|One saved/public five-pick map with few/no gem clusters, and one gold-poor ordinary-reward map if the existing static inventory contains them. Choose by public feature before outcomes; do not invent map names or force an absent family. Keep pick-count strata separate.|
|Revealed-prefix screen|Delayed-Prism reorder control versus delayed best candidate(s)|Two contrasting observed prefix families on a small matched map/side subset with frozen reactive roster proxies. Check collisions/unknown-prefix fallback and actual disclosure timing.|
|Gameplay interaction|Same two draft arms × baseline versus selected hop/escape gameplay combination|A small matched subset where routing and reward access matter. Test the interaction directly; neither single arm must win before the combination is tried. Do not silently combine with v48 overlays.|

Primary mechanism metrics: each role's first real payout and gold, time carrying9/12+ Prism gems (mechanical comparison markers only), first useful item, ordinary clear/capture cycles, productive work versus travel/recovery, paid Willow service followed by continued work, paired deaths/bag losses, and tribute timing. Record final score/outcome, draft/body count, native errors/rollovers and cost. Evaluate alternatives at the same opponent/map/side; don't compare Mite's different opponent to our local game as a treatment effect.

A useful first prototype can choose among a small tested role menu with an explicit default and exact disclosed-prefix features. It need not solve an optimal draft, impose a fixed service threshold, or prove unavailable private histories. Source/fixture checks for valid picks, deterministic map summaries, six-body support and no future-pick access are implementation checks, not a one-loss promotion veto. Broader source-pinned evidence remains necessary before any release.
