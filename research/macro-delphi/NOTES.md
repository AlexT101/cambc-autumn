# macro-delphi: macro refactor of charybdis (2026-11-11, orchestrator DELPHI)

Branch `macro-o4-20261111`, worktree `/home/ubuntu/wt/macro-o4`. Every A/B: `tools/ab.py variants/CAND
variants/charybdis-ref --no-test-draft --fuel 200000`, release builds, fast runner (native), own drafts.
Suites: `maps/macro-dev` (5,120 fresh ladder-v2 maps), subsets `maps/macro-dev512` / `maps/macro-dev1280` (its first
512 / 1,280 maps, symlinks) for quick reads; `maps/macro-holdout` (1,280) kept for confirmation. Helper:
`research/macro-delphi/ab.sh CAND NAME SUITES`. Implementation briefs: `briefs/`.

## Evidence 0: the charybdis mirror (variants/mirror = ref vs ref, debug, macro-dev512, 1,024 games = 512 distinct)

- 512 games, mean 821 rounds. Winner / loser per team-game: kills 6.9 / 2.1, deaths 2.2 / 6.8, dead 4.2% / 12.1% of
  turns, gems lost at death 69 / 273, captures 56.9 / 50.0, capture gems 1053 / 866.
- Time: walking ~50% (move_bag 26%, move 24%), camp 18-20%, hold 4-5%, recall 6%, tribute 1-4%, fight 2%.
  Walk segments after spawn/recall: ~20% of alive time.
- Prism in both drafts in 433/512 games (Prism in 455). Winner's Prism collects 782 gems (incl. kills), submits 592,
  4.8 kills, 0.2 deaths; loser's 513 / 69 / 1.0 kills / 1.6 deaths. Other champions collect 107-141 each.
- 816 Prism deaths: killed by the enemy Prism 78%; victim/killer-side Prism Focus < 0.5 in 63%, < 0.8 in 87%.
  First Prism death: victim's team loses 90.5% (284 games). Deaths peak r400-800. Victim's last decisions: retreat 'R'
  (~50%), stop-game-ender 'E' (~30%, desperation), farm 'F' (~10%).
- Focus race (Prism-both games): winner/loser Prism Focus median ratio 1.00 at r100, 1.06 r150, 1.09 r200, 1.14 r300,
  1.17 r400; the eventual winner is ahead 47% / 59% / 60% / 66% / 68%. The race is close early and decided by r300-400.

## Experiments

| Candidate | Idea | Games | Win % | Verdict |
|---|---|---|---|---|
| p-home05 | probe: home_power x0.5 (less own-side preference) | 2,560 (dev1280) | 51.4 (49.4-53.3) | level |
| p-life067 / p-life15 | probe: life_value x0.67 / x1.5 | 2,560 each | 49.5 / 50.2 | level |
| p-shop2 | probe: shop_gain_scale x2 (more shopping trips) | 10,240 | 48.4 (47.4-49.4) | loses |
| p-home0 / p-home2 | probe: home_power 0 / x2 | 10,240 each | 47.8 / 49.7 | 0 loses; x2 level (OOF 2.4x) |
| p-hurt16 / p-homeret16 | probe: hurt_retreat_ratio x1.6 / home_retreat_ratio x1.6 | 10,240 each | 50.1 / 50.1 | level |
| p-pshop3 / p-pshop033 | probe: the Prism's shop-trip gain x3 / x0.33 (wants_shop) | 10,240 each | 47.5 / 50.0 | more Prism trips lose 2.5; fewer level |
| p-shop05 | probe: shop_gain_scale x0.5 | 10,240 | 49.6 | level |
| hub (E2) | allies price the Prism's carry bonus on groups it can take over (q from hand-over paths) | 10,240 | 50.1 (49.1-51.1) | level; the bonus changed ~6% of ally picks |
| rally (E1) | engaged champions post a fight beacon; others within one cooldown's walk answer when the pack test says even or better; champion hits over camp hits near an engaged ally | 10,240 | 49.0 (48.0-50.0) | loses 1; answers ~100-250 turns a game, about half arrive in time |
| p-home05 (full) | probe: home_power x0.5 | 10,240 | 50.8 (49.9-51.8) | level |
| pairprice (E3) | a Cassi/Issac kill prices the partner's life too: target worth, chase cost, turn-order bids, our own stake | 10,240 | 49.8 (48.8-50.7) | level (OOF 447 vs 574) |
| pack (E5, interim build) | allies farm only within carry_reach of the Prism's work, walk to it when nothing qualifies | 10,240 | 38.7 (37.8-39.6) | loses 11 |
| pack-r24 | pack (idle walk) with radius 24 | 2,560 (dev1280) | 39.1 | loses |
| pack2-r1 / pack2-r2 | pack with no idle walk (unmasked fallback when nothing is in the pack), radius 12 / 24 | 2,560 each | 40.8 / 40.3 | loses |
| pack2-r10 | pack2, radius x10 (mask almost never binds): only the leave_for_prism relaxation (no dominance veto, 12-round wait) | 2,560 | 47.5 | relaxation costs ~2.5; the mask ~7 more |
| p-noleave | probe: allies never leave an unclaimed cleared group for the Prism ('near' leave off) | 2,560 | 49.3 | level |
| convoy (E6) | the Prism's candidates limited to groups within 12 of some ally's work (unmasked fallback) | 2,560 | 45.0 (43.1-47.0) | loses 5; the Prism already keeps ~4-5 tiles from its nearest ally |
| rally-prism | rally, but only the Prism answers fights | 2,560 | 49.3 | level |
| rally-guard | rally, but allies answer only fights their visible Prism is in (no posted beacons) | 2,560 | 49.7 | level |
| pack3 | pack2 with only the 2 strongest allies (max health x Strength) bound, no leave relaxation | 2,560 | 43.2 (41.3-45.1) | loses 7 |
| pack-early300 | pack3 code with every ally bound, only until round 300 (the Focus race and first kills) | 2,560 | 45.7 (43.8-47.7) | loses 4 |
| hub / pairprice / p-home05 on macro-dev2 | confirmation on a second fresh suite | 10,240 each | 50.2 / 50.0 / 49.8 | level (pooled with dev: 50.15 / 49.9 / 50.3 of 20,480) |
| endguard (E7) | escort the winning tribute on every map: guards hold the carrier's altar, carrier left out of guard ranking, lock veto by an unseen carrier | 2,560 / 10,240 (dev) | 49.4 / 49.4 (48.4-50.4) | level |
| combo | hub + pairprice | 10,240 (dev) | 49.2 (48.3-50.2) | level |
| window (E8) | a keeping Prism banks (bank floor) while every enemy Prism is dead and walk + channel fits before its respawn | 10,240 (dev) | 48.3 (47.3-49.3) | loses 1.7: the hoard's Focus outlives the window |
| hub on held-out suites | macro-holdout / ladder+gen+gen-s1 | 2,560 / 1,280 | 50.3 (48.3-52.2) / 49.0 (46.3-51.7) | level everywhere: 50.1 pooled over 24,320 |
| p-swing25 | probe: EOQ bag_swing 2 -> 2.5 (a carrier killed by the enemy Prism also feeds its Focus) | 10,240 | 50.0 (49.0-51.0) | level |
| yield (E10) | our Prism's work steps keep out of radius 5 of a visible enemy Prism with 2x its Focus; no chase start on it | 10,240 (dev) | 49.9 (48.9-50.8) | level; fires rarely (contact happens in retreat/strike branches it does not reach) |
| stunsafe (E11) | a winning or long tribute does not start while a visible enemy stun can reach us within the window | 10,240 (dev) | 50.0 (49.1-51.0) | level; ~never fires: tribute_safe's kill test already refuses then, so cancels happen mid-channel |
| contest1 (E12) | contest_capture before chase_with_guard in decide() (denial before chases) | 10,240 (dev) | 50.2 (49.3-51.2) | level |

Probes are diagnostic only (one knob, not for shipping): the tuned constants sit on a flat optimum in the mirror too.

More mirror evidence (dev512):
- First kill of the game: the killer's team wins 69% (median round 221); first victim a Prism: 98.6%.
- First team whose score + carried gems reach 1000 wins 87%; it takes a median 58 rounds (mean 147) to convert.
- Of capture gems on groups an ally (non-Prism) cleared, the Prism gets ~25% (140-150 of 530-640 a game).
- Prism unspent gold: mean 114 (r200-400), 280 (r400-800); other champions 18-32 (they spend promptly). 90% of
  Prism recalls are followed by a shop. Prism ends games with 380 gold unspent on average.
- Deaths by the victim's decision the round before: retreat 'R' 2,930, stop-ender 'E' 1,131 (85% in games already
  lost), farm 'F' 1,467.
- Deaths after a retreat ('R' the round before): the retreat began only 1-2 rounds before death in 40%, and from
  full health in 24%: one-shots by a stronger Prism's burst (stun 1.5x Focus + ground 1x Focus), not slow chases.
- `maps/macro-dev2`: 5,120 more fresh ladder-v2 maps (mapgen seeds 86000-86019), a second development suite.
- First kill of the game: victim Cassi 45% (200/447), Prism 15%; killer Prism 47%, Vesper 15%.
- Cassi & Issac are in 1018/1024 team-games and die 1.69 times a game (2 bodies x 60 rounds each, both bags, one
  kill) - the largest death sink (Prism 0.90, Vesper 0.58). 1,720 pair deaths: Issac's body 1,058, Cassi's 662;
  killers Prism 56%, Vesper 19%; victim at full health 5 rounds before in 68% (bursts, stun then follow-up);
  bodies 12+ apart in 31%.
- hub (interim build, before its audit): 50.2% of 10,240 (dev) - level.
- rally (interim build, before its audit): 49.3% of 10,240 (dev).
- Deaths to a Prism: the victim's team saw the killer 4 rounds before in 59% (victim itself 2,129 of 3,627), at
  distance 5-7 mostly, with the killer's burst (2.5x Focus) above the victim's health in 90%+; the victim's team's
  Prism was weaker (<0.8x) or dead in 74% of those.
- Kill values (plan.cc, abilities.h kill_distance) price a Cassi/Issac kill as one life plus both bags, though it
  removes two bodies for 60 rounds: an unpriced mechanic.
- Monolith maps: 117 of 512 (23%); in 70 nobody captured it; the first capturer won 37 of 47.
- Prism-on-Prism stun openers (mirror): when our two-turn burst (2.5x Focus + 2 basics) kills the target and its
  answer would not kill us, the opener kills 86-91% and dies 2%; both lethal: kills 59-67%, dies 16-24%; ours not
  lethal, theirs lethal with its stun ready: dies 78% (366 cases, but 278 are 'E' desperation in lost games).
- Prism contacts (both alive, in sight within 8, 20 quiet rounds before): at Focus ratio < 0.5 the weaker dies within
  15 rounds 36% (844 episodes); 0.8-1.25: 6% either way.

Note: /tmp hit its quota at 19:45 (other sessions); ab.sh now sets TMPDIR=replays/tmp.
- Focus saturation: 574 of 910 Prisms at some point carry more Focus than a two-turn burst (2.5x Focus) needs to kill
  the toughest enemy's max health, for ~325 rounds, ~190 gems beyond it on average; 74 such Prisms died carrying
  ~750 gems each (their team lost 58). A tribute scores the whole bag, so a surplus cannot be banked on its own.

## The pack result (20:20): cohesion wins fights, the idle walk-back loses the economy
pack (interim build) on its 100 kept games, pack vs ref a game: kills 7.66 vs 5.88, deaths 6.64 vs 8.11, kill share at
equal numbers 0.575, our Prism's kills 5.8 vs 3.1 and deaths 0.9 vs 1.7, Prism collected 660 vs 535 gems - and yet
captures 62.6 vs 74.3, ally collection 90 vs 119 a champion, tributed 536 vs 768: 38.7% of 10,240. The implementer's
traces: 300-1,150 ally-turns a game with no candidate inside the pack (idle by the Prism or walking back).
So the fight value of cohesion is large and real; the design must buy it without idle allies.
The box became heavily loaded at ~20:10 (load 160-200): a 10,240-game A/B now takes ~50 min, so screens use
macro-dev1280 (2,560 games) and only promising candidates get full runs. The final pack build's full run was
stopped at 1,094 games.
- Denial pool: per game (both teams) 14.5 captures (330 gems) had an opponent within 6 of the tiles during the hold,
  4.3 (126 gems) within 3; contested resets happen 0.5 times a game ('X' is 0.09% of turns).
- After reaching score + carried >= 1000, a team starts 4.2 tributes of 150+ gems on average before one completes
  (first one 18.6 rounds after the threshold).
- Correction to the pack read: per game, pack's kill difference is bimodal. Of 100 kept games, pack won 38 (33 with
  more kills) and lost 62 (42 with fewer kills, 13 level). Its higher mean kills come from blowout wins; in most
  losses it also lost the fights (the implementer saw collapses of 0 kills and 8-11 deaths). Cohesion is not a
  uniform fight edge.
- Game-ending tributes (499 games): the Prism's in 261. Median start bag 647 gems against 577 needed, a 47-turn
  channel (with the Tribute emblem), and 4.5 attempts of 150+ gems by that Prism before one completes. In one endguard
  smoke game a 1,245-1,598-gem bag (125+ turns) was cancelled 20 times before it landed.

## Conclusions (21:25)

**No candidate beat charybdis-ref.** Every behaviour change was level or lost; `bots/charybdis` is left equal to
`variants/charybdis-ref`. The 60% target was not reached.

What the evidence says about where the mirror is decided:
1. **The Prism duel snowballs.** Kills decide (winners 6.9 kills, 2.2 deaths a game; losers 2.1, 6.8). The first kill
   wins 69%, and the first Prism death loses 90%+ (98.6% when it is the game's first kill). The dominated Prism
   (Focus under half) dies within 15 rounds of contact 36% of the time. Duel openers win when their two-turn burst
   is lethal and the answer is not. The Focus race is even at r100 and decided by r300-400.
2. **The farm optimiser is strong, and every restriction of its choices loses, roughly in proportion to how much it
   binds.**
   - Allies bound to the Prism: -9 to -11.
   - Two escorts bound: -7.
   - Bound only to r300: -4.
   - The Prism bound near allies, which rarely binds: -5.
   - Longer leaves for the Prism: -2.5.
   - More Prism shop trips: -2.5.

   Soft prices that seldom change a pick (hub, pairprice) are level.
3. **Cohesion does not win fights for free.** pack's higher mean kills came from blowout wins. In most of its losses it
   lost the fights too. Reactive cohesion (rally, its Prism-only and guard-the-Prism forms) was level or -1.
4. **Tuned constants sit on flat optima in the mirror too.** Every one-knob probe landed at 47.5-51.4, and the
   significant ones were all losses.

Final state: `bots/charybdis` is unchanged (identical to `variants/charybdis-ref`, so 50.0% against it by
construction). The best-measured behaviour change, hub, is 50.1% over 24,320 games (dev, dev2, holdout and the
standard suites): not a gain, so it is not shipped. Each candidate's source diff against the reference is in
`patches/`, and the analysis scripts are in `tools/` (they read extract.mjs output, e.g.
`py tools/pdeath.py EXTRACT_DIR`).

Leads not taken (time):
- **The Prism's long final tribute:** median 47 turns, 4.5 attempts, sometimes 20 cancellations of a 1,500-gem bag.
  A tribute scores the whole bag and its length is fixed at the start. Ways to end a game with less channel exposure
  (allies' bags; banking in enemy-Prism death windows lost 1.7, variant `window`) look like the cleanest remaining
  inefficiency.
- **The denial pool:** 14.5 enemy captures a game (330 gems, both teams) with an opponent within 6 during the hold,
  but contests happen 0.5 times a game.
- **Snowball control:** what makes one side win the first fights at even Focus (turn-order seats, vision/bush first
  strikes) was measured only indirectly.
- Last-hit routing (E9, cancelled before testing): non-Prism kills are 4.6 a game (both teams, 92 gems), but only 0.33 a
  game have our Prism within 4 of the victim (23 gems). Leaving killing blows to the Prism has almost nothing to win.
