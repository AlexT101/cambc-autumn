# Brief A: the engagement pact (team-fight commitment)

You are an implementation subagent for the macro4 lead. Work ONLY in /home/ubuntu/wt/macro4 (git worktree, branch
macro4-20261111). Never touch other checkouts under /home/ubuntu/wt/ or /home/ubuntu/cambc-autumn, never edit
bots/variants/ocean-ref-b7c87cf or bots/ocean, never write to any Claude memory directory, never run ab.py / fgate /
A/B tests. Read /home/ubuntu/wt/macro4/AGENTS.md and cambc-rules.yaml first (C++ API: docs/api/cpp.md,
sdk/cpp/cambc.h). Commit nothing; the lead commits.

## Candidate
Create it with `cd /home/ubuntu/wt/macro4 && ./copybot ocean variants/macro4-pact` and edit only
bots/variants/macro4-pact/src. Do not touch draft/ or emblem selection (shop.cc's emblem choice).

## Why (evidence from 256 mirror games, ocean vs ocean)
- Games are decided by lopsided fights: of multi-death clusters, 2-0 271 times and 3-0 50 times against 101 1-1
  trades. The side that dies first loses 63%; first to a 2-death lead wins 73%.
- At the first death the victim had an ally within 4 tiles in 62% of cases, yet 66% of victims got no ally hitting
  back. Of the allies within 8 tiles at the first hit: 32% hit the attackers, 32% retreated, 17% kept hitting their
  camp, 5% kept holding a capture or banking. Typical sequence: the enemy pack farms next to the victim, the victim
  retreats, the pack chases and gets a 2v1/3v1 while our nearby allies each retreat or farm on their own verdict.
- Structural cause: every champion decides stand/retreat/join alone, with a roster of the allies IT sees within
  safety_params::fight_ally_radius = 4 (chasing_ally_radius 7 for allies posting the chase bit) and the pack zone
  (guard.cc `outmatched`, pack_ally_radius). Verdicts are inconsistent across allies, so nobody can count on anyone.
  Earlier tries: widening fight_ally_radius to 8 lost (counted allies did not come); a distress beacon + assist
  branch was level (fights better, economy worse: allies left farming on health/distance rules, not on whether
  their joining wins the fight). The missing piece is a consistent, committed roster.

## Design: one shared contact signal, consistent rosters, joins that win
Generalise the existing chase bit (comms.cc `chasing`/`ally_chasing`, priority payload bits 11-13, read only while
the ally is visible; ally_chasing widens that ally's roster radius to 7 in safety.cc `fighting_allies`) into a
contact state that every member of a local fight posts and reads:
1. **Contact post** (priority payload, like the chase bit): a champion posts `engaged` at its turn end when it struck
   an enemy champion this turn, or a visible enemy can hit its tile before its next turn, or it chases; and
   `joining` when it is walking to join an engaged teammate (point 3). Encode with round&3 as the chase bit does, so
   readers accept posts from this round or last. Keep the claim (bits 0-7) and support mailbox bits intact; find free
   payload bits (priority_payload_bits = 16 in turn_order.h; check what turn_order.cc puts above it).
2. **Consistent roster**: in `fighting_allies` (safety.cc ~764) and wherever the pack zone counts allies
   (guard.cc `outmatched` and the ally counting it uses), an ally posting engaged or joining counts from
   chasing_ally_radius (7) instead of 4, with its arrival delayed as walk_allies_in already does for chasing allies.
   So the engaged champion does not flee from a fight its allies are converging on, and the joiners count each other.
3. **Join when it wins**: a champion that is free (alive, not mending/leaving per want_home, not channelling, not
   holding a capture whose payout is within 2 rounds, carrying a bag below params::brake_bag unless the bag is
   protected by the fight being near-won) and sees an engaged teammate within ~7 tiles walking (its strike reach plus
   two turns of walking) evaluates that fight WITH ITSELF ADDED, using the existing machinery (team_pressed / prey /
   chase_trade with its own arrival delay, `escapes` verdict). If the team's fight is won with us and is lost or
   uncertain without us (or the teammate would otherwise fall), it posts `joining` and goes: set the strike search's
   aim at that fight (chase_aim / intent.aim) and step toward it (the chase branch's walk), overriding farm, contest,
   siege and shop (not mend/leave/hold-with-imminent-payout). Prefer extending `team_pressed` + `prey`/`chase_aim`
   (fight.cc ~641-959) over a new bolted-on branch: today team_pressed only takes a teammate's visible fight where the
   enemy is in the ally's attack range and hurt below the ally's health share; widen it to any engaged teammate's
   enemies within reach of us in 2-3 turns, judged by the fight sim with us counted.
4. **Retreat together**: when an engaged champion's verdict is still lost with joiners counted, and a teammate posting
   joining/engaged is nearer than our spawn along the escape route, let the escape planner (model/escape.cc) treat
   tiles within 1 of that teammate as a goal like home (it retreats into help, not away from it). Only if this is
   simple in escape.cc's goal machinery; skip it otherwise and say so.

Keep everything rule-derived (reach, walking turns, the fight sim's verdict); no new tuned magic numbers beyond
reusing existing radii. Add `debug_block` trace lines (prefix `PACT`) when a champion posts engaged, decides to join
(with the teammate, enemy count, verdicts with/without us), and when a roster counts a joiner, so the lead can count
them in debug replays.

## Done when
- It compiles: `cd /home/ubuntu/wt/macro4 && cambc build bots/variants/macro4-pact` (and a `--release` build).
  Check tools/README.md if the build command differs.
- A couple of local games run without errors or crashes, e.g.
  `cambc run bots/variants/macro4-pact bots/variants/ocean-ref-b7c87cf --map 00ambush` (see cambc --help for the
  exact syntax), and PACT lines appear in a debug run's stdout.
- Then spawn a read-only auditor subagent (Explore or Plan type) with this brief and your diff
  (`diff -ru bots/ocean/src bots/variants/macro4-pact/src`): check the diff against the brief for bugs, unintended
  behaviour changes, stale-payload reads, fuel blowups (2x fuel is the test budget, but no per-tile loops over
  unbounded sets), and turn-order/payload bit collisions. Fix what it finds.
- Report back: a concise summary of the diff (files, functions, what each change does), the payload bits used, the
  auditor's findings and your fixes, and anything you skipped. Stop there; keep scope bounded to this brief.
