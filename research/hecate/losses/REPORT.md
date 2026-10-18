# Why nemesis loses ladder games (since 2026-10-17 13:00)

183 nemesis games, 122 won, 61 lost (download still running at the time; only Mite of the strong teams had
arrived, 10 games, we won 1; other losses to ~1820-1890 teams: Shawn, Boost, EMPEROR Tung, Let's LARP,
invisibleAgain, KratosMessi, meow). Games are replays/.analysis/<id>. Scripts in this folder.

In losses we capture 679 gems a game vs the winner's 1055. Kill gems (73 each) and bags lost (73 vs 83) are even:
the race is lost on farming speed; deaths hurt through time dead (11.9% vs 8.2% of champion-rounds, r1-300).
Three maps carry most of the gap: stampede (10 losses, 47% of the capture deficit), swirl (8, 23%), ambush (7,
slowest opening). Time use in losses r1-300 (us/them): dead 11.9/8.2, gem camps 14.7/15.8, gold camps 4.3/2.1,
walking 55.3/52.2, still 3.0/9.5.

## Failure modes, ranked
1. **Stampede: the shared 360-gem group goes to the enemy every respawn** (10 losses, 10,800 gems). Opponents send
   4-6 bodies by ~r53, capture ~r127-140 and after each respawn; our median first gem capture there r500 vs r150.
   siege_ready (big_rounds 50, siege_pool_share) doesn't pass early; farm() files the group as risky. We never
   deny their capture (12 of 44 with none of ours within 6 tiles in the 25 rounds before payout). Examples
   bad55339923d51cb (Let's LARP 0-1080, enemy first hit r53, capture r127 six ways, ours r373), 91c6bdd42eda1a6a
   (Mite), 5ead7f5074f35e19 r52-75. Fix: big-group siege from the opening, judging elk damage per body over 5-6
   attackers; when it is awake/losing health and not ours, arrive at the clear and stand on a capture tile.
2. **Starting camps one health bar can't finish, then recalling mid-clear.** Home from an unfinished elk/Monolith
   group 7.9 times per loss vs 2.75; clears of 80+ rounds 12% vs 5.4%; ambush first gem capture r167 vs r74.
   7e765f3899e3d60f r55-97 (three pairs on three elk groups, all recall r76-97 with nothing cleared; Shawn clears
   one with five, captures r78). Cause: affordable allows (hp - recall line)/camp_risk 0.35, ~2.9x the spare
   health; heal_rounds never added to a group's cycle. Fix: heal_rounds in every damaging group's cycle, camp_risk
   toward 1 as the walk from spawn grows, crews of 3+ on far elk groups.
3. **Walking into visible packs that strike first with spells.** In losses, 217 enemy-started fights killed 293 of
   ours vs 54 of theirs (~half our deaths): 165 victims walking, 119 had seen the attacker 6+ rounds earlier at
   6-8 tiles, 159 in our half, 105 outnumbered, 58 attackers in a bush, 37 never seen before the hit. Victims Varg
   78, Issac 41. Cause: pack_zone uses health x output() with spells spread over the cooldown (burst barely
   counts), ratio 100 away from home; lethal()/fight() only consider enemies in reach, so the step from 6 into
   reach is never checked. Examples 57a109e48e8733f2 swirl r372-387 (Tavi Focus 570 stun ~1250 one-shots Varg),
   contest vs Mite 8ba74237ac7f8bcd / 57b8a94954d7e85c (90 and 89 deaths vs 2, dead 55% of the game; Mite 20.6k gold
   vs 1.0k). Fix: pack zone from burst (Strike + 2 basic attacks), ratio ~1.2 in both halves; fight() on the
   destination tile of steps ending within reach+1 of a visible enemy; when a pack holds the centre farm outer
   camps and come back grouped.
4. **Starting outmatched fights with spells that also cost the walk.** 156 lethal fights we started with < 0.8x the
   enemy's health nearby: our deaths 147, theirs 81; 106 opened with Stellar area/Damage, Ryth area stun, Tavi stun.
   decide() casts first; keep_walk only when carrying. Examples 7d42502bddcf6313 r651, 75afcf7d8ca8199b r181. Fix:
   before the opening attack/cast require fight(here) not lost (not self_falls for Cassi/Issac) unless the hit
   kills or stops a tribute; otherwise cast only with keep_walk.
5. **200-round spell kites and idle crews.** 4cdf484edb7f33b4 swirl: lead 320-124 at r196, Stellar kites a 192-gem
   four-elk group r198-397, Cassi/Issac idle ~90 rounds; lost 908-1024 with 35 kills to 13. Cause:
   spell_clear_rounds makes 150+-round zero-damage plans; crews add allies with nothing to hit. Fix: cap kite
   plans ~40 rounds; don't crew a kite without a spell or safe target.
6. **Recalling home with the winning bag to shop.** 7e765f3899e3d60f r674-722 (team at 1058 incl. bags, Stellar
   recalls to buy two emblems, Shawn wins at r722); also 18e8e972f5e5656d r569, 66f4ac7af2de1516 r412,
   fda3700e274736fc r720. 4 of 61 losses ended with tributed + carried >= 1000. Cause: gems_short ignores allies'
   bags; the shop branch never checks closing(). Fix: skip shop branch and hurt bonus when closing().
7. **Chasing alone into the enemy half.** Chases ending only in our death 1.02 per loss vs 0.26 per win.
   75afcf7d8ca8199b r373-389. Fix: drop a target whose distance hasn't closed in 2 turns without a dash; stop after
   3 turns in their half or when a second enemy appears.
8. **Standoffs at the pack-zone edge.** A-B-A oscillations of 10+ rounds: 24 champion-rounds per loss (10 per win).
   18e8e972f5e5656d (Cassi r259-395), 075a8660699029b2 (Cassi r106-276).
9. **Pure farming races to Mite** (df99c5d3ec9cc544, 735919a938a10c7a, 61436a3ee232c537): we walk 63/61/55% vs
   56/54/50%, attack gem camps 20/20/26% vs 23/20/30%, bank smaller bags (32 vs 36-39). Levers: bigger chained bags
   when no threat is near; less early gold-only farming.

Checked, not significant: captures lost to walking off/contests (1.6 vs 4.5 a game), tribute cancels (~1 a game),
camp deaths (0.5 a game), kill-bag swaps (even).
