# T6: unbiased stands, no flinching (candidate `bots/variants/macro2-stand`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/ocean-ref-b7c87cf` to `variants/macro2-stand`.

## Evidence (512 mirror games, debug D lines + replays; analyst report)
- 131 retreat runs (branch R) per team-game, mean 2.2 turns, 60% last one turn; 54% start <=3 rounds after the same
  champion's previous retreat (R F R flapping).
- 45% of runs are "wasteful-class": HP >= 0.8, no champion damage in the prior 5 rounds, nearest enemy >= 5 tiles.
  85% of them take no champion damage within 10 rounds; the enemy chases in only 10%; ~206 champion-rounds per
  team-game lost (retreat turns + the walk back).
- Mutual flinches: 58% of our runs have an enemy retreat starting within 2 rounds within 8 tiles; 21 events a game
  are both sides flinching on the same farm group; afterwards both come back (54%), and the capture splits evenly.
- Deaths: 83% die during or right after a retreat run; the fatal runs start at median HP 0.70, 42% after champion
  damage, the enemy chasing in 47%, nearest enemy 4. Only 16% of fatal runs start healthy at distance >= 5.
- Earlier repo finding (research/EXPERIMENTS.md): "every fight model reads equal fights as lost". In a mirror
  both sides' stand tests say "lost", so both retreat. That is a biased model, not a real threat.

## Principle
A retreat is insurance against a fight we would lose. A stand is only lost if the enemy actually commits to it.
Initiative goes to the side that does not have to walk in: an enemy that must walk or dash into reach of us arrives
on its turn and is struck by us on ours before it can follow up, unless it can already strike our tile from where
it stands, or it can reach and strike within its next turn. Ocean's stand test (`stand_lost_at` in combat/fight.cc,
via `Safety::stand_reach` / `stand_roster` / `stand_trade`) and the pack-zone `outmatched` (combat/guard.cc
`pack_members_of`, which for healthy champions applies only on their own ground) decide most of these retreats.

## What to build
1. First, find out which trigger fires in the wasteful class: add a debug trace in `want_home` naming the trigger
   (recall line, outmatched/pack zone, mono/camp trap, camp_fled, Willow exposure, stand_lost_at) with HP share,
   bag, nearest visible enemy distance and whether we took champion damage last round. Play 2-3 local games, count.
2. Make the stand test unbiased for a champion that is not under attack: health >= `params::hurt_health_fraction`
   of max, no champion damage taken since our previous turn (ocean tracks damage taken; find the existing field),
   not linked (Cassi/Issac keep their current test: two lives at stake), bag below `params::brake_bag`:
   - If no roster enemy can strike our tile before our next turn from where it stands now (i.e. every one of them
     must walk/dash in first), judge the stand with US striking first (the initiative goes to the side not walking
     in). Use the existing sim machinery: find how `stand_trade` / the fight simulator order initiative and reuse the
     ordering it already supports; do not write a new simulator. If an enemy can already strike us, keep the
     existing ordering.
   - Apply the same initiative rule wherever the healthy own-ground pack zone (`outmatched`) would send such a
     champion home, if it is cheap to do through the same stand machinery; otherwise leave the pack zone as is and
     say so.
3. Leave alone: the recall line (low HP), camp traps, `camp_fled`, lethal checks, the step guard (lethal tiles stay
   off limits), chase/prey, hurt or bag-carrying or linked champions, and Willow's own rule (a healer holds no fight).
4. No new tuned constants; if you need a threshold, derive it from rules (ranges, dash) or existing params.

## Check
Trace `STAND round handle trigger old_lost new_lost nearest_dist` when the verdict changes. Build, 2-3 local games
(at least one generated map), audit, report as common.md says, including the trigger counts from step 1.
