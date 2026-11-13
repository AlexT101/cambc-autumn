## Which early lead predicts the winner (share of games where W led on it, ties excluded; n = games with a non-tie)
| lead in | r100 | r200 | r300 | r400 |
|---|---|---|---|---|
| wealth | 57% [54, 59] n=1987 | 62% [60, 64] n=2395 | 68% [66, 70] n=2461 | 72% [71, 74] n=2433 |
| cap | 56% [54, 59] n=1952 | 61% [59, 63] n=2374 | 66% [64, 68] n=2449 | 68% [66, 70] n=2421 |
| trib | 53% [50, 56] n=987 | 54% [52, 56] n=1875 | 57% [55, 59] n=2264 | 61% [59, 63] n=2335 |
| earned | 56% [54, 58] n=2149 | 60% [58, 62] n=2479 | 65% [63, 67] n=2516 | 68% [66, 70] n=2483 |
| campdmg | 54% [52, 56] n=2486 | 56% [54, 58] n=2546 | 63% [61, 64] n=2542 | 65% [63, 67] n=2493 |
| kills | 63% [58, 67] n=435 | 64% [60, 67] n=905 | 69% [66, 71] n=1198 | 74% [71, 76] n=1370 |
| deaths_neg | 61% [57, 66] n=502 | 63% [60, 66] n=998 | 68% [65, 71] n=1295 | 73% [70, 75] n=1476 |
| prism_bag | - | 63% [60, 65] n=2070 | 66% [64, 68] n=2146 | 69% [67, 71] n=2114 |
| prism_foc | - | 62% [60, 65] n=2096 | 66% [64, 67] n=2166 | 68% [67, 70] n=2127 |

## Win rate by collected-gem lead (from either side's view)
r200: lead<=-100: 22% (n=472), -99..-25: 39% (n=984), -24..24: 50% (n=2208), 25..99: 61% (n=984), 100..199: 76% (n=319), 200+: 84% (n=153)
r300: lead<=-100: 14% (n=796), -99..-25: 36% (n=970), -24..24: 50% (n=1570), 25..99: 64% (n=970), 100..199: 80% (n=408), 200+: 92% (n=388)
r400: lead<=-100: 11% (n=1078), -99..-25: 37% (n=820), -24..24: 50% (n=1196), 25..99: 63% (n=820), 100..199: 79% (n=438), 200+: 95% (n=640)
r600: lead<=-100: 10% (n=1116), -99..-25: 34% (n=488), -24..24: 50% (n=616), 25..99: 66% (n=488), 100..199: 78% (n=305), 200+: 94% (n=811)

## Prism deaths against the break
Prism games 2227; L Prism died 58%. First L Prism death minus b0: median +19, IQR +1..+183; before b0 10%, within 0..10 after 36%, 11..100 after 20%, 100+ after 34%
Bags lost to champions per game, whole game: L Prism 206, W Prism 17, L others 75, W others 22. Share of the kill-gem gap from Prism bags: 0.78
r300: Prism bag / team collected gems W 0.57, L 0.49
r400: Prism bag / team collected gems W 0.57, L 0.47

## Games where the first kill came late
first kill after r300: n=1134 (44%); W ahead at r300 58%, lead median +8, IQR -15..+46
first kill after r500: n=585 (23%); W ahead at r500 63%, lead median +18, IQR -11..+69

## Bank wins and r2000 games
bank wins 204: L carried at end mean 486 (Prism share 273 at r600), end round median 693
r2000 games 98: W Prism tribute cancels per game 27.2; team A wins 45%; presets [('ladder', 38), ('mut', 27), ('classic', 10), ('shared-gems', 6), ('monolith', 5), ('small-brawl', 3)]
W Prism tribute outcomes per game, games ending on 1000 gems (n=2158): cancel:stun 1.94, cancel:manual 1.41, done 1.07, cancel:lock 0.95, open 0.09, cancel:death 0.00
  completed sizes: median 547, IQR 355-734; final tribute that ended the game was the Prism's in 56%

## Side asymmetry by end type and symmetry
end: 1000 48.3% [46.3, 50.2] n=2462, r2000 44.9% [35.7, 55.1] n=98
sym: rotational 48.8% [46.4, 51.2] n=1483, vertical 50.2% [45.8, 54.6] n=480, horizontal 44.9% [40.9, 48.6] n=597

## Cleared clusters left unheld: rounds in state "cleared, unclaimed" per capture, by class
wolf: idle-cleared rounds per capture 2.3; untouched-up rounds per capture 156
wolf_cl: idle-cleared rounds per capture 1.8; untouched-up rounds per capture 86
elk: idle-cleared rounds per capture 1.9; untouched-up rounds per capture 65
golem: idle-cleared rounds per capture 2.1; untouched-up rounds per capture 134
gem_cl: idle-cleared rounds per capture 4.8; untouched-up rounds per capture 33
gold_cl: idle-cleared rounds per capture 9.8; untouched-up rounds per capture 79
mixed_cl: idle-cleared rounds per capture 2.7; untouched-up rounds per capture 22
monolith: idle-cleared rounds per capture 2.0; untouched-up rounds per capture 1245
