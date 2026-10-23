# Follow-ups from the v38 replay analysis

Changes to try, drawn from [REPLAY-ANALYSIS.md](REPLAY-ANALYSIS.md) by two independent reviews. Each item gives its evidence, the change, its risks, and how to judge it.

## Review 1

I worked from the code up. I read each finding's code path in `bots/hyperion/src` and re-read the trace for one or two of its cases with `v38lib`. I also ran one new scan, over winning-bag tributes (R1-1). Line numbers are v38's (5b02a02).

### Root causes shared by several findings

1. **One stage chooses a plan and a later stage vetoes it, with no feedback.** The chooser picks the same plan again next turn, so the champion freezes or wastes turns.
   - B1: `farm` prices a spell clear that `camp_cast`'s value floor refuses.
   - B2: the dash fields price a crossing that `dash_across` refuses.
   - B4a: `capture_recall` times a ride that `continue_recall` cancels at payout.
   - B3 is a milder form: the shared pick depends on what we see this turn.

   The fixes make the two stages agree: the executor accepts what the chooser priced, or the chooser models the veto. They are bug fixes, not tuning.
2. **Risk checks that ignore how long or how we are exposed.**
   - A1/D2: `any_risk` ignores the channel's length.
   - B4b: the shop and bank recall keeps skip `recall_outruns`, which the home keep uses.
   - D4: `tribute_safe` models death but not stuns.
3. **The threat model is optimistic in places we can name.**
   - A3a: an enemy's second turn uses its first turn's cooldowns.
   - A4: a bush tile we cannot see is treated as hidden from an enemy's unseen ward.
   - A3b: the step guard's fuel gate.
4. **The leave path bypasses the planner.** On a retreat turn `decide` calls `retreat()` and never runs the strike search. C1 (kills walked away from), C3 (casts held) and A2 (stand-and-cast) all follow from this. The full fix is strike phase 4a (a search on retreat turns), which is fuel-bound (TODO #5). R1-6 is the cheap slice of it that the evidence clearly supports.

### Suggestions, ranked by expected value

#### R1-1. A winning bag is tributed at any risk only when its channel is short (bug fix: decision rule)

- **Evidence.**
  - A1/D2. `any_risk` (bot.cpp:656) returns true for any `winning_bag`, so `tribute_ok` (bot.cpp:660) never consults `tribute_safe`. That holds for `submit_here` (669), `continue_tribute` (3948) and `can_tribute_safely` (3135).
  - Re-checked **ddbc8901-3 r1974-1976**. Our Vesper holds 2,490 gems with `ch=trib:196`. The enemy Vesper is visible at 24,16 (distance 4) and the enemy HoR at 24,17-18 (distance 2-3). Every turn shows `tribute keep=1 why=safe`.
  - My scan of every trusted winning-bag tribute over 6 turns (our score from `tribute_end` totals, plus the bag): 95 channels in 63 games.
    - 46 completed, 26 ended in death, 18 in a stun, 4 in a lock, and 1 was still running at the end.
    - The proxy for `tribute_safe` failing is a visible enemy (TB `v=1`) within 4 tiles on one of our turns during the channel.
    - All 26 deaths had one. Of the 46 completions, 39 never did, so the change would most likely leave them alone. Only 7 did and are at risk of being cancelled or delayed.
    - The 7: 2e0e5476-1, ddf817bb-5, 195988e7-2, bee3c30a-2, 3f146df4-3, a4dc726e-4, 1ad29aed-2.
    - So the trade is about 26 deaths, each handing over a winning bag, against at most 7 delayed completions.
    - The script is `wb.py` in my session scratchpad, not committed.
  - `tribute_safe`'s own comment says why the rule should apply here: "a long bag's whole channel would wait on any enemy in sight". It is re-judged every turn over `min(turns, tribute_window)`, so a long channel starts when no visible enemy can kill within 6 turns and is cancelled once one could.
- **Change.** In `any_risk` (bot.cpp:656):
  ```cpp
  return (winning_bag(world) && channel_turns <= params::tribute_window) || rounds_left(world) <= channel_turns + endgame_slack;
  ```
  - A longer winning channel then goes through `tribute_safe`.
  - `continue_tribute`'s fallback (3950) still keeps it until we are damaged or `want_home` fires, so it cancels only on a real threat.
  - Optional: keep the any-risk path when the enemy's live bags could also win. `game_ender`'s first lines (`carried >= need`, bot.cpp:3253-3258) give that cheaply. `game_ender` returns nothing while our bag wins, so after this change a winning carrier that flees ignores an enemy's winning tribute.
- **Expected effect.**
  - Most of the 26-32 winning-bag deaths on long channels (21-24k gems, 19 of 33 games lost) become a flee with the bag.
  - A bag passed to the killer is usually a winning bag for them. Those deaths cost the game, not just the gems.
- **Risks.**
  - A long channel near a camping enemy may never complete: on `01boss_battle` the bag can circle until round 2000.
  - The endgame clause still forces it in the last `channel + 2` rounds. That is pointless once `channel > rounds_left`; add `channel_turns <= rounds_left(world)` there too.
  - Fleeing with 2,000 gems can still die. It is no worse than standing for 200 turns beside the enemy.
- **Judge.**
  - `ab.py` will barely see it: winning-bag channels over 6 turns need huge bags, which self-play rarely makes. Expect level, and keep it if level (a logic fix).
  - Watch gems lost on `d=T` deaths and the completion rate of winning-bag tributes over 6 turns.
  - Then the ladder: `01boss_battle` (6 of 13 won) and `00collision` (8 of 22).
  - Also make the tracer print `why=risk` for the `any_risk` branch (trace-bot bot.cpp:4013), so the next analysis can tell the two apart.
- **Confidence:** high that it is right; medium on its size in win rate. Review 2 reached the same change independently (R2-1), from the opponents' behaviour: they cancel long winning channels (48 times) and die on them far less.

#### R1-2. Spell clears always finish what they stand there for (bug fix)

- **Evidence.**
  - B1. `spell_clear` (bot.cpp:1547) stands in spell range and outside every attacker's reach, then calls `cast_at_camp(world, g, true)`.
  - In `camp_cast`, `attackers_only` makes `post_basic` false (abilities.cpp:398), so `all_visible` and `sole_finish` are false. The floor is then `min_camp_value = 50`, while a cast is worth `min(raw, health)`.
  - Once the attackers have under 50 health left, nothing can act. The cast is refused, the basic attack is out of range, and `spell_clear` still returns true.
  - Re-checked **09de3c49-2 c5**. Group 4 is two wolves and a gem cluster, at distance 4 from the Prism's tile 5,57. The last cast was at r328. From r337 both slots are ready (`cd=0,0`), and every turn reads `farm best=4 v=1.684 steps=4`, with no cast and no move, for 867 rounds.
  - 84 runs, 20.6k turns in 56 games, 4.6k gems held.
- **Change.** In `camp_cast`, when `attackers_only`, lower the floor to `min(min_camp_value, the live attackers' total health)`: a cast that deals all that is left is never refused. This covers both wolves in the case above, which `sole_finish` alone (one member) would not.

  The simpler `all_visible = post_basic || attackers_only` would fix only the one-member case. `spell_clear` is the only caller that passes `attackers_only = true` (bot.cpp:1571), so no other cast changes.
- **Expected effect.** The Prism finishes the group, captures it and moves on. That is about 20k frozen Prism turns back, and the carried bags are no longer held idle.
- **Risks.** A cast for 10 health spends an 8-round cooldown. That only happens on the turn that ends the spell clear, which is the purpose of the station.
- **Judge.**
  - `ab.py`, keeping it if level.
  - Watch Prism idle runs at a chosen live group under 50 health. Grep a traced run for `farm best=g` with no TA on 8+ turns; it should drop to about 0.
- **Confidence:** high.

#### R1-3. Landing dashers' fields drop crossings the mover will never take (bug fix: model mismatch)

- **Evidence.**
  - B2: 34.8k turns in 50+-turn episodes, in 86 games, including every `00great_wall` and `01islands` game. In this set `00great_wall` was 8 won of 28 and `01islands` 8 of 14.
  - The analysts call `dash_across`'s wake ban the defect. **I disagree on great_wall.**
    - Re-checked **28c601b7-5 c4 r600**. The HoR alternates 30,16 ↔ 31,16. Every landing past the row-17 hole line (28-31,18) is within 1 of group 1, a **Monolith** plus a gem cluster at 29-30,19-20.
    - The HoR's landing hit would wake a 20,000-health Monolith, so refusing it is correct.
    - The defect is that the dash fields (`find_crossings`, world.cpp:775-822; `static_walls()` returns `dash_walls` for any dasher) keep that crossing open. Bank and farm then choose targets that only it reaches.
  - On `01islands` (**9fa0e422-2 c4**, 28,14), the landings past the row-15 holes touch group 12, a wolf (strength 20) plus a gold cluster. There the ban is over-cautious, but the same fix ends the freeze.
- **Change.**
  - In `find_crossings`, for a champion whose dash `lands()`, drop a crossing tile c in direction d when either landing tile c±d is within the landing radius of a camp tile of a group with a harmful member (`strength > 0`). This is the static form of `landing_wakes`.
  - `StaticMap::build` (world.cpp:826) has no champion, so build a `landing_dash_walls` board, with its own `near_crossable`, beside `dash_walls`. `Pathing::static_walls()` (pathing.cpp:23) and `dash_across` then pick it when the champion's dash lands.
  - The cost is one pass at map load. For a dead group it errs closed, which costs a detour and not a freeze.
  - Optionally, `dash_across` could then accept a landing that wakes only a weak group (summed strength × `max_camp_reach` below spare health), which would let the islands HoR fight the wolf.
- **Expected effect.** No HoR freezes at hole lines. Targets beyond them are priced by the walk, or dropped when there is none (an island).
- **Risks.**
  - Some legal crossings are lost while their group is dead.
  - A bitboard pass per crossing direction is a one-time cost.
  - The Vesper freezes in B2 (no landing) are a different guard, which neither the analysts nor I found. Goals exclude hole tiles (pathing.cpp, `search_approach`), so it is not an unreachable goal. It needs a level-2 trace with pathing detail.
- **Judge.**
  - `ab.py`, plus a fresh mapgen suite with hole lines if mapgen makes them.
  - Watch dasher idle episodes of 50+ turns and HoR gems tributed on great_wall-like maps.
  - Then the ladder on `00great_wall` and `01islands`.
- **Confidence:** high that it is the right fix for HoR; medium on the size.

#### R1-4. The enemy's second turn uses that turn's cooldowns (mis-estimate, narrowed w2-chain)

- **Evidence.**
  - A3a. `Reach::build` reads readiness once, at `turn_round` (safety.cpp:1318), and `build_ways` uses the same `ready` for turn 1 of a `twice` build (1408-1415). `threat_strike`'s widened strike reuses `strike_memo(c, next_turn_round)` (822-836).
  - Re-checked **5e559ba0-1 r622**. Our HoR c9 farms at 29,13-14. Marcella is at 25,17 with `rr=624,623` and `act=0`. The turn order puts her after c9 in r622 and first in r623.
  - She did not move: at r623 t0 she cast slot 1 from 25,17 for 1000. The bot had `ls=-1` and `fs=0:0:0:0:0:0`, so it believed the tile was safe.
  - 203 deaths (144 games, 4.9k gems), 19% of deaths by cast. They are concentrated on Marcella, the ladder's main killer (821 of 3,042 deaths).
- **Change.** This is the TODO's "narrowed to slots readied for turn 2", not the w2-chain that lost (47.1%, both slots across both turns, out-of-fuel turns +20%).
  - In `build_ways`, pass a second readiness array for turn 1: `e.ability_ready(slot, turn_round + 1)`. Add it to the `Recipe`/`ways_by_` key; the index grows from 3 bits to 5.
  - Still allow one cast across both turns. The turn-1 ways already stand for "walk on turn 0, act on turn 1".
  - In `threat_strike`, take the `walked` term from `strike_memo(c, next_turn_round + 1)` when `turns_before_ours >= 2`. Both are memoised per round.
- **Expected effect.** `lethal`, `stand`, the step guard and the search see a nuke that comes off cooldown between the enemy's two turns. That covers most of the 203 deaths, all but the 7 with unseen killers.
- **Risks.**
  - More tiles read as dangerous: more retreats and fewer farm steps near Marcella.
  - Fuel: one more `ways_by_` recipe per enemy acting twice. Measure out-of-fuel turns. The lost w2-chain's cost came from chaining both slots, which this does not do.
- **Judge.**
  - `ab.py` against current. Report out-of-fuel turns alongside the win rate.
  - Keep it if level and out-of-fuel turns are not up materially; it is a logic fix.
- **Confidence:** medium-high on the logic; medium on the fuel.

#### R1-5. A champion that wants home keeps no recall that cannot outrun its pursuers (bug fix: decision rule)

- **Evidence.**
  - B4b. In `continue_recall`, the home keep requires `recall_outruns` (bot.cpp:3977). The shop keep (`wants_shop`, 3219) and the bank keep (`recall_to_bank`, 3150) check only `threatened()`, which flips turn to turn.
  - Re-checked **db84c66d-3 c5 r659-663**. Prism, 80 health, 60 gems. Every turn reads `home v=1 why=low`.
    - r659 and r662: `recall keep=0 why=home_unsafe` and a retreat step.
    - r661 and r663: `recall keep=1 why=shop` (`ts=0`) and no move, with Marcella at distance 3.
  - 61 deaths, 1,477 gems; 258 such alternations.
- **Change.** In `continue_recall`, once `*home` is true and the home keep failed, skip the shop and bank keeps unless `recall_outruns(world, safety)`. The reason the home recall was refused applies to every recall. Champions that do not want home are unchanged.
- **Expected effect.** Retreats walk every turn instead of every other turn, which means fewer of those 61 deaths.
- **Risks.**
  - A few shop trips that would have landed are lost. They are re-offered once the threat is gone.
  - Fuel is negligible: `recall_outruns` is one loop over the enemies, already run on most of these turns.
- **Judge.** `ab.py`, keeping it if level. Watch k-R-k alternations and deaths within 4 turns of a shop or bank keep.
- **Confidence:** high.

#### R1-6. Take a one-hit kill before retreating (behaviour change, small)

- **Evidence.**
  - C1. `retreat()` (bot.cpp:4002) never runs the strike search.
    - A ranged champion never basic-attacks on a retreat turn: `walk_and_attack_independent` is false, and `reset_and_attack_enemy` needs the attack already spent.
    - A melee champion attacks the weakest enemy from its start tile, before the step.
  - Re-checked **77b4141d-4 c1 r518**. Our Vesper, at 894/1000, sees the enemy Vendetta adjacent at 14,7 with `hp=16/1200`. The TA lines are only `dash_away` and `retreat_step`. The Vendetta was still at 16 the next round, in a bush.
  - Strict windows: 119 turns in 90 games, and 74 of those enemies were alive 3 rounds later.
  - In the mirror, +1 net kill at round 300 takes the win rate from 56% to 85% (EXPERIMENTS lessons).
- **Change.**
  - At the top of `retreat()`, for every champion: if a visible enemy in attack range dies to one basic attack (health plus shield ≤ Strength × `taken`, as `reset_and_attack_enemy` tests), attack it first.
  - Vesper and Issac can still `dash_away`, since a dash spends neither the walk nor the attack. A ranged non-dasher gives up the step for the kill.
  - Melee: when no kill is in range at the start tile, attack after the step instead of before it, so a kill beside the end tile (2721e800-5 r44) is taken.
- **Expected effect.** About 70 more kills across 624 games, each worth 100 gold, the bag and 60 enemy rounds, and it removes a pursuer.
- **Risks.**
  - A ranged non-dasher that kills instead of stepping can be caught by a second enemy. Only 2 of the 53 strict ranged turns were not Vesper, so this is rare.
  - Melee moving its attack after the step loses chip damage from the start tile, which is worth little on a retreat.
- **Judge.** `ab.py`. Watch kills per game and our deaths within 2 rounds of a retreat-turn kill.
- **Confidence:** high on the kill-first part; medium on the melee reorder. Ship the first alone if in doubt.

#### R1-7. Bush tiles we cannot see are not concealment from an enemy whose ward we do not see (mis-estimate)

- **Evidence.**
  - A4: 196 deaths (131 games, 3.8k gems) on a bush tile whose cluster held an enemy ward, against 15 bush-tile deaths without one. 163 of the 196 had stepped into the bush that turn.
  - The case a0bf6932-4 r652 has the killer's own ward at 7,21 inside the cluster.
  - In `Reach::at` (safety.cpp:1504-1525), a bush tile is seen only from its cluster or by a ward we see (`ward_of` / `ward_sees`). An enemy's ward inside a bush is invisible from outside it.
  - EXPERIMENTS already notes "Reach is bolder than reality beside our bush clusters".
- **Change.** In `Reach::at`'s `seen` lambda, treat a bush `p` as seen from anywhere (`win_full`) when we cannot see `p` (`!test(world.visible, p)`) and this enemy's ward is not in sight (`ward_ < 0`).
  - It is per owner, since a champion sees only through its own ward.
  - It costs one bit test per bush query, and only for owners whose ward we do not see.
  - It is not the "remember wards" change that was level (49.6%, stale 90%). It assumes nothing about where a ward is; it only refuses to assume where one is not.
- **Expected effect.**
  - Steps into unseen bush clusters stop reading as safe from casters with a ward down. That affects mostly the Marcella and Vesper deaths at distance 3-4.
  - Inside our own cluster, which we see, nothing changes.
- **Risks.**
  - Bushes lose value as hiding places against enemies whose wards are unaccounted for.
  - The base rate of surviving bush steps is unknown. The 196:15 ratio counts deaths only.
- **Judge.** `ab.py`; self-play wards bushes too (`ward_bushes`). Watch deaths on bush tiles and out-of-fuel turns.
- **Confidence:** medium.

#### R1-8. A capture recall is kept through the payout it was timed for (bug fix)

- **Evidence.**
  - B4a. `recall_to_bank` returns false while `memory.banking` is false (bot.cpp:3151). `banking` is set only in `carry_bag` and `retreat`, after `continue_recall` has run. So the turn the capture pays, the recall is cancelled with 1 turn left and restarted for 5.
  - Re-checked **24d1a6f9-1 c6 r71-77**.
    - Our c9 cleared group 2 at r70, and `capture_hold` is at r71's capture phase.
    - The Vesper stepped on at r71 and kept the recall for `capture` at r73-75. It cancelled at r76 (`rec:1`) after the payout, stepped once, and kept a new recall for `bank` from r77.
  - **Correction to B4a's "timed to land one turn after payout".** The recall is timed to land at the payout the bot *believes*. `World::hold_start` takes the later possibility on purpose ("Late costs a round, early the capture", world.cpp:1722-1726). Here the hold began with c9 at r70, so payout was r76, while the Vesper believed 77.
- **Change.** In `continue_recall`'s non-holding branch: if last turn kept the recall for a capture (`decision == 'Q'`, kept in `Memory`), we carry a bag, are not retaining and are not `threatened`, then set `memory.banking = true` before `recall_to_bank`. The decision to ride is honoured, and `home_trip` still compares it with walking.
- **Expected effect.** 491 rides restarted (1,962 channel turns), plus some of the ~555 cancels. About 3-4 turns per capture recall.
- **Risks.** A champion that would rather chain a nearby group rides home instead. `capture_recall` already judged the ride better than walking to an altar.
- **Judge.** `ab.py`, keeping it if level. Watch the `PQQQB` pattern count.
- **Confidence:** high on the fix, small effect.

#### R1-9. Prism retains a bag only while its channel stays short (strategy change, test only)

- **Evidence.**
  - D1/D2. Prism loses 61% as many gems as it tributes; other champions lose 5-14%.
  - `retaining_gems` (bot.cpp:649) banks only a winning bag or at the game's close, so Prism's tributes are long. 311 of 363 tributes over 20 turns were Prism's, and 173 completed.
  - Non-winning tributes fail 1.1% at 1-5 turns and 32-35% at 11-50.
  - The other side of the trade is real: 46 gems are +69 Focus on a base of 80. So this is not a fix.
- **Change.** In `retaining_gems`, add `&& tribute_turns(my_gems()) <= params::tribute_window` (60 gems). Above that the bag is banked by the normal carry logic.
- **Expected effect.**
  - Fewer 100+ gem Prism bags lost, and short Prism tributes.
  - The median retained-bag death (46 gems) is unchanged: this cuts the tail, not the trade.
- **Risks.** Less Focus late. Prism also leaves farming to bank more often.
- **Judge.** `ab.py`, then a fresh suite. Watch Prism gems tributed and lost, and Prism damage.
- **Confidence:** low. Review 2 found that the opponents' Prisms carry bags the same way: mean bag 79 against 76, and median tribute 200 for both. That weakens the case. Test it only after R1-2 has removed the Prism freezes.

#### R1-10. A kill is worth at least the victim's maximum health (behaviour change, small)

- **Evidence.**
  - C2: 49 turns in 34 games, late, where a non-lethal nuke on a healthy enemy beat a sure kill.
    - c4fafdae-5 r934 and r950 left a Tavi at 48 health alive.
    - f974cb55-5 r1447 and r1449 left a recalling Ryth at 119/5000 alive.
  - `hit_worth` (plan.cpp:100, abilities.cpp:91) values a kill at `health + 300 + bag` but any other damage at its full amount, although a recall or the spawn heals it.
  - Constant `life_value` raises were level (EXPERIMENTS), but they do not scale with the late game, which is where this happens.
- **Change.** The kill's worth becomes `max(health + life_value, victim max health) + bag`, in both `hit_worth`s. The victim's max health has to be passed to plan.cpp's fighter.
- **Expected effect.** A few late kills. It also bears on 25 of C4's 35 focus misses.
- **Risks.** A changed valuation reaches the search, the cast choice and prey ordering. Rare per turn, so it is hard to measure.
- **Judge.** `ab.py`, judged as level-or-better.
- **Confidence:** low-medium.

#### R1-11. `tribute_safe` counts a ready stun that reaches us before the channel ends (mis-estimate)

- **Evidence.**
  - D4: 167 tributes cancelled by stuns. 55 of them had a visible stunner with a ready stun within 6 tiles at the start, and 37 champions died with the bag before banking.
  - 6d6e0961-3 r375 submitted a 2-turn tribute with a visible Ryth 3 tiles away, stun ready (`rr=375,375`), and was stunned at once.
  - `tribute_safe` (bot.cpp:375) checks only death.
- **Change.** For channels over 1 turn: unsafe if a visible, non-immune-to-us stunner has a stun slot ready within the window and `Safety::approach` brings it into that slot's reach within the window. Only where the stun is ready; no new fuel gate.
- **Risks.** Tributes are delayed near Ryths, which carry the most stuns. The cost of a stun is a turn plus damage, so the gain per case is small.
- **Judge.** `ab.py`. Watch stun-cancelled tributes and tribute delays.
- **Confidence:** low-medium.

### Where I disagree, or would not act

- **A2's stand-and-cast against C3's held casts.** The two analysts blame the same rule, the flat `escape_step_value` (bot.cpp:33) on retreat turns, in opposite directions. A2 says casting in place kills: 158 deaths, 2.95% against 1.31%. C3 says holding casts kills: 603 deaths, with a 9% base rate. Both are associations, and "a stun valued by the turn it denies" already lost (48.5%). The real fix is a search on retreat turns that knows whether the step escapes (strike phase 4a). I would not retune the constant.
- **B3's mechanism.** The analysts say a crew value exists only while the claimer is visible. In the code it is the reverse:
  - An unseen claimer with no fresh anchor gets `anchor_round = -1`, so `delay()` is 0 (bot.cpp:1873-1881) and it is assumed to have been working all along.
  - `health_left` then often drops to 0 or below, and the shared candidate is skipped (`continue`, about bot.cpp:2177).
  - So the shared pick vanishes when we lose sight of the claimer, because we assume it is about to finish the group.

  If it is pursued, the fix is to anchor an unseen claimer on its last seen position and round instead of delay 0. Crew changes have lost four times (EXPERIMENTS), and most loops are 10-19 turns, so I rank it below the list.
- **A3b, the step-guard fuel gate.** 0.16% death rate on skipped turns against 0.11-0.20% overall is not evidence of harm. It stays TODO #4's fuel work.
- **B5, B6, D3, D6.**
  - B5's lost captures are mostly correct retreats.
  - B6 (2.2k turns) would need farm to evaluate on standoff turns, which are the turns that already run out of fuel (D6.2).
  - D3's "retreat to the altar instead of spawn" helps only if the tribute can finish under pursuit, which it rarely can.
  - D6's opening and standoff out-of-fuel turns belong to TODO #1-2. One point for that work: in standoffs, a turn that ran out replays the same search with the same inputs and runs out again (b0a77e05-2: 7-turn streaks). The search's node cap should bound the worst case below the budget, rather than leave it to the next turn.

## Review 2

Working from the games down: how the 624 distinct games were won and lost, what the opponents do in the same situations, and which findings matter given that. Scripts and outputs are in the reviewer's scratchpad (`pergame.py`, `champs.py`, `activity.py`, `tribs.py`, `caps.py`), not committed. They read only the ladder extracts (both teams' positions, events and end-of-game stats), so their numbers cover whole games, not only trusted rounds. Spot-checks against the traces are named where they were made.

### How games are won and lost

- **Losses are farm races lost by round 600, not fights lost early.**
  - In the 268 losses, deaths are even until round 600: 2.83 of ours against 2.81 of theirs per game.
  - The score gap opens anyway: level at round 200 (53 against 54), then 129 against 162 at round 400 and 197 against 294 at round 600.
  - Over the whole game they out-capture us: 1,027 capture gems against 694, and 7,174 capture gold against 4,273. We have fewer capture gems in 218 of the 268 losses.
  - Net kill gems exceed the final margin in only 14 losses.
  - The gap is mostly Elk groups: from round 400, they take 233 Elk gems a game against our 143, and from round 800, 287 against 152. Monoliths add to it late (71 against 7).
- **The fight deficit comes after the economic one.** From round 600 to 1000 in losses, we die 2.87 times a game and they die 1.79 times. Gems lost on death are 101 against 47 a game. By then they are richer, with 72% more gold over the game, and their damage to champions is 29.8k in losses against 17.6k in our wins.
- **In wins the picture mirrors this.** We out-capture them, 1,016 against 587, and they die 3-4 times as often as we do throughout.
- **Our wasted time is concentrated in long freezes, not in ordinary idling.**
  - Idle rounds overall are equal: 15.3% of alive rounds for us, 15.2% for them (no move, attack or cast, not channelling, off spawn).
  - Idle runs of 50 rounds or more are three times theirs: 1.8% of alive rounds against 0.6%.
  - Our Prism spends 3.8% of its life in such runs, against 0.1% for the 85 enemy Prisms. Its idle share is 21% against their 12%, and it earns 227 gems per 1000 alive rounds against their 304.
  - Our dashers show the same, less strongly: Heart of Ruin 1.7% against 1.0%, Vesper 2.3% against 1.0%.
  - In the losses, the opponents' long-idle share is 0.1%.
- **Bag handling is at or better than the opponents' for every type but one.** Gems lost on death per gem tributed:

  | champion | us | them |
  |---|---|---|
  | Heart of Ruin | 0.08 | 0.20 |
  | Ryth | 0.05 | 0.18 |
  | Vesper | 0.13 | 0.19 |
  | Marcella | 0.12 | 0.12 |
  | Vendetta | 0.09 | 0.09 |

  Our non-Prism champions bank smaller bags more often (7.3-8.5 tributes a game, median 15-25 gems; theirs 3.8-5.6, median 22-30). The outlier is long tributes (R2-1).
- **The opponents' Prisms also keep their bags.**

  | Prism | us | them |
  |---|---|---|
  | mean bag while alive | 79 | 76 |
  | share of alive rounds carrying 50+ gems | 41% | 35% |
  | median tribute | 200 | 200 |
  | gems lost on death per game | 78 | 78 |

  `retaining_gems` is what top teams do, and I would not drop it on D1's evidence. Our Prism's shortfall is throughput (the freezes above, R2-2), not the retention.
- **Our deaths look like theirs.**

  | death | ours | theirs |
  |---|---|---|
  | walked 4+ tiles toward its own spawn in the 8 rounds before | 22% | 18% |
  | at 50%+ health 8 rounds earlier | 78% | 72% |
  | median distance from its own spawn | 15 | 17 |
  | carrying a bag | 31% | 31% |

  A chased retreat is how a lost fight ends for everyone. The opponents' bots do not escape it either, so I read A2 as fights lost, not a retreat rule to rewrite (see the disagreements below).
- **Gold.** The opponents take more gold per gem than we do: 7.2 gold per gem against our 6.2, across all games. In the first 400 rounds of losses they earn 30% more capture gold, and that gold compounds into stats. This is an open question, not a suggestion: gold weights have lost locally (EXPERIMENTS: 3x gold 46.9%, front-loaded gold 45.6-47.2%), and nothing in the analysis isolates a mechanism.

So the order of value is: stop the long freezes that cost farm tempo (R2-2, R2-3); stop handing over game-deciding bags on long channels, where the opponents behave differently (R2-1); then the small mechanical leaks (R2-4 to R2-7). Fight-model retuning comes last: deaths are even while the game is being decided.

### Suggestions, ranked by expected value

#### R2-1. A winning bag's tribute is taken "at any risk" only when the channel is short

- **Type:** decision-rule (behaviour) change.
- **Evidence:**
  - Code: `any_risk` (bot.cpp:656) makes `tribute_ok` (bot.cpp:660) true for any `winning_bag`, whatever the channel length. So `submit_here` starts the channel and `continue_tribute` (bot.cpp:3948) keeps it, beside visible enemies, for up to 249 turns.
  - Long winning-bag channels (11+ turns), ours against the opponents' in the same situation:

    | | starts | deaths | cancelled by their own choice | completed |
    |---|---|---|---|---|
    | us | 87 | 26 | 0 | 36 |
    | them | 191 | 5 | 48 | 67 |

    At 51+ turns: we have 33 starts and 16 deaths; they have 78 starts and 4 deaths. We started 11 of our 33 with an enemy within 4 tiles; they started 9 of their 78 that way.
  - All tribute deaths: 38 of ours (25,014 gems, 30 games) against 18 of theirs (4,924 gems).
  - The 26 winning-bag deaths fell in 19 games, 10 of them lost. They concentrate on 01boss_battle (7) and 00collision (2).
  - Spot-checked: ddbc8901-3 r1974-1976.
    - Our Vesper kept a 2,490-gem channel (`trib:196`, `keep=1 why=safe`) with an enemy Vesper and Heart of Ruin visible 3-4 tiles away, and died at r1976.
    - With 24 rounds left, that channel could never have finished: it was kept at any risk for no possible return.
- **Change:**
  - In `any_risk` (bot.cpp:656), make the winning-bag clause `winning_bag(world) && channel_turns <= params::tribute_window`. A winning bag with a longer channel then goes through `tribute_safe`, like any other bag: it starts only when no visible enemy could kill it within the window, and it is cancelled and re-tried (carry_bag's `W` wait) when one comes. This is what the opponents do (48 cancels).
  - Never start or keep a channel that cannot finish by round 2000. In `tribute_ok`, return false when `channel_turns > rounds_left(world)`, since a bag scores nothing at the round limit. This also covers the `rounds_left` clause of `any_risk`.
- **Expected effect:**
  - Most of the 26 deaths become cancels, with the bag kept, re-tried or carried.
  - Each saved death denies the enemy a bag of 450-2,500 gems. On 01boss_battle and 00collision that bag often decides the game.
  - Perhaps 3-5 of the 10 losses flip: +0.5-1 point on the ladder.
- **Risks and edge cases:**
  - Fewer completions where enemies always hover near the only altar (01boss_battle). There the bag may never find a safe window. The opponents complete 35% of their long winning channels and we complete 41%, so cancelling does not obviously cost completions.
  - A short winning tribute (6 turns or fewer) keeps the at-any-risk rule, so the endgame race is unchanged for normal bags.
  - Cassi/Issac bags use `bag_at_stake` elsewhere; check that `winning_bag` is still the right test for them.
- **How to judge:**
  - `py tools/ab.py` against the current bot. The local suites rarely make 1000-gem bags, so expect level overall and read the ladder slice (01boss_battle, 00collision).
  - Count tribute deaths and `tribute_cancel` events in the A/B replays.
  - Keep if level: it is the logical rule.
- **Confidence:** high that the change is right; low that a local A/B can show it.

#### R2-2. Prism's spell clear deadlocks on a nearly dead monster (B1)

- **Type:** bug fix.
- **Evidence:**
  - Code (verified):
    - `spell_clear` (bot.cpp:1547-1583) stands outside reach and calls `cast_at_camp(world, g, attackers_only=true)`.
    - With `attackers_only`, `post_basic` is false (abilities.cpp:398), so `sole_finish` is false.
    - The cast's value, `min(raw, health)`, then has to reach `min_camp_value = 50` (abilities.cpp:20, 471).
    - A member with under 50 health can never be cast at. The basic attack is out of range at distance 4, and `spell_clear` still returns true.
  - Spot-checked: 00f0c307-4. Prism c5 stands at 25,79 from r175 to at least r1100, at full health with 45 gems and 10 gold, `cd=0,0`, every turn `farm best=19 steps=4`, and no action but the routine recall.
  - The analysts count 84 runs in 56 games (20.6k turns). My comparison puts our Prism's 50+-round idle at 3.8% of its life, against 0.1% for the opponents' Prisms.
- **Change:**
  - In `camp_cast`, a candidate whose damage finishes its member (`raw * finish_factor >= m.health`) meets the floor, for unit and ground targets alike. `sole_finish` already does this for the last visible member; the cap `min(raw, health)` otherwise makes finishing a weak member impossible.
  - A narrower alternative: in `spell_clear`'s `hit()`, pass `any_value=true` when the group's live attackers' total health is under `min_camp_value`.
- **Expected effect:**
  - Frees much of the Prism's long-idle time: B1's 20.6k turns are close to all of its 50+-round idle.
  - The group clears and respawns, so captures resume, and the retained bag can reach `closing`/`winning_bag` tributes sooner.
  - Prism is in every one of our drafts.
- **Risks:** an 8-round cooldown spent on a few health points. Here the alternative is nothing, so the cost is nil; elsewhere the broad version might cast where a basic attack was coming. Prefer the narrow version if the A/B is unclear.
- **How to judge:**
  - An A/B against the current bot.
  - Watch the Prism's idle runs of 50+ rounds and its captures per game in the A/B replays. 01big_world reproduces the case: the same r176 opening in 9 games.
- **Confidence:** high.

#### R2-3. Dashers stall at hole lines: price the wake instead of banning the landing (B2)

- **Type:** mechanical fix (the path model and the move code disagree).
- **Evidence:**
  - Code: farm and bank fields count a dash over a crossable hole line (world.cpp:821). The only crossing, `dash_across` (self_abilities.cpp:294-310), drops every landing that `wakes_camp`. For Heart of Ruin, whose landing hits everything within 1, that is any landing next to a live sleeping harmful monster.
  - Spot-checked: 9fa0e422-2. Heart of Ruin c4 stands at 28,14 from r315 to the end of the trace. At r600 it has a different target (`farm best=35 steps=15`), so the stall is not tied to one group. The tiles across the row-15 hole line border group 12 (a Wolf and a gold cluster at 28-29,17: 4 gems, 20 Strength), not its target.
  - The wake the ban avoids is a Wolf, while the stall costs about 900 turns.
  - The analysts count 34.8k turns in 86 games, every 00great_wall and 01islands game. Our record there is 6-14 and 8-6.
- **Change:**
  - In `dash_across`, rank wake-free landings first as now. When none passes, accept a waking landing if the groups it wakes cannot trap us: our health is above their combined Strength × (`max_camp_reach` + 1) rounds, the bound `camp_trapped` already uses.
  - The landing also stuns the woken monsters, so their first attack is skipped.
- **Expected effect:** the 50+-turn dasher stalls on these maps end. 98 of the 210 episodes are banking (`B`), so tributes resume too.
- **Risks:**
  - Waking a strong group (Golem, Elk) next to us. The health bound refuses those for most of the game.
  - The Vesper variant (9fa0e422-2 c1, 18,18) is refused by another guard. It needs a level-2 trace first; leave it out of this change.
- **How to judge:** an A/B against the current bot. The generated suites have hole-line maps, so check the dashers' long-idle runs there. Keep if level.
- **Confidence:** medium. The direction is clear; the safety bound is a judgment.

#### R2-4. Take a sure kill on a retreat turn (C1)

- **Type:** mechanical fix.
- **Evidence:**
  - Code: `retreat()` (bot.cpp:4002-4022) never basic-attacks for a ranged champion unless a reset is ready, and it calls `dash_away` first.
  - For a melee champion it attacks only from the start tile. After `retreat_step`, an unspent attack is never used.
  - Spot-checked: 4a126b66-5 r585. Our Vesper (Strength 115, reset on cooldown, dash ready) had the enemy Vesper at distance 3 with 1/2100 health. It dashed away and stepped, with no attack. Another champion got the kill two rounds later.
  - The analysts count 119 strict turns (74 of those enemies alive 3 rounds later), and 287 by the looser bound.
- **Change:**
  - Before `dash_away` in `retreat()`, attack a visible enemy in range whose health plus shield is at most our basic damage × its `taken`, when we can still move afterwards: melee, or ranged with a ready dash.
  - For ranged without a dash, take the kill only when that enemy is the only one that can reach us next turn. This is the "free stun" logic in `enemy_cast` applied to a kill.
  - For melee, after the retreat step, use an unspent attack (`attack_enemy`). Walking and attacking are independent, so the hit is free.
- **Expected effect:** a few extra kills a hundred games: 100 gold, 60 dead rounds and the enemy's bag each. The lessons record says +1 net kill at round 300 moves the mirror's win rate from 56% to 85%.
- **Risks:** a ranged champion without a dash loses its step. The only-reacher condition bounds this.
- **How to judge:** an A/B against the current bot; count kills on `d=R` turns. Keep if level.
- **Confidence:** medium-high on correctness, small EV.

#### R2-5. Count a slot that comes ready between an enemy's two turns (A3a)

- **Type:** calculation fix.
- **Evidence:**
  - Code (verified): `Reach::build` (safety.cpp:1318) decides readiness once, at `turn_round`, and the `twice` reach (safety.cpp:1885) reuses it for the enemy's second turn. `threat_strike`'s `strike_memo` does the same.
  - The analysts count 203 deaths (144 games, 4,910 gems) where the killing slot came ready exactly in that gap. 196 of those killers were visible, and the cases are mostly Marcella one-casts.
- **Change:** when `twice`, read readiness at `turn_round + 1` for the strike. A slot ready at the first turn is ready at the second, so this only adds threats. It is the "slots readied for turn 2" narrowing that TODO's Candidates lists after w2-chain lost (47.1%).
- **Expected effect:** fewer `stand_ok`/`ls=-1` verdicts next to a Marcella whose nuke comes back next round. This is A5's largest visible-killer source.
- **Risks:** more retreats and lost farm turns, which is how w2-chain lost. This version adds no chain search and no fuel.
- **How to judge:** an A/B against the current bot, with fuel and out-of-fuel turns.
- **Confidence:** medium.

#### R2-6. A capture recall that lands the turn after payout is cancelled and restarted (B4a)

- **Type:** bug fix (stale state).
- **Evidence:**
  - Code (verified):
    - `decide` resets `memory.banking` while the bag is empty (bot.cpp:4109).
    - On the payout turn, `continue_recall`'s non-holding branch calls `recall_to_bank`, which returns at once on `!memory.banking` (bot.cpp:3151).
    - The recall is cancelled with 1 turn end left, and `carry_bag` then sets `banking`.
  - The analysts count 491 restarts (1,962 channel turns, 276 games), and about 555 more cases where a ride landing the next turn was abandoned.
- **Change:** where `capture_recall` keeps the recall because the share reaches an altar sooner by way of home (its last line, the non-Prism path), set `memory.banking = true`. That keep is already a banking decision. The flag survives the reset once the share is paid.
- **Expected effect:** about 4 channel turns saved per case, a few per game.
- **Risks:** none beyond the recall being kept one more turn when the rest of `recall_to_bank`'s test still holds.
- **How to judge:** an A/B, keep if level. Count `recall_cancel` events with `left=1` that follow a capture.
- **Confidence:** high, small EV.

#### R2-7. Shop and bank recalls must be able to land (B4b)

- **Type:** mechanical fix (consistency).
- **Evidence:**
  - Code (verified): the home keep requires `recall_outruns` (bot.cpp:3977). The shop and bank keeps (bot.cpp:3986-3989) check only the probabilistic `threatened()`.
  - The analysts count 61 deaths (1,477 gems) with a recall kept for shop or bank in the last 4 turns, and 258 keep-retreat-keep alternations.
- **Change:** keep a recall for `recall_to_bank` or `shop()` only if `recall_outruns(world, safety)` too.
- **Expected effect:** fewer standing turns while a pursuer closes in.
- **Risks:** fewer bank and shop rides when an enemy is far but fast. It is the same test the home keep already passes.
- **How to judge:** an A/B, keep if level.
- **Confidence:** medium-high, small EV.

### Where I disagree with the analysis, or would not act

- **D1 (Prism retention, ranked first by gems).** The opponents' Prisms keep bags of the same size and lose the same gems per game (table above). Dropping `retaining_gems` would copy no one and gives up the Focus. Fix the Prism's freezes (R2-2) and the tribute rule (R2-1) first.
- **A2 and C3 pull against each other.** A2 says casting while fleeing kills us (2.95% against 1.31%). C3 says not casting kills us (603 deaths with a ready nuke). Both are associations on the same flat `escape_step_value`, both are confounded by how close the enemy was, and the deaths look like the opponents' deaths. Past retunes lost: casting before walking 46.2%, a stun valued by the turn it denies 48.5%, and the retreat planner variants. I would not change the threshold without a model of whether the step escapes. If it is tried, price the walk as the damage it avoids (the difference in `damage_bound` between the start tile and the best step), not as a constant.
- **A3b (step guard skipped for fuel)** is an existing gate on TODO's list. The excess death rate is 0.16% against 0.11% (17 deaths), so it is not urgent.
- **D6 (out-of-fuel turns in rounds 1-4).** These are real, but they cost a first walk in 102 games: a turn or two of tempo. It belongs to TODO item 1 (the farm loop), not a new change.
- **B3 (crew flips).** Real, but EXPERIMENTS records three crew-seniority fixes that lost. Not without a new mechanism.
- **The ranking by gems handed over** overweights death findings. In losses, kill-gem differences exceed the final margin in only 14 of 268 games, while the capture deficit is about three times the kill-gem deficit.
