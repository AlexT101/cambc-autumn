# cal-c: the Prism war (hoard-aware posture)

Variant NAME `cal-c`: edit only /home/ubuntu/wt/macro-o3/bots/variants/cal-c/ (already created as a copy of charybdis).

## Why (measured)

Prism (passive: +1.5 Focus per carried gem; slot 0 = unit stun-damage 1.5 x Focus, slot 1 = ground 3x3 damage 1 x Focus,
both range 4, exclusive) keeps every gem it captures for Focus (`keeps_gems`, economy/bank.cc). About 90% of
teams draft Prism, and in our A/Bs both teams draft the same composition. Measured on charybdis vs itself:
- The hoard is the dominant mechanic: removing it (Prism banks like everyone) wins 28.7% against the reference;
  capping it at 300 gems 34.8%, at 600 48.4%.
- In Prism-kills-Prism deaths with 100+ gems, the victim had the SMALLER bag in 175 of 180 cases (97%). The bigger
  hoard wins the duel. The killer takes the whole bag (combat.kill), so the winner of the duel becomes bigger still.
- Big-bag deaths (100+ gems) occur 0.66 times a game, and the victim's team then wins only 15%. 80% of the victims are
  Prism. They die retreating (the debug branch is R, retreat, for the last 3+ turns: the retreat starts too late),
  banking a winning bag (B), or stopping an enemy game-ender (E).
- A narrative: an 844-gem enemy Prism killed four of our champions in one round with its 3x3 ground spell, our
  736-gem Prism among them, after our Prism spent ~25 rounds starting and cancelling a 74-turn winning tribute at
  the mid altar beside the enemy.

## Design

A team-wide reading of the Prism war, computed each turn from World beliefs, and used by the systems that already
decide those things (extend them; no separate mode):

1. **Hoard comparison.** For our Prism (self, or an ally Prism: exact bag in vision, else comms::bag_of) and each
   living enemy Prism (bag: exact if visible now, else its last seen gems; ChampionBelief gems/pos/pos_round): the enemy
   Prism *outguns* ours when its known bag is >= ours (the duel goes to the bigger bag; a tie is a coin we do not
   want to toss with the hoard at stake). Ours *dominates* an enemy Prism when ours is bigger. An enemy Prism never
   seen yet counts as neither (no information). Cassi/Issac and other champions are not part of this.

2. **Outgunned: keep out of its reach, early.** While our Prism is outgunned by enemy Prism E, E's *threat zone* is
   every tile from which E could hit our Prism with a stun next turn: within (its walk this turn + cast range 4) of
   any tile E may be on. Use the World's belief of where E may be (ChampionBelief `possible` board while it is
   tracked; its exact tile when visible; while it is beyond params::track_horizon unseen it could be anywhere: then
   use its last seen tile plus 1 tile a round since, capped, or no zone if that grows past the map; pick the cleanest
   available). Then:
   - our Prism's work steps do not enter the zone (bot.cc passes an `avoid` board to guard_work; the farm walk;
     see how home_reach_avoid / prism_hold_seen feed `avoid`), and its farm choice excludes groups whose work tiles
     lie inside the zone (or prices them as unreachable);
   - if our Prism already stands inside the zone, it leaves now (retreat/want_home path), before contact, instead of
     the late retreat it makes today;
   - our winning-bag tribute does not start while an outgunning enemy Prism could reach the altar before the
     channel completes (tribute_turns(bag) turns), and our Prism does not walk to an altar for a channel it cannot
     finish: it keeps hoarding (check keeps_gems/winning_bag/carry_bag/tribute_safe/any_risk paths);
   - allies carrying a bag of params::brake_bag or more also keep out of the outgunning Prism's zone (its 3x3
     ground spell kills clumps); allies without a bag are unchanged.
   - Our Prism does not take the stop-the-game-ender branch (bot.cc game_ender/stop_game_ender) against an
     outgunning enemy Prism; other allies still may.

3. **Dominant: the enemy Prism is the prize.** While our Prism dominates enemy Prism E and E was seen within
   params::track_horizon rounds, E is our Prism's priority target: find how chases are chosen (chase_with_guard,
   the strike search's target values, kill values using params::gem_value per carried gem) and make our dominating
   Prism pursue E when E is within reach of a pursuit (its walk + cast range within a few turns, using the same
   horizon the chase code uses), ahead of farming. Do not make it walk across the map after a stale sighting.

4. Debug traces (debug_block): one line when the posture changes for our Prism (round, handle, our bag, enemy bag,
   outgunned/dominant), when the zone blocks a farm choice or makes our Prism leave, when a winning tribute is held
   back, and when a dominant hunt starts.

Be careful with: cached/kept values in farm (GroupFacts contexts) that must see the zone change each turn; the
guard/avoid bitboards' semantics; fuel (the zone is one board a turn: build it once per turn, reuse); and that
everything degrades to today's behaviour when there is no enemy Prism or no reading of it.
