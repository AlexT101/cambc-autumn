# Top-team behaviours (2026-10-18)

909 distinct ladder games since 2026-10-16 08:00 with the top-5 teams, Sneaky Bush Campers (SBC) or Univardisty
(Univ), incl. 100 of ours against them. Nemesis era (since 10-17 13:00): only 10 games, all vs Mite (won 9):
replays/mine/20261017-130622-Mite-vs-PTN-Hyperion-1cd3404a, replays/mine/20261017-154011-Mite-vs-PTN-Hyperion-6c90138d.
The scripts and out/*.txt tables behind it are in git history, deleted in the 2026-10-19 research cleanup.

## Ranked behaviours
1. **Contest-like maps: lock every altar, hold the centre as a pack, win the tiebreak.** Mite locks both central
   altars early (r77/r100 in 6c90138d/5-contest, r78/r197 in 1cd3404a/3-contest), parks 5-6 champions between them
   (~(21-26, 21-27)), farms central gold clusters, never touches the Monoliths. Both games 0-0 at r2000, nemesis
   lost on gold and kills: died 90 and 89 times vs Mite's 2 (one at a time into the held centre after respawns).
   Rival likewise (103 deaths, 20261016-230029-Mite-vs-PTN-Hyperion-fe4abf76/2-contest). Mite locked every altar
   in 89 games (won 71), Univ 61 (median ~r200). Value very high.
2. **Stampede: commit 4-5 bodies to the shared block, then lock both altars.** 6c90138d/4-stampede: 5 Mite bodies
   at the 360-gem block (55,20) by r60, nemesis only Cassi nearby; cleared r116, 3x120 at r123, home, locks both
   altars (r161, r163), tributes; repeats r257. 1080-0 both nemesis games. Shared-group captures/game: Mite 2.68,
   SBC 2.69, Univ 2.17, us 0 (7 games). Value very high.
3. **Focus builds on every spell user, burst from range 4.** Fish: Power Focus on 83% of Stellar's shards, 80%
   of Ren's, 81% of Tavi's; our Ren and Tavi build Strength (median Focus 100 at r300 vs Fish 230/170). Mite routes
   gold to carries (Stellar 785 lifetime gold at r450, Ren 330). Mite Stellar hits 840 (Damage) and 588 (AoE)
   from 4 (fe4abf76/5-elkring r411-420). 73-83% of fights are opened from range 4 by every team; kills follow in
   29% (Fish), 31% (Mite), 17% (us); vs supported targets 28-31% vs 12%. Value high.
4. **Cast every damage or stun spell on cooldown, at camps from distance 4.** Casts per 100 alive
   champion-rounds: Fish 5.9, Univ 4.9, us 3.2. Camp damage from 4+: Fish 28%, Univ 29%, us 8% (Stellar 51-57%
   vs 22%; Monoliths Fish 69%, Mite 100%, us 0%). Stuns on camps 48-50/game (Fish, Univ) vs 13 for us. A lone
   Fish Stellar takes a Monolith from range over 316 rounds (20261016-090004-...-9f3b7948/5-contest r1407).
   Value high, cheap.
5. **Wards only in bushes, at distance 2** (100% for every top team; none on bushless maps; Mite re-wards altar
   and approach bushes every round on contest). 26-35% of top-team kills are on victims who had not seen the
   killer in the previous 3 rounds, vs 19% of ours. Value medium.
6. **Hunt hurt farmers in the enemy half.** After r60 top teams spend 9-16% of champion-rounds in the enemy half,
   we 3-4%. Kills/game: Fish 8.1, Mite 7.2, Univ 7.2, us 2.5. 96% of nemesis-era deaths to Mite were in our half,
   often camp-hurt (hp 0.37-0.65 at first hit). Value high if fight checks are good.
7. **Steal camps nemesis leaves idle** (6c90138d/1-packs: Mite took our $$GG group 4 times, 192 gems).
   Enemy-side captures 8-16% of top-team captures, 5% of ours. Value medium-high.
8. **Altar bushes: tribute from them, ambush carriers from them.** Tributes from a bush where possible: 54-74% top
   teams, 31% us. 17-29% of top-team kills within 2 of an altar; Fish's kills of 30+ bags: 208/281 heading to an
   altar or home. Example 35d06d77/5-eight r297-311. Value medium.
9. **Lock-snipe big enemy tributes** (~2% of locks cancel a tribute, ~150 gems each). Value medium-low.
10. **Cancel your own tribute when enemies close in** (Mite 1.36/game, bag 161; us 0.18). Low-medium.
11. **Recall more, and recall to shop** (27-34 completed recalls/game vs our 22). Low-medium.
12. Not worth copying: multi-phase clears (we already do as often), respawn denial and capture contests (rare),
    openings (ours fastest: 237 gems by r150 vs 168-220), team structure in general.

## Nemesis vs Mite by map
contest 0-0 x2 lost tiebreak (1); stampede 0-1080 x2 (2); packs 728-1008 (192 gems stolen); rows 924-1012 (farm
race); rushbait_v2 798-1016, 930-1008 (Mite's 4th wolf r47 vs ours r71); corners 962-1066 (14 deaths vs 6);
eight 1112-766 (our only win).
