# E9 "lasthit": leave a carrier's killing blow to our Prism (bots/variants/lasthit)

Read /home/ubuntu/wt/macro-o4/research/macro-delphi/briefs/common.md first (TMPDIR rule; output under
/home/ubuntu/wt/macro-o4/replays/delphi-smoke/lasthit/). Candidate dir: `bots/variants/lasthit` (already created as a
copy of bots/charybdis). HARD DEADLINE: report by 22:20 UTC (`date -u`). Skip the auditor if the diff is under ~50 lines.

## Why
- Rules: the champion landing the killing blow gets all of the victim's carried gems. Our Prism gains 1.5 Focus per
  carried gem, which decides the Prism duel (in 87% of Prism deaths the victim had under 0.8x the killer's Focus).
  charybdis prices a gem in its Prism's bag at 1 + `carried_bonus` (economy/capture.cc).
- About 30% of our kills are landed by non-Prism champions. Their victims' bags go to those champions, worth 1 per gem
  instead of 1 + bonus.

## Design
When a non-Prism champion of ours is about to make a **killing** hit or cast on an enemy carrying gems
(`pair_gems(world, e) > 0`), it holds that blow if all of these hold:
- our keeping Prism (`keeps_bag`) is visible;
- it has not yet acted this round and acts before the victim's next turn (the turn order is known: World has slot or
  turn-order helpers, e.g. `world.slot(...)`; check `combat/plan.cc` and model/turn_order for what "acts before" uses);
- the victim is within its basic or cast reach (`attack_reach_in_turn` in model/safety.cc), and its ready damage
  (basic Strength or a ready damage cast at its Focus multiplier) kills the victim's current health plus shield.

Instead, that champion takes its best non-killing action (another target or a camp), or does nothing with that
attack. Find the single place where the strike search, or `attack_enemy`/`strike_enemy`, commits a killing blow, and
add the check there as a veto on that option only. Never veto when the victim is our attacker's own lethal threat
(it could kill us before the Prism acts), or when the game would be lost otherwise.

Debug trace: each veto (round, victim, bag), and whether the Prism then landed the kill.

## Done when
It builds and two local games finish without bot errors. Report the veto count and the Prism-follow-up kill count.
