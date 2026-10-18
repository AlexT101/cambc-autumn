# Why we lose to the top ladder teams (2026-10-18)

Data: every v17 and v18 game against the top 10 on 2026-10-18, labelled by version from the platform (`fetch_replays.py` with the website cookie). v17 is nemesis 5ef5601 plus local spell-station farming and cleared-group pickup; v18 is hecate fddba49. 201 games analysed (32 against Intercontinental Fish).

| Rank | Team | v17 | v18 (hecate) |
|---|---|---|---|
| 1 | Intercontinental Fish | 4-16 (20%) | 2-18 (10%) |
| 2 | Mite | 5-15 (25%) | 7-8 (47%) |
| 3 | Nyxius | 10-10 (50%) | 6-9 (40%) |
| 4 | procless | 2-18 (10%) | 3-12 (20%) |
| 5 | new team(4) | 10-15 (40%) | 4-16 (20%) |
| 6 | Tartarus | 3-2 | — |
| 7 | Univardisty of Shingtonwash | 5-5 | 0-5 |
| 8 | Sneaky Bush Campers | 6-4 | 3-2 |
| 11 | hello | — | 7-8 |
| | Top 10 | 45-85 (35%) | 32-78 (29%) |
| | Everyone else | 138-52 (73%) | 94-26 (78%) |

Locally hecate and v17 are level (17-17 on the ladder maps), so the ladder gap between them is within noise.

## The game is lost between rounds 300 and 600

Against Fish, hecate leads on tributed gems until round 300 (+34 at rounds 201-300), then falls behind (−24 at 301-400, −128 after 600). Captured gems by round 300 are level (427 vs 441).

What Fish has built by then is gold. By round 300 it has earned 22% more (2277 vs 1866) and by round 400 33% more (3165 vs 2371). Its champions have 17% more Strength + Focus and 30% more max health. From there it wins fights: its champions in our half rise from 0.32 per round (rounds 1-100) to 0.73 (401-600), 77% of our deaths are in our own half, 58% of theirs are in ours, and while 2+ of them are in our half our camp-attack rate halves (0.20 → 0.11).

## Where the gold comes from

Gold earned by round 300, Fish minus hecate: gold clusters +217 (273 vs 56), wolves +99, elk +45, kills +50. By round 600: clusters +477, wolves +396, elk +148, kills +131.

- **Gold clusters.** Fish gives its weakest bodies (Cassi; Tavi and Prism when picked) gold clusters, which never hit back: Fish's Cassi tributes 13 gems in rounds 1-300 and spends its time on clusters; its Tavi buys shards on the spot. On stampede Fish took 25 of its own-half gold clusters to our 3, on contest 50 to 25. hecate takes the fewest of any of our bots (86 gold from clusters by round 300 against the top 10; v17 188, the opponents 203). Its farm value prices gold at `gold_worth × clear_share` (0.15), so two clusters (70 gold) are worth about 7 gems against 31 for a wolf.
- **Throughput in our own half.** Fish captures 23.3 own-half groups per game to our 17.1, with bigger crews on elk (3.2 champions to 2.0) and more camp damage overall (71k vs 57k). Banking: 59 gems per tribute to our 47, 1.6 captures per tribute to 1.2; we spend 7.3% of the time walking to altars to their 4.9%. Far own-half groups (corners, expanse, eight) go nearly untouched by us.
- **Ren.** Every top-10 team drafts Ren; we never do (6th in preference). Fish's Ren builds Focus (about 30 Power Focus shards plus Durability and Bruiser health) and makes 24 camp damage per alive round, 316 gems and 1423 gold a game with 0.47 deaths. Hitting it costs us ~930 reflected damage a game. Our `main_stat` would build it Strength (spells 1.25 × 10 < 5 × 5), ignoring that its stun and reflect scale with Focus.
- **Tavi** is our worst pick against them: 89 gems, 391 gold and 2.1 deaths a game (v18, all top 10).

## Fights

Bags lost matter less than expected: against Fish we lose about 41 gems a game in bags to their 26. Deaths matter through dead time (13% of our champion-rounds vs 8%), kill gold and lost farming.

- Fish converts damage into kills twice as well: 0.46 kills per 1000 champion damage vs our 0.20 (all top 10: 0.42 vs hecate's 0.24, v17's 0.33). Focus fire is the same on both sides (0.86-0.89 of a round's damage on the top target).
- Against Fish, a champion of ours below 30% health with an enemy within 5 dies 52-57% of the time (both versions); theirs 30%. Against the top 10 as a whole it is 38% on both sides, so this is Fish-specific. Most fatal windows last about 3 rounds and are spent walking home. Stuns don't explain it: both sides land about 20 a game and about 45% of deaths on both sides follow a stun within 4 rounds.
- We die alone more (3.5 vs 1.2 a game for hecate), but 39% of our deaths had 2+ allies within 5: with their stat lead they win even fights.

## Why local testing misses it

Our local opponents are our own bots: they draft Cassi/Varg/Stellar, leave gold clusters, and build no Focus Ren. Two changes aimed at the gaps above lost locally against hecate (gold ×3: 46.9%; Fish's draft with Focus Ren: 42.3%; see EXPERIMENTS.md). These ideas need ladder evidence, or a local sparring bot that plays like Fish (Ren first, gold-cluster farmers, big elk crews), before they are judged.
