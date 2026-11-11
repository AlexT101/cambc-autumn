# Brief G: the stun window (threat model correctness)

You are an implementation subagent for the macro4 lead. Work ONLY in /home/ubuntu/wt/macro4 (git worktree, branch
macro4-20261111). Never touch other checkouts, never edit bots/variants/ocean-ref-b7c87cf, bots/ocean, or any
bots/variants/macro4-* other than your own, never write to any Claude memory directory, never run ab.py / fgate / A/B
tests, commit nothing. Read /home/ubuntu/wt/macro4/AGENTS.md and cambc-rules.yaml first.

## Base
hub2f (bots/variants/macro4-hub2f; our best, 55.5% vs ref). Make these directories, each with
`./copybot variants/macro4-hub2f variants/<name>`:
- macro4-g1: piece 1 only. macro4-g2: piece 2 only. macro4-gall: pieces 1+2+3+4.
Edit only those directories. No draft/ or emblem changes.

## Evidence (micro study of 79 deaths of our 100+-bag Prism where a smaller-bag enemy Prism killed it; scripts
/home/ubuntu/wt/macro4-maps/scr/pduel_*.py, pduel-cls2.json)
- Whoever fires first wins: in 55/79 the enemy's stun + its following ground spell (2.5x its Focus) was >= our HP;
  17 were one-shots. A stun removes the target's next turn, so the reply never comes.
- Classes, by our last turn before its first hit: stepped into its ready reach (6->5, 5->4) 23; kept a tribute
  channel while it walked up 15 (14 were winning bags with 26-92 channel turns left; we saw it coming in 10);
  stood in its reach with no shot 14; it moved after us and acted first next round 8; walked at an enemy Prism that
  was tributing, to stun it (walking forbids the exclusive stun that turn) 6; other 13.
- The enemy Prism was unseen by ours on that last turn in 29/77 (20 of the 43 C/D). Our stun was usually ready.
- Allies within 4 cut death from 4.7% to 1.1% of exposed rounds.

## Pieces
1. **Stun window in the threat model.** `Safety::lethal()` (model/safety.cc) compares `worst_damage(p)` - one turn's
   blows - with our health. Per the rules a stunning blow also removes our next turn, so the same enemy (and any
   other enemy whose reach covers us) gets a second blow before we can reply: price a stunning blow as that blow
   plus that enemy's best blow on its next turn (abilities by cooldown readiness then), plus the other enemies' next
   blows. Find every consumer of lethal / worst_damage (stand_lost_at in combat/fight.cc via want_home, step_guard in
   combat/guard.cc, escape, strike search) and make sure the change is consistent. This applies to every stunner
   (Prism, Tavi, Ren, Ryth, Heart of Ruin, Marcella's reset, Cassi), so it is a model fix for all comps, not a Prism
   rule. Do NOT add bag-based caution (a previous attempt that made carriers count their fall at bag >= a life lost
   6 points); the fall still counts only where the existing fight logic already counts it.
2. **Unseen threats in step_guard.** step_guard() / step_guard_cover() begin with `if (!enemy_seen(world)) return
   nullptr;` and GuardFoes lists only seen enemies, so an economy walk has no strike guard against a tracked-but-
   unseen enemy (ground spells hit unseen champions). Use the tracked threats (`threats()` / belief positions with
   their staleness as already modelled) so that tiles where the (stun-window) lethal test fires are guarded, as long
   as our current tile doesn't fire it too. Keep fuel bounded; the early return exists for fuel, so keep a cheap
   early-out when no tracked threat can reach.
3. **stop_game_ender** (combat/fight.cc): it clears the guard and walks into stun range; the walk forbids the
   exclusive stun that turn, so the tributer casts first. Stop on the last tile outside its cast reach and make the
   final step only when we can cast that turn (i.e. step+cast is impossible for exclusive spells: approach to a tile
   from which our stun reaches without walking next turn, while outside theirs if possible), or keep the guard on
   the final step.
4. **Tribute channel vs a lethal stun window.** continue_tribute (economy/bank.cc) keeps the channel when
   !want_home && winning_bag. With piece 1 the want_home test sees the real window; check whether a channelling
   champion's want_home is even evaluated for an approaching stunner whose window will be lethal before the channel
   ends, and cancel (gems stay carried) only when it is lethal before the next turn we could still act.
Add `debug_block` lines prefixed `STUN` where a decision changes because of the window (lethal only via the window,
guard tile rejected from unseen threats, game-ender stop, tribute cancelled).

## Done when
- All three directories build (debug and `--release`, sequentially) and play one or two smoke games each vs
  ocean-ref without errors; report STUN trace counts and OOF lines vs hub2f in the same game.
- A read-only auditor (Explore or Plan) reviews the gall diff (g1/g2 are subsets): correctness of the window (turn
  order: an enemy acting after us in the same round vs before; cooldown ticks), fuel, magic numbers. Fix findings in
  all directories.
- Final reply: design as built, diff summary, audit findings and fixes, trace counts.
