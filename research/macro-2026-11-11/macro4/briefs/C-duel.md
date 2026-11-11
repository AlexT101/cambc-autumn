# Brief C: the Prism duel (protect our carry, hunt theirs)

You are an implementation subagent for the macro4 lead. Work ONLY in /home/ubuntu/wt/macro4 (git worktree, branch
macro4-20261111). Never touch other checkouts under /home/ubuntu/wt/ or /home/ubuntu/cambc-autumn, never edit
bots/variants/ocean-ref-b7c87cf, bots/ocean, or any bots/variants/macro4-* other than your own, never write to any Claude
memory directory, never run ab.py / fgate / A/B tests, commit nothing. Read /home/ubuntu/wt/macro4/AGENTS.md and
cambc-rules.yaml first (API: docs/api/cpp.md, sdk/cpp/cambc.h).

## Candidate
`cd /home/ubuntu/wt/macro4 && ./copybot variants/macro4-hub1 variants/macro4-duel`; edit only
bots/variants/macro4-duel/src. Do not touch draft/ or emblem selection. macro4-hub is the base (it won 53.5% over
10k games vs ref): read `diff -ru --exclude=.cambc bots/ocean/src bots/variants/macro4-hub1/src` first, it makes our
Prism the team's gem hub (allies value gems Prism can collect at x(1+rho), hand holds to Prism).

## Why (measured)
- The game is a Prism Focus race. Prism's passive is +1.5 Focus per carried gem; stun deals 1.5x Focus (range 4,
  single unit), ground 1x Focus (3x3), cooldown 8. A 100-gem bag one-shots most champions.
- In ocean mirror games, Prism bags of 100+ are 67% of all gems lost to deaths, and the team losing one loses 83% of
  those games. In 309 Prism deaths the killer was the enemy Prism 169 times (91 solo); the median HP of our Prism at
  the first hit was 1.00 and it died within 3 rounds: the first cast decides the duel.
- With the hub, our Prism carries more for longer, so this exposure grows, and so does the prize for killing theirs
  (a kill takes all the victim's carried gems).


## Where the hub loses (measured on macro4-hub vs ref, 735 games where both teams drafted Prism)
- Our Prism carries far more than theirs: mean bag 87 vs 54 at r200, 268 vs 161 at r500. Yet it wins only 53.6%,
  because the bag is lost: our Prism died carrying 100+ gems in 162 of 735 games (22%), and we won just 10% of those
  (3% when theirs survived). In games where neither Prism lost a 100+ bag we won 54%.
- The 180 deaths of our 100+ Prism: killed by the enemy Prism 73, Vesper 63, camps 11, others ~30. In 130 of them the
  enemy Prism carried LESS than ours: we lose duels we should win. Half (90) died while channelling a recall (recall
  is 5 turns and any damage cancels it). At the death or at the recall start the nearest enemy was 3-4 tiles away
  in most cases (stun range is 4), our Prism was usually hurt (median ~0.2-0.3 HP outside recalls), and in 35 of
  each 90 no ally was within 4.
- So the main loss is a big carrier lingering hurt inside enemy cast reach, often starting a recall there, alone.
  Theirs dies the same way 200 times, mostly to our Prism (136): hunting theirs already works; protecting ours does not.

## Most important piece: the carrier's life is worth its bag
A death hands the killer every carried gem (a swing of twice the bag in the race) and, for Prism, all its Focus.
Make the safety / retreat / recall decisions of a carrier scale with that, from the kit, not constants:
- A carrier treats tiles where the visible (and recently seen, still-plausible) enemies' combined burst over the next
  turn(s) could kill it as unsafe, unless the fight there is clearly won without losing it. Today's retreat is likely
  HP-fraction based; find it and make it burst-vs-HP based for carriers, with the death cost = carried gems.
- No recall start while an enemy can reach and damage us before the 5-turn recall completes (damage cancels it;
  those turns are wasted while the enemy closes). Walk away / toward allies instead (reuse escape.cc goals).
- When our Prism outguns theirs (its burst kills theirs first), the duel is a strike, not a retreat (item 3 above).
This is the piece to build first; items 1-4 above are its parts.

## Design: treat Prisms as a duel decided by Focus and the first cast
First read how ocean models threat today (model/safety*, combat/fight*, combat/strike* or whatever does the strike
search and the fight sim) and how it estimates an enemy's damage: does it know an enemy Prism's Focus (from its carried
gems if visible via the API, or Focus directly) and its spell cooldown? Use what the API exposes; never assume
hidden information. Then, deriving every threshold from the kit and state (HP, Focus, cooldown, ranges, move speed),
not hand-picked numbers:
1. **Know the burst.** An enemy Prism's burst this turn and next = its spell damage at its current Focus if the spell
   is ready (or ready by then), over its cast reach (move + range). Make sure the safety/threat model uses that true
   burst (Focus-scaled) rather than a base-stat estimate. Same for our Prism's burst on them.
2. **Our carry doesn't step into a lost duel.** Our Prism (and any carrier with a big bag) avoids tiles inside an enemy
   Prism's cast reach when that enemy's burst kills or cripples us before we can kill it (compare bursts, HP, who
   acts first given cooldowns and turn order). Reuse the existing safe-tile / escape machinery rather than a new
   movement system.
3. **Our carry takes a won duel.** When our Prism's burst kills the enemy Prism (or the enemy Prism is within the
   reach of our combined burst with allies in range), and ours survives the reply, that kill is valued at its full
   prize (100 gold + all its carried gems, which also swings the Focus race by twice its bag). Check the strike
   search already values carried gems in a kill; if it does, make sure it fires for this case (range/reach gates).
4. **Focus the carry.** In a fight, other champions' target choice should prefer the enemy Prism (or the enemy
   carrying the most gems) when it is killable, because removing its Focus removes the enemy's main damage and
   returns its bag. Keep this inside the existing target scoring as a derived value (gems carried x their worth),
   not a flat bonus.
Keep each piece small and coherent; if the code already does one of these, say so and don't duplicate it.

Add `debug_block` lines prefixed `DUEL` for (a) a tile rejected as inside a lost Prism duel, (b) a duel strike taken,
(c) a carry-focus target choice. Keep fuel bounded (2x fuel is the test budget).

## Done when
- Builds (`cambc build bots/variants/macro4-duel`, debug and `--release`; see tools/README.md) and one or two local
  games against bots/variants/ocean-ref-b7c87cf run without errors on a map where both teams have Prism; report how
  often each DUEL trace fired.
- Spawn a read-only auditor (Explore or Plan subagent) on your diff: correctness (wrong team, stale positions,
  off-by-one in reach/cooldown, turn order), fuel, and any magic number. Fix what it finds.
- Final reply: the design as built, the diff summary (files, functions), what the auditor found and what you fixed,
  and trace counts.
