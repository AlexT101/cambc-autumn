# Audit: bots/astraeus/src/model/support_mailbox.h

The mailbox carries the protected mate's heal request and the healer's offer in each one's turn-order
priority payload (bits 8-10: intent, round mod 4), read by the other endpoint while it sees the sender.

## Changed

Commit `astraeus audit (support_mailbox): cleanup`. Byte-identical.

- `receive`: dropped checks that the reset already implies. The `!present` terms in the initial reset
  are covered by the per-endpoint `present && alive`. `pair[other].alive` in the read branch can't be
  false once there is no reset. The per-endpoint `alive[]` array became one `both_alive` flag, which
  gives the same "alive last read and now" test. `receive` now returns `void`; its only caller,
  `comms.cc receive_support`, ignored the result.
- `valid`: dropped `sent >= 0` (implied by `positive`, since both are set and cleared together) and
  `alive[protected_mate] && alive[healer]` (if either is dead, this round's `receive` reset `positive`).
- Comments: a header explaining the protocol, including why the age is at most 1. The endpoint
  comments now name `support_protected`/`support_healer`, since the protected mate can also be Tavi on
  3-pick maps (map_economy.h), not only Prism. Added a comment on what `valid` means.

Verification:
- Standard bench (`--test-draft`, 4 maps): 8/8 replays identical, fuel +0.00%. Those drafts never have
  both Prism and Willow, so this run doesn't exercise the code.
- Own drafts (HEAD copy vs working tree): 8/8 identical, +0.00%. These drafts didn't pick Willow on
  these maps either.
- Forced Prism+Willow copies of both base and candidate (`map_model_draft = false`, draft_three/four led
  by prism, willow; draft_five already has both). All 8 games drafted the pair: 8/8 identical, total
  fuel -0.06% (2,071,487,408 -> 2,070,281,388; 39,824 turns cheaper, 194 dearer).

## Considered, not changed

- **The respawn check (`respawn[]`, `Endpoint::respawned_round`) is redundant.** `respawned_round` only
  changes when world.cc flips an ally from dead to alive (world.cc:1587-1596). That transition already
  resets through `both_alive`, and a death and respawn hidden inside a gap resets through
  `read_round != round - 1`. Removing it would mean dropping a field comms.cc initialises
  (comms.cc:264), so it is out of scope. Suggestion below.
- **`Endpoint::present` is always true.** comms.cc calls `receive` only when both pointers are
  non-null. Kept, because the type is shared.
- **Widening the round tag** (see Suggestions). It is cheap but changes priority values, so it can
  change replays and the engine's view of our priorities. It is also rare, so I left it as a
  suggestion rather than an "obvious" fix.

## Suggestions

1. **A raw turn rank of 0 erases the whole payload: the support intent and the claim**
   (turn_order.cc:97-98, `packed_priority`: `if (raw == 0) return 0;`). The idle priority is
   `role + 8 - 8*floor(10*(1 - hp/den))` (idle_priority.h). Prism has role 0, so with no gems, no
   danger bucket and no wish band, it gets raw 0 at 80-90% health. That is exactly when it might start
   asking for a heal, and its request and claim are then not sent: `payload_of` reads priority 0 as
   "none" (comms.cc:254). Willow (role -1) never hits 0 when idle. A `wish.priority()` with band 0 and
   value 0 also gives raw 0.
   Fix: let raw 0 pack to the payload alone, `return payload`. Values 0..65535 still sort between rank
   -1 (negative) and rank +1 (>= 65536), and `>> priority_payload_bits` still reads them as rank 0
   (turn_order.cc:194). The cost is that two raw-0 allies would tie-break on payload rather than id.
   Alternatively, keep `7 - index` in the rank for raw 0 and offset it so it stays non-zero.
   Severity: medium for the Prism/Willow pair and claims. Effort: small, plus an A/B.
2. **Round-tag aliasing after 4+ skipped sender turns** (support_mailbox.h:15, :53). The tag is
   `round & 3`. A sender that skipped publishing (`world.is_stale()`, bot.cc:481) for exactly 4-5
   rounds reads as age 0-1, so an old positive is taken as fresh. Bits 11-15 of the 16-bit payload are
   free, so the tag could be `round & 31` (mask 31 in `encode` and the age). Severity: low (needs long
   fuel outages). Effort: trivial, but it changes priorities, so A/B it.
3. **The first message after a gap or a revival is discarded** (support_mailbox.h:46-50). The payload
   carries its own round, so it doesn't need `continuous` to be dated. Only `sent`/`positive` need
   clearing. Reading the payload even on reset rounds (when both are alive now) would cut a round of
   latency after our own missed turn. After a revival this mostly doesn't matter: the sender's
   pre-revival payload was published with `both_alive = false`, so it was negative anyway. Severity:
   low. Effort: trivial; changes behaviour.
4. **Drop the respawn tracking** (support_mailbox.h:26, :32, :39-44 and comms.cc:264): it is
   redundant, as explained above. This is a cross-file cleanup that also needs comms.cc's aggregate
   initialiser changed. Similarly, `Endpoint::present` and the `present ? ... : -1` branches could go if
   comms.cc only ever passes complete pairs (it does). Severity: none (simplification). Effort: small.
5. **Modelling gap: the mailbox links exactly one healer to one protected mate** (comms.cc:236-250).
   Willow can heal any ally, but any other ally's need is visible only through Willow's own reading of
   its health, with no request. If more mates benefit, a per-ally "wants heal" bit could go in each
   ally's payload, since every ally already publishes one. Severity: unknown; needs an experiment.
   Effort: medium.
6. **Freshness window**: `valid` accepts a positive for 2 rounds after it was sent
   (support_mailbox.h:63), even if the sender has since withdrawn it out of sight. That is inherent to
   vision-gated reads and is the right trade-off; noted only for completeness.
