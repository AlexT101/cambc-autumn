# Top-10 ladder drafts (fetched 2026-11-03)

Ranked games since 2026-10-31 of the top 10 other teams (ours, "newer team", #3, left out), from `replays/ladder/*/group.json` (`fetch_replays.py --top 11 --since 2026-10-26 --kind ranked --max-groups 0 --no-replays`, 9,571 groups). Compositions as sets, the top three per pick count. Nobody drafts Stellar (2% at most); Intercontinental Fish and test4 draft Cassi & Issac in 99-100% of games, Mite in 49%.

### Mite (2135 games) — C&I 49%, Stellar 0%
  3p (393): HoR Vend Vesper 74%; HoR Marc Vend 21%; HoR Marc Ryth 3%
  4p (484): C&I HoR Marc Vend 65%; C&I HoR Vend Vesper 35%
  5p (1258): HoR Marc Tavi Vend Vesper 52%; C&I HoR Marc Vend Vesper 43%; HoR Marc Prism Tavi Vesper 3%

### Intercontinental Fish (2140 games) — C&I 99%, Stellar 0%
  3p (402): C&I Marc Vesper 53%; C&I HoR Vesper 37%; C&I HoR Marc 9%
  4p (469): C&I HoR Marc Vend 83%; C&I HoR Vend Vesper 10%; HoR Varg Vend Vesper 6%
  5p (1269): C&I HoR Marc Vend Willow 59%; C&I HoR Vend Vesper Willow 18%; C&I HoR Varg Vend Vesper 18%

### Univardisty of Shingtonwash (2145 games) — C&I 40%, Stellar 0%
  3p (360): HoR Marc Ryth 38%; HoR Marc Varg 22%; Marc Varg Vesper 6%
  4p (457): HoR Ryth Varg Vesper 19%; HoR Marc Ryth Vend 13%; HoR Marc Ryth Vesper 13%
  5p (1328): C&I HoR Ryth Varg Willow 24%; HoR Marc Ryth Varg Vend 17%; C&I HoR Ryth Tavi Varg 8%

### Ad Astra (2145 games) — C&I 39%, Stellar 0%
  3p (366): C&I HoR Vesper 46%; HoR Ryth Vesper 24%; C&I Marc Prism 12%
  4p (489): C&I HoR Marc Vesper 48%; HoR Marc Ryth Vesper 21%; C&I HoR Marc Prism 11%
  5p (1290): HoR Marc Ren Ryth Vesper 34%; HoR Marc Ren Vesper Willow 19%; C&I HoR Ren Vend Vesper 17%

### NEETCoders (2140 games) — C&I 33%, Stellar 0%
  3p (380): HoR Vend Vesper 63%; HoR Marc Vesper 28%; C&I Marc Prism 9%
  4p (430): HoR Marc Vend Willow 36%; HoR Marc Vend Vesper 20%; C&I Marc Prism Vend 13%
  5p (1330): HoR Marc Ryth Vend Vesper 48%; C&I Marc Prism Ryth Vend 14%; HoR Marc Ren Vend Vesper 13%

### test4 (2145 games) — C&I 100%, Stellar 0%
  3p (347): C&I Marc Vesper 86%; C&I HoR Marc 14%; Marc Ryth Vesper 1%
  4p (486): C&I HoR Marc Willow 92%; C&I HoR Marc Vesper 8%; C&I HoR Marc Vend 0%
  5p (1312): C&I HoR Marc Vesper Willow 92%; C&I HoR Marc Tavi Vesper 8%; C&I HoR Marc Vend Willow 0%

### Sponge(Albert and Bob) (2145 games) — C&I 0%, Stellar 2%
  3p (354): HoR Marc Vesper 62%; Marc Ryth Vend 21%; HoR Marc Ryth 7%
  4p (506): HoR Marc Ryth Vesper 63%; HoR Marc Ryth Willow 22%; HoR Prism Ryth Willow 9%
  5p (1285): HoR Marc Ryth Vend Vesper 66%; HoR Marc Ryth Vend Willow 22%; HoR Prism Ryth Vend Willow 6%

### print dont int (2145 games) — C&I 2%, Stellar 0%
  3p (369): HoR Marc Vesper 76%; HoR Marc Prism 15%; C&I HoR Marc 10%
  4p (485): HoR Marc Vend Willow 45%; HoR Marc Vend Vesper 45%; HoR Marc Prism Vend 11%
  5p (1291): HoR Marc Ryth Vend Vesper 48%; HoR Marc Ryth Vend Willow 46%; HoR Marc Prism Ryth Vend 6%

### T1 (2145 games) — C&I 0%, Stellar 0%
  3p (390): HoR Marc Vesper 58%; HoR Vend Vesper 35%; HoR Marc Ryth 7%
  4p (488): HoR Marc Ryth Vesper 82%; HoR Ryth Vend Vesper 7%; HoR Varg Vend Vesper 6%
  5p (1267): HoR Marc Ryth Vend Vesper 80%; HoR Marc Varg Vend Vesper 18%; HoR Marc Ryth Varg Vend 2%

### BattleCats (2140 games) — C&I 9%, Stellar 1%
  3p (388): HoR Marc Vend 38%; Marc Vend Vesper 15%; HoR Vend Vesper 9%
  4p (442): HoR Marc Vend Vesper 23%; HoR Marc Prism Vend 20%; HoR Marc Ryth Vend 17%
  5p (1310): HoR Marc Ryth Vend Vesper 24%; HoR Marc Prism Ryth Vend 16%; HoR Marc Prism Vend Vesper 13%

## Test-draft table (`params::test_draft`, 2026-11-03)

astraeus's `test_compositions` (`bots/astraeus/src/draft/draft.cc`), replacing the 2026-10-21 table in DRAFT.md. Same definition: these team-games (ranked, 2026-10-31 00:02 to 11-03 00:50Z, 3,283 groups, 21,425 team-games of the 10 teams above), the 10 most common compositions as sets per pick count, each in its most common pick order (the script was not kept: count `matches[].sides[].draft` of those teams in groups created since 10-31). `choose()` takes one per game by a hash of the map and side, uniformly: rare and common compositions are played equally. Count, share of that pick count, and how often that order was the one played:
- 3 picks (3749): Vesper Marc HoR 883 (23.6%, order 523); Vesper HoR Vend 723 (19.3%, order 289); Vesper Marc C&I 554 (14.8%, order 511); Vesper C&I HoR 322 (8.6%, order 173); HoR Vend Marc 246 (6.6%, order 97); Ryth Marc HoR 211 (5.6%, order 166); HoR Marc C&I 128 (3.4%, order 47); HoR Vesper Ryth 103 (2.7%, order 102); Marc Varg HoR 86 (2.3%, order 75); Prism Marc HoR 80 (2.1%, order 62).
- 4 picks (4736): HoR Vesper Ryth Marc 881 (18.6%, order 413); Marc Vend HoR C&I 705 (14.9%, order 703); HoR Marc Willow C&I 447 (9.4%, order 447); Vesper HoR Vend Marc 401 (8.5%, order 216); Willow HoR Vend Marc 389 (8.2%, order 217); Vesper C&I HoR Marc 277 (5.8%, order 125); Vesper Vend HoR C&I 249 (5.3%, order 216); Ryth Vend Marc HoR 160 (3.4%, order 85); Prism Marc HoR Vend 141 (3.0%, order 59); HoR Ryth Willow Marc 125 (2.6%, order 111).
- 5 picks (12940): Vesper Vend HoR Ryth Marc 3431 (26.5%, order 1019); HoR Marc Vesper C&I Willow 1201 (9.3%, order 1201); Willow HoR Vend Ryth Marc 899 (6.9%, order 596); Marc Vend HoR C&I Willow 754 (5.8%, order 751); Vesper Vend HoR Marc C&I 692 (5.3%, order 545); Vesper Vend HoR Tavi Marc 650 (5.0%, order 650); HoR Ren Vesper Ryth Marc 441 (3.4%, order 441); HoR Ren Vesper C&I Vend 430 (3.3%, order 217); Ryth Vend Marc Varg HoR 353 (2.7%, order 249); Vesper Vend HoR Varg Marc 352 (2.7%, order 222).
- The 10th 3-pick slot is a tie at 80: Prism Marc HoR kept, Prism C&I Marc left out. The ten cover 89% / 80% / 71% of 3 / 4 / 5-pick team-games.
