# Observable counterdraft timing

2026-10-23. Current source/API/rules inspection only. No gameplay edit, engine, export, deployment or new script. Latest local source337f42a5 is not attributed to a deployed live result here; recent online history must establish the executable/version chronology before claiming a regression.

## What can be known

`docs/llm/GameRules.md:59` states simultaneous picks with progressive revelation. `cambc-rules.yaml:21–26` gives one draft round per pick, numbered from0. `sdk/cpp/cambc.h:5140–5155` returns an owning list of **completed** picks and skips `DraftUnavailable`; selecting a champion ends this turn's actions. Opponent picks do not ban our own choice. Cassi&Issac is one pick and later two bodies.

The older Khaos_v32 Fish five-pick games used Cassi&Issac fourth and Ryth fifth. Newly retrieved metadata for group `342a1765-2345-4f3a-890e-79e83f6802a8` instead uses **Varg fourth, Cassi&Issac fifth** on its five-pick maps. The first three picks are unchanged:

| Our choice | Older opponent prefix available | Recent opponent prefix available |
|---|---|---|
| 1: Prism | None | None |
| 2: Vesper | Vesper | Vesper |
| 3: Marcella | Vesper, Vendetta | Vesper, Vendetta |
| 4: currently Willow | Vesper, Vendetta, HoR | Vesper, Vendetta, HoR |
| 5: currently HoR | Vesper, Vendetta, HoR, Cassi&Issac | Vesper, Vendetta, HoR, Varg |

The full five-pick composition cannot be observed before our final choice. In particular, **recent Cassi&Issac is not observable even if we postpone the Willow decision to fifth**. Matching the first three or four picks is an observable trigger, not certainty about the unseen next pick or identification of a named opponent. The same restriction applies on both physical sides; engine call order is not a valid way around simultaneous disclosure.

## Current architecture and implementable alternatives

`draft.cpp:244–264` caches the **entire preference list on its first invocation**; `play_draft:294` explicitly invokes it before first-round expensive map analysis. Therefore simply adding an opponent query inside that static initializer would inspect no useful prefix. Keep public map/count analysis cached, but evaluate any remaining-pick detector at the actual later decision. Use actual completed allied picks to identify the slot and validate the expected Prism/Vesper/Marcella prefix. Preserve `ensure_picked`, duplicate rejection/fallback and writing draft memory before the successful pick; never skip a pick to wait for disclosure.

Two implementable options, requiring a deliberate choice rather than hidden inference:

1. **Preserve previous baseline order:** at our fourth choice on a five-pick map, match exactly the revealed ordered prefix Vesper/Vendetta/HoR and the predeclared public map predicate. If matched, choose the teacher Ryth-or-Vendetta slot, then HoR fifth. Otherwise keep Willow fourth, HoR fifth. This reproduces the old baseline roster/order on activation but cannot distinguish the recent Varg continuation from the older Cassi&Issac continuation. Prefix collisions must be reported.
2. **Observe the fourth unit before deciding:** for the suspected three-pick prefix, choose the common HoR fourth; at the fifth choice inspect the completed four-pick prefix. A recent-lineup experiment can match Vesper/Vendetta/HoR/**Varg**, choosing teacher Ryth/Vendetta; otherwise choose Willow. This is a response to four known units, **not detection of Cassi&Issac or a full fixed draft**. An older-lineup experiment could separately match Cassi&Issac fourth, but the earlier wins do not establish a need to do so. This retains the first three picks and gets a stronger observed trigger, but changes HoR's draft position on all suspected-prefix cases, including false alarms. Default turn-order ties depend on draft order, so this is not an exact old-baseline behavior restoration. It needs a reordered-Willow control as well as the fallback comparison. Full five-pick matching still remains impossible.

No new shared gameplay protocol is needed. Cache separate teacher/default candidate lists if useful; do not freeze the counterdraft decision before the relevant prefix arrives. Keep test-draft behavior and three/four-pick native rosters unchanged. A failed/unavailable observation should use the default choice, not infer the missing pick. A "large map" predicate needs an explicit public threshold or geometry definition; five picks are known but are not automatically equivalent to map area. No new threshold is selected from the current small live sample.

## What the fallback actually is

Both frozen8be8eaa and current upstreamfbda803 use `teacher_draft_roles` (`draft_selection.h`): Prism/Vesper/Marcella, then **Vendetta if `3*camp_members > 10*camp_groups`, otherwise Ryth**, then HoR. The criterion is public camp density, not map width or enemy identity. Current qualified Willow replaces that fourth slot on five-pick maps. Four-pick upstream already keeps HoR and drops the Ryth/Vendetta slot.

Selecting those teacher roles would be a **draft-only fallback within latest gameplay**. It would not restore the whole earlier Hyperion combat/economy/fuel policy, nor establish that the earlier reported competitive result transfers. An exact historical-policy fallback is a different, much larger intervention. The user's earlier coinflip/slight-win recollection still needs matching version/opponent/date/roster evidence; no such rate is inferred from a source role list.

## Historical control

The existing Khaos_v32 Fish group was4–1: Monolith391–1054 loss; Swirl1065–333, Quadrants1012–854, BossBattle1146–0 and Hooks1001–66 wins. Three games were five-pick P/V/M/W/HoR (2–1); two were four-pick P/V/M/HoR (2–0). All three five-pick opponents had the full Vesper/Vendetta/HoR/Cassi&Issac/Ryth roster. Thus this exact revealed prefix has previously accompanied Willow wins as well as a loss. It does not itself prove a bad matchup or validate a fallback selector. Sources of those live executables remain unverified; see the pinned `intercontinental-fish/analysis-final/*/meta.json` and `willow-fish-monolith-loss-review.md`.

## Recent metadata changes the comparison

`provenance/fish-regression-history/pantheon-page-02.json` records the finished group created2026-10-23 21:04Z and finished21:09Z: Pantheon A loses Gemfight, Shortcut, Expanse and BigWorld, and wins Hooks (1–4). Expanse match `65642cbd-2c7c-4cba-a769-5a612f817c1d` and BigWorld `b51a5364-c7fc-4b94-9181-e694eae67834` are the two five-pick losses. Their Fish draft array is `[1,2,11,9,3]`: Vesper/Vendetta/HoR/Varg/Cassi&Issac. Four-pick Fish remains `[1,2,11,3]`; our four-pick P/V/M/HoR games are1–2, so the whole1–4 result cannot be assigned to Willow.

These metadata indices use replay `DRAFT_CHAMPIONS` (`tools/replay/engine_own_view_v3_compat.mjs:21`), **not SDK champion or champion-draft ordinals**. An implementation must use typed SDK enum names, never these raw numbers. The recent five-pick lineup replaces Ryth with Varg and shifts Cassi&Issac later; both map mix and opponent composition differ from the older group. That is an established confound, not proof that Varg caused the losses. Recent executable source/version identity and action-level causes remain unverified. Expanse/BigWorld replay analysis should precede any source-regression or fallback-benefit claim. The timing options above prepare a legitimate experiment without inventing knowledge of the final Cassi pick.
