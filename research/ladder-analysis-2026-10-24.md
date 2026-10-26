# Ladder analysis, 2026-10-24: astraeus ("willow best girl") vs Fish, Mite, Claudus, Trzy, wonk

Source: 2565 ranked games from 2026-10-24 involving at least one of Intercontinental Fish (IF), Mite, Claudus Maximus (CM),
Trzy Kwaterki (TK) and policy wonk (PW), downloaded into `replay-bulk/2026-10-24/` and narrated with
`py tools/replay/narrate.py replay-bulk/2026-10-24` into `replays/.narrative/` (2388 distinct games; 355 of ours).
Three analysts (map control, combat, economy/vision) worked from the narratives; their scripts are in the session
scratchpad (`analysis-A/B/C`). Most of our games predate CHANGES 133 (it seems to go live ~15h UTC); about 5 use CHANGES 134's draft.

Head to head: CM 58-43, IF 37-55, Mite 35-29, TK 37-28, PW 23-10.

## Big picture

- We already fight best: top-vs-top K-D 1.79 (IF 1.41, others 0.55-0.95), first hit in 69% of fights, fewest blind
  first hits taken (3.3/game vs 4.5-8.1), die in 8% of fight exits (others 12-19%).
- We lose the economy against IF and Mite: gold spent per 100 rounds 545 vs 709 (IF), 514 vs 627 (Mite) with level
  captured gems. Lost games collapse late (after r900 K-D 59-136 vs IF) with about half the damage per hit of won
  games, so the fight losses look downstream of gold, not tactics.
- Monoliths decide many CM/IF games and we barely take them.

## Ranked ideas to test

| # | Idea | Evidence (one line) | Where | Prior tests |
|---|------|---------------------|-------|-------------|
| 1 | Solo multi-visit Monolith chip on mixed maps (Vesper with Jungle), mid-late | Monolith maps: we capture one in 17% of games, CM 55%, IF 53%; head to head CM first in 23/40 (we won 6), IF first in 20/34; CM deals 5.8k a visit, 68% solo, median first visit r627 | `farm()` skips Monoliths (bot.cpp ~2173/~2216); `siege_ready` limit 0 on mixed maps | team sieges lost (39.6-48.3%); eris's Monolith bursts (EXPERIMENTS "eris") won 54.4% on Monolith maps, 56.6% fresh, but were not ported and their commits are gone; solo multi-visit untested |
| 2 | Finish a visible low-hp Monolith with no enemy in reach | CM leaves Monoliths at ≤30% for ~50 rounds between visits; CM returned first in 128 of 144 such windows | `siege_candidate` | untested |
| 3 | Prism builds Treasure first | 0 of 327 Prism builds own Treasure; Prism earns 25% of our base capture gold at x0.95; team bonus x1.153 vs IF/CM 1.21; ~+230 gold/game | `best_emblem` `gem_focus` branch, bot.cpp ~1294 | untested (CHANGES 101 left Prism unchanged) |
| 4 | Price Marcella's +2 gold per tributed gem in farm value / capture holder | Found by two analysts: TK/PW bank 42-48% of tributes through Marcella, we bank 25-31%; `marcella_tribute_gold_per_gem` is never read | like `prism_capture_holder` | farm worth now counts it (CHANGES 136, 140, after this data); capture-holder choice still unpriced |
| 5 | Kill-progress pricing of non-lethal hits | We hit the lowest-hp enemy in range 64-65% of the time (others 78-91%); hit a 60%+ enemy while a ≤30% one is in range on 16.1% of turns (others 1.2-8.9%); we kill 19% of enemies we bring below 25% (IF 27%, CM 31%) | plan.cpp `hit_worth` → `useful_damage` (world.h:598) values chip at full damage; price ~γ·d + (life+bag)·d/h, γ≈0.3-0.5 | "Fish's targeting" level on hecate (before the strike search) |
| 6 | Stop leaving nearly cleared groups for the enemy | Enemy finishes 2.8 of our damaged groups a game (others 0.7-1.3), 0.79/game left at ≤25% hp (others 0.20-0.34); 26% of the time we left for another camp (others 11-12%) | trace first; which decision leaves them | untested |
| 7 | Value follow-up on a stunned target; let the stunner act first | Allies hit our stun targets 28% (PW 41%); target dies in the window 6.0% (IF 9.0%) | plan.cpp hit value on `turn_lost`; turn_order.cpp | "stun valued by the turn it denies" 48.5% priced the stun, not the follow-up |
| 8 | Heart of Ruin running out of fuel in fights (ladder build) | 718 out-of-fuel fight turns, 336 right after a dash landing; IF/CM/PW have 0; worst on 01elk_arena (eb94e8da-5) | check whether CHANGES 131/132 fixed it with tools/replay/harness | — |
| 9 | Ward the altar's adjacent bush before a 5+ turn channel | Our ward covers the altar before 150+ gem tributes 27% of the time, IF/CM 58-62%; 01corridors 2b9fdd62-5: Prism with a winning 850-gem bag blind-hit from bush B17, tributed anyway, Mite locked and killed it. But warded tributes are not cancelled less overall (7.2% vs 6.2%) | `submit_here` / `ward_bushes` | — |
| 10 | No chases into an awake camp's reach | 25% of our fight damage is from camps (others 10-17%); 3f5701c7-3 00contest F70 lost two champions chasing Issac into a Monolith | bot.cpp ~3225 `prey()`/`chase_trade` | "camp damage in fight sim" lost 47.7%; chase-only untested |
| 11 | Willow does not open fights alone (5-pick maps) | As first hitter K-D 41-38, dies 10%; dies in 18% of fight exits (others 5-11%) | — | — |
| 12 | Defend/take mid and own-half gold-only groups | ~500 of IF's 782 extra base gold is mid groups; IF/Mite steal 20-21% of our-half gold groups, we take 7-8% of theirs | farm pricing | gold valued 3x lost 46.9% |

Lower: Vesper Power Strength over Bruiser Strength (CM 93%, Mite 85%, IF 76% Power by r800, ours 62%; "Fish builds" lost 3);
one Durability emblem for HoR/Marcella (26% vs 75-80%; prior Health/Durability level or lost); Marcella Focus build
(PW 60% Focus shards; prior Focus builds -4); enemy-race deadline for Prism's bag (we carry 27-30% unbanked at r700 vs 12-19%,
37% of losses end with ≥150 carried vs 6-10%; already tested level 51.1%); fewer lone gem-cluster bank trips
(8.6 clusters/game vs 3.7-5.8, mostly fixed by CHANGES 133: small-bag walk 17.1 → 13.5 steps).

## Anomaly to check first (not an A/B)

20 of our games (4 whole matches: 55575c56, 0aeb9255, 8b4c3289, 091481a3, 2026-10-23 23:30 to 10-24 04:40) drafted
Willow + Varg, Tavi, Stellar, Ren, Cassi/Issac and went 4-16. None of our usual picks appear, so it is not a random
fill after a missed pick; the draft fuel looks normal. Either a test build was live, or the draft has a failure mode.
Resolved 2026-10-25: an experiment batch (a Willow-first test build), not a draft failure.

## Not gaps (data says leave alone)

- Openings: map-matched we match or beat everyone on gems by r150 and r600; more spread out but no cost.
- Steals deep in our half: balanced (CM takes 30/game, we take 33); raw STEAL counts are inflated by equidistant groups.
- Altar choice (all teams 50-58% own, 31-38% mid), recall timing and hp (all alike), recall completion 98%.
- Engaging outnumbered (K-D positive even at -2), chases (we land most), third-party camp fights (best K-D both ways).
- Big-bag deaths: 0.53/game vs 0.43-0.70; Prism with 100+ gems goes K-D 233-49.
- Wards: we ward least (1.8 per champion per 100 rounds, 100% in bushes) and still see best. Nobody always wards near
  altars: CM wards every cooldown (7.2) but only 8% in bushes; TK 100% bushes; IF 73%, Mite 58%, PW 54%.
- Bush ambushes/lurks: lurks pay off 1-3% for every team. IF's blind first hits on us: 83 IF kills vs 44 ours.
- Teleports: Trzy/wonk 5.7, IF 4.2, Mite 3.0, CM 0, us 0.04; no loss signal (we win 58% when the opponent teleports 3+).
- Locks: ours (4.3/game) cancel a tribute 3% of the time vs Mite's 1.5/game at 37%; prior lock tests suggest a small ceiling.

## Other facts

- Opponent drafts are fixed per pick count: CM HoR/Marcella/Tavi/Vendetta/Vesper; IF Cassi-Issac/HoR/Ryth/Vendetta/Vesper;
  Mite Marcella/Ryth/Tavi/Vendetta/Vesper; TK HoR/Marcella/Ryth/Vendetta/Vesper; PW HoR/Marcella/Tavi/Vesper/Willow.
- Our records by pick count: 5-pick 57% of 230; 4-pick 51% of 69 (5/21 vs IF); 3-pick 45% of 56 (2/10 vs TK; now replaced by CHANGES 134).
- Build orders: top teams take one emblem per passive family (Treasure, Jungle, then Durability/Monster/Power) before
  Bruiser spam; ours go Treasure > Jungle > Bruiser > Bruiser, Prism Monster Focus > Bruiser Focus.
- Recall feints every turn: us (by design, `start_recall`), Mite, TK; not IF, CM, PW.
- One-round kills from 50%+ hp: PW 38% of its kills, TK 17%, us 16%, Mite 15%, IF 10%, CM 7%; our Prism is one-shot most (79).
