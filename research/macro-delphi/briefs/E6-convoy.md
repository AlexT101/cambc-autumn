# E6 "convoy": the Prism works where its team works (bots/variants/convoy)

Read /home/ubuntu/wt/macro-o4/research/macro-delphi/briefs/common.md first and follow it (TMPDIR rule; all output
under /home/ubuntu/wt/macro-o4/replays/delphi-smoke/). Candidate dir: `bots/variants/convoy` (create:
`./copybot charybdis variants/convoy`). Reference: `bots/variants/charybdis-ref`.

## Why
- Variant `pack` confined every ally to within `carry_reach()` (12) of our Prism's work. Against charybdis-ref it
  **won the fights decisively**: kills 7.7 vs 5.9 a game, deaths 6.6 vs 8.1, kill share at equal numbers 0.575, our
  Prism's kills 5.8 vs 3.1 and deaths 0.9 vs 1.7, Prism gems 660 vs 535.
- It **lost the economy and the game**: captures 63 vs 74, allies collected 90 vs 119 gems each, 38.7% of 10,240.
  Four allies tied to one area left them idle (300-1,150 ally-turns a game with no group to farm).
- The Prism is the team's fight engine. It is 78% of Prism killers, and its stun and ground spell scale with Focus.
  It is also the one body whose death decides the game (the team whose Prism dies first loses 90%).
- So invert the constraint. **One body (the Prism) keeps near the team**, instead of the team keeping near the
  Prism. That costs one champion's freedom instead of four, and the Prism already spends much of its time
  collecting allies' clears ('G'/'L'/'Q' picks).

## Design
1. **Support set.** For our keeping Prism (`keeps_gems`), the support set is its living allies' work positions:
   each ally's claimed group centre (`comms::claim_of`), else its seen or posted tile (`recent_tile` in
   economy/capture.cc). Cassi and Issac count as two.
2. **Prism's candidates (economy/farm.cc farm_turn, Prism only).** A group is a candidate only if its tiles are within
   R = `carry_reach()` (12) of at least one ally's work position. R is derived: an ally within that walk is one the
   Prism can still reach to collect a capture from, and one that can reach the Prism's fight within about two
   ability cooldowns.
   - Apply it to every pick type (solo, crew, join, kite, risky, 'G'/'L'/'Q', pick_up).
   - Exceptions:
     - our own banking or winning trip, heal/shop trips, the opening plan while it runs, Monolith/siege operations;
     - **no ally alive or known**;
     - **no candidate left inside**. Then fall back to the unconstrained choice for that turn. Never idle, and never
       walk to allies for its own sake.
   - Prune bounds: masking only lowers the best. Make sure kept or memoised choices respect the mask, as variant
     `bots/variants/pack/src` does for allies. Read its diff: `diff -ru bots/variants/charybdis-ref/src
     bots/variants/pack/src`. It has a cached per-group mask, an exemption for the group we are working from where we
     stand, and the places in farm_turn the mask must reach. Reuse that structure, applied to the Prism, with the
     support set instead of an anchor.
3. **Allies are unchanged.** They farm as charybdis-ref does, and keep handing captures to the Prism as they do today.
4. **Debug traces:** per 50 rounds, the Prism's distance to its nearest ally; per turn when the mask removed the
   unconstrained best; how often the fallback fired.

## Done when
It builds, three local games against charybdis-ref finish without bot errors, and traces show the Prism nearer its
allies than in the reference, with the fallback firing. Report as common.md asks. Include the Prism's mean
distance to its nearest ally in your games, ours vs the ref's.
