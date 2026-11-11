# E1 "rally": the team answers fights (bots/variants/rally)

Read /home/ubuntu/wt/macro-o4/research/macro-delphi/briefs/common.md first and follow it. Candidate dir:
`bots/variants/rally` (already created as a copy of bots/charybdis). Reference: `bots/variants/charybdis-ref`.

## Why (measured)
- charybdis mirror (512 games, 2x fuel): kills decide games. Winners average 6.9 kills and 2.2 deaths, losers 2.1 and
  6.8; losers spend 12% of their turns dead. Prism deaths decide most (the side whose Prism dies first loses 90%);
  Prisms die in team fights (typically 3-5 enemies within 8 of the victim), mostly while retreating ('R').
- Earlier mirror studies (research/macro-2026-11-11/macro1/macro1-log.md, Evidence 2): at fight start ~1.7/2.8/3.4 of
  a side's ~4.9 bodies are within 4/8/12, and only 0.3 more arrive in the next 5 rounds. Allies 5-8 tiles from a dying
  teammate: 13% fought, 47% kept farming. More bodies wins the fight 64%; the initiator 68%.
- The best ladder team (Fish; research/ideas-2026-11-11/fishfight/README.md, read its "What real Fish does" section):
  its edge is not micro but **who fights**: its whole pack turns on the target (its Cassi, Issac, Vendetta, Willow hit
  champions where ours keep hitting the camp), with 1.65 bodies within 4 of the target the round before the first hit
  against our 0.83-1.10. The first target dies 38% vs 16%, and the kill rate climbs with attackers within 4 (Fish: 0 ->
  9%, 1 -> 30%, 2 -> 43%, 3+ -> 56%). It concluded the gap is in the strike planner's caution and in farm routing.
- Earlier coordination attempts that failed (research/macro-2026-11-11/macro2/macro2.md "What failed"): joint
  ENGAGE/DISENGAGE verdicts over comms (level: fewer deaths, no economy), pair stakes, summons and packs (walking cost
  more than the fights gained; summoned champions came late or did not listen). So: no summons, no pack mode, no
  rigid commitment. Each champion decides for itself from shared facts, only for fights it can reach in time, only
  when its arrival makes the fight favourable, and it stops the moment that stops being true.

## Design
1. **Fight facts.** A champion is *engaged* in a round if, on its turn, it hit or cast at an enemy champion, or took
   champion damage since its previous turn, or ends its turn with a visible enemy champion within that enemy's strike
   reach (its walk + attack/cast range, as the bot's Safety/threat code computes reach). Make this known to allies:
   allies in sight already see the enemy and the engaged champion; for allies out of sight, post a compact fight
   beacon in the 8 shared bytes (model/comms.cc: read its layout comment; find room, e.g. a free-bits record, a flag
   in the `ally` position record, or a narrower existing field; degrade gracefully when the layout has no room). The
   beacon needs the fight's tile (to within the existing position-record precision) and recency (a round mod 4 as the
   ally record has). Also post what the enemy side there is, if it fits (a count of enemies seen), else readers use
   their own enemy beliefs (World's enemies with positions and last-seen rounds).
2. **Who answers.** On its turn a champion that is not engaged considers the most recent fight (seen or posted within
   the last 2 rounds) whose tile it can reach (walking distance: use an existing field towards the tile, bounded by a
   Chebyshev pre-check) within `ability_cooldown` (8) rounds: one cooldown is the length of an exchange of casts,
   arriving later misses it. It answers only if all hold:
   - it is not channelling, not holding a counting capture that pays within 2 rounds, not banking/carrying a bag the
     bot is walking to an altar (bank branch), and its health is above `params::hurt_health_fraction`;
   - with it added, our side is at least level with the enemies around the fight: use the bot's own fight model
     (Safety's team-fight simulation / the pack-zone "outmatch" test in combat/guard.cc, which compares health x damage
     a side) on our champions that are engaged or answering within reach vs the enemies believed within 8 of the fight
     tile; a fight we would lose even with us is not joined (do not feed);
   - a Prism answers like anyone (it is the team's main damage), but a Prism whose Focus is under the largest seen
     enemy Prism's does not walk towards a fight that enemy Prism is in (the weaker Prism dies in 63% of Prism deaths).
3. **What answering does.** In place of the farm branch's walk (and of camp hits while walking), it steps towards the
   fight with the bot's guarded walking (`step_safely` / the step guard), so it never steps into a tile the guard
   forbids. Once an enemy is in its reach the existing strike search takes over as usual. The answer is re-decided
   every turn (no memory of commitment beyond the beacon's recency), so it stops when the fight ends or turns bad.
4. **Nobody keeps the camp.** When an ally within 4 of us is engaged and an enemy champion is within our basic or cast
   reach, our basic attack and damage casts go to enemy champions rather than camps (find where the strike search /
   farm's `attack_in_range` and the hold branch choose camp hits while enemies are in reach, and make champion targets
   win there whenever the strike search finds a legal champion hit that its own safety checks allow). Do not override
   the strike search's safety: only the camp-vs-champion preference.
5. Debug traces (debug_block): each answer (round, champion, fight tile, walk, sides' strengths), each turn a camp hit
   was replaced by a champion hit.

## Not in scope
Draft, emblems, banking thresholds, the Prism carry economy, retreat logic (want_home stays in charge of leaving).

## Done when
Builds; three local games against charybdis-ref finish without bot errors; traces show answers firing (report how
many a game, how often the answering champion arrived while the fight was still on). Report as common.md asks.
