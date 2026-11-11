# charybdis: final merge report (phases 1 and 2)

Base: `bots/charybdis` started as macro1-hold6 (`variants/charybdis-base`), the best of the six macro bots at normal
fuel (56.8% of 40,960 against ocean-main-b7c87cf). Phase 1 merged the KEEP queue (`variants/charybdis-p1`). Phase 2
worked through the CONSIDER queue. The final state is `bots/charybdis`, frozen as `bots/variants/charybdis-p2`.
Details are in merge-log.md, tables in results.md, specs in plan.md.

All A/Bs used release builds, normal fuel, `--no-test-draft`, the fast runner, and fresh ladder-v2 suites, both
sides. Phase 1 ran on s-710001..080 and phase 2 on s-720001..240. "Paired" compares two candidates game by game on
the same maps and sides against the same opponent.

## Final win rates

`charybdis-p2` = p1 + C2 + C10 + C3r, on s-720001..160 (81,920 games each):

| Opponent | charybdis-p2 | charybdis-p1 there | charybdis-base |
|---|---|---|---|
| ocean-main-b7c87cf | **60.12%** (CI 59.78-60.46) | 58.68% | 56.9% (s-710001..040) |
| charybdis-base | **53.19%** (CI 52.85-53.53) | 51.96% | - |
| charybdis-p1 | **51.32%** (CI 50.98-51.66) | - | - |

Against ocean, the merge moved the bot from the base's ~56.9% to p1's 58.7% to p2's 60.1%.

## Every change, by source

Status key:
- **P1** merged in phase 1;
- **P2** merged in phase 2;
- **DROP-plan** dropped by the planner (not ported);
- **DROP-user** dropped by user decision;
- **rejected** ported and tested, but not merged.

### macro3 (eoq2, 52.3% at normal fuel)

| Change | Status | Why, with numbers |
|---|---|---|
| M3-a (K1) EOQ bank floor with an online carrier hazard | **P1** | 57.9% vs ocean, 51.1% vs base (20,480). |
| L-3 (C5) eoq5: the chain limit replaced by a holding cost | rejected | Level on C2. Paired vs C2: ocean -0.01, base +0.20, p1 +0.00 (40,960 each). It changes 34 decisions a game but not the result. It was level at 2x too, so no fuel flag. |

### macro2 (lstep, 50.7%)

| Change | Status | Why, with numbers |
|---|---|---|
| M2-d (K2a) no lethal camp flight | **P1** | A mechanical bug fix: 58.2% vs ocean, 51.4% vs base. |
| M2-c (in K2b, then C10) hold cast | **P2** | As K2b with M2-b on K2a it was level (58.5 / 51.4). As C10 with M2-a on C2, paired vs C2: **p1 +0.61 (CI +0.12..+1.11)**, base +0.62 (+0.13..+1.11), ocean +0.10 (40,960). |
| M2-a (in K2b, then C10) Willow heal order | **P2** | Together with M2-c, as above. |
| M2-b (in K2b) two casts on a double turn | **DROP-user** | Dropped by user decision: adds caution; level in K2b and alone on macro2. |

### macro4 (handfc, 55.9%)

| Change | Status | Why, with numbers |
|---|---|---|
| M4-a2 (C2) the Prism collects an ally's clear in progress ('Q') | **P2** | 59.15% vs ocean (paired vs p1 +0.54, CI +0.06..+1.03), 52.43% vs base, **50.91% vs p1 (CI 50.4-51.4)**. |
| M4-a3 + M4-b2 (C1) team-marginal carry value with the `hub_net` gate | rejected | Loses: 57.69% vs ocean, 51.35% vs base, **49.31% vs p1**. The holder-gain term cut the Prism's G/L carries by ~45%, undoing the base's carry lever. |
| M4-b2 alone (C1b) the `hub_net` gate on held hand-overs | rejected | Level: 58.73 / 52.35 / 50.06 vs p1. It fires 0.26 a game. |
| M4-b1 (K3, then C9) hand-over of full and single-tile holds, rebuilt in the base | rejected | Phase 1, on K2a: level (58.3 / 51.6). Phase 2, on C2, paired vs C2: p1 +0.02, ocean -0.05, base +0.35 (CI +0.03..+0.67). Not a gain against p1. |
| M4-b4 single-tile part (`hub_claim`) | rejected (folded into K3/C9) | Went with K3. |
| M4-a1 'Q' collection of held captures as a separate mechanism | DROP-plan | A parallel mechanism to the base's G/L; the two pickers would fight over the same holds. |
| M4-b3 `hub_awaited` in `capture_recall` | DROP-plan | Covered by the base's `prism_coming` / `left_for_prism` / `yields_to_prism` path. |
| M4-b4 rest (`hub_claim` for multi-tile groups) | DROP-plan | The base's claimed branch already times hand-overs, and the Prism joins by 'G'. |
| HUB debug lines | DROP-plan | Debug-only. |

### macro5 (hold-sole2, 56.2%)

| Change | Status | Why, with numbers |
|---|---|---|
| M5-c (C4) Prism stun-lock safety (prismsafe) | rejected | Paired vs C2: **ocean -0.68 (CI -1.23..-0.12)**, base -0.05, p1 -0.02. OOF turns +15%. |
| M5-f (C6) route tie-break off the Prism's hold | rejected (not built) | The plan's condition failed: a trace showed 0.014 transit splits a game. |
| M5-a holder Focus premium | DROP-plan | Covered by the base's `sole_capture_holder` (B1); the residue conflicts with B1. |
| M5-b Prism pick-up of allies' counting holds | DROP-plan | Covered by the base's 'G' (B2), and needs M5-a. |
| M5-d hold-sole's threat-gated yield | DROP-plan | Level, and the base has its own yield under threat. |
| M5-e capture-recall co-holder step-off | DROP-plan | Covered by the base's B5. |
| L-2 hold-sole3, more dilution-leak fixes | DROP-plan | 51.8% of 512 (noise). Its recall rework is the base's hold7 (level), and its transit rule is a softer M5-f. |

### macro6 (carry3, 55.3%)

| Change | Status | Why, with numbers |
|---|---|---|
| M6-bc (C3, then C3r) Focus-priced farm values replacing `gold_part` | **P2** (user decision) | On p1 (chy2-C3) over 122,880 games: **50.35% vs p1 (CI 50.07-50.63)**, ocean paired vs p1 +0.42 (+0.08..+0.75). Re-ported on C2 + C10, over 81,920 games, paired vs C10: **ocean +0.70 (CI +0.29..+1.11)**, base +0.16, p1 -0.05. Kept because it holds a clear ocean gain with p1 and base level, and it replaces the base's crude `gold_part` halving with a derived price (user decision). |
| L-1 (C7) macro6-mono, the carry price extended to the Monolith | **DROP-user** | Dropped by user decision: fired too rarely to pass (80 debug games, 70 identical to carry3); untested. |
| M6-a carry holder premium and the Prism 'T' takeover | DROP-plan | The premium is covered by B1, and the 'T' takeover duplicates the base's 'G'. |
| YIELD / PHOLD / TAKEOVER / KEEPB debug lines | DROP-plan | Debug-only. |

### macro1 (the base, hold6)

The base itself, with its Prism mechanisms B1-B6 (`sole_capture_holder`, G/L carries, `leave_for_prism`, `gold_part`
and others). C3r replaced `gold_part`.

## Fuel-optimization flags

- **None outstanding.** C3 was the only "gained at 2x, level at normal fuel" change ("dropped at normal fuel:
  candidate for later fuel optimization"), and it was accepted as C3r, so the flag is withdrawn.
- **C4 (M5-c) has a fuel cost** but is not flagged: OOF turns rose 15%, and macro5's own evidence for it was not
  significant (+0.5 over 29,696 games).
- **C10 also costs fuel:** OOF turns rose about 1%. The fuel-only fix the audit suggested (hoisting
  `engagement_near` out of the hold cast's group loop) is merged.

## Unexpected results, likely reasons and next steps

- **C1 lost (49.3% vs p1)**, although macro4 gained with it.
  - Likely reason: macro4's host (ocean) barely carried on the Prism, while the base's gain *is* the Prism carry.
    The holder-gain term refuses about half those carries whenever the holder values gold more.
  - Next: price the holder gain in gems only, or take the premium only on empty 'L' groups.
- **C3 level against our own forks, but a clear gain against ocean.** It was level at 81,920 on p1, and on C2 + C10
  it was +0.70 against ocean but -0.05 against p1.
  - Likely reason: p1 and base share the Prism-carry economy, so a better-priced Prism wins little against them.
    Ocean does not share it.
  - Next: the audit's health gate on 'Q''s crew premium (J has one; 'Q' doesn't), and a Focus premium gated on
    `prism_dominant`.
- **C4 lost against ocean (-0.68).**
  - Likely reason: the lock scan runs every Prism turn, and its fuel (OOF +15%) costs more than the ~1.5 safer turns
    a game gain.
  - Next: a cheap pre-test (only with a visible stun-ready enemy in reach), then re-measure.
- **K2b level, but C10 a gain.** M2-b's added caution probably cancelled M2-c and M2-a. Without it, and on C2, the
  pair gains +0.6 against both p1 and base.
- **K3/C9 level twice.** It changes only about 4,400 of 40,960 games.
  - Next: let C2's 'Q' take a full group through K3's hand-over. That needs its own pricing, and the C9 audit flagged
    it.
- **C5 level** although it fires 34 times a game: the holding cost and the old chain limit pick the same banks in
  practice. It's a possible clean-up (it removes `chain_bag_limit`) if a later change needs it.

## Method notes

- C3's first extension on s-720161..240 lost its OOF counts: a replay cleanup glob matched the running batches. The
  per-game results are intact.
- s-720241..320 were generated for a second C3 extension that wasn't needed. They are unused, so still fresh.
- The decision rules came from merge2-brief.md, amended by user decisions: M2-b, C7 and C3r's acceptance.
