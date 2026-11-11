# Gem price against gold, and the race the enemy is running (gemprice, 2026-11-11)

Brief: the user's leads on wheel ("our gem value func is miscalculated and we are going for gold even though enemy is
about to gem victory"; "does it consider enemy state"; crystals; min_bank from map features). Base:
`variants/chy18-cm2k3` (charybdis chy-draft18 plus the comms port). Results:
[EXPERIMENTS.md](../../EXPERIMENTS.md) "Gem price and the race (charybdis)".

## How charybdis prices gems against gold now

- Farm values a group at gems + `per_gold` x gold (+ Marcella's tribute gold, + the Prism's `carried_bonus` on gems,
  itself priced at `per_gold`). `per_gold` (shop.cc `prices`) = `gold_price_scale` x `gems_share` x (the next
  emblem's rounds saved per gold), x the mid-game hump (1.25 while the higher tributed score is 100-500, to 1 by 700).
- `gems_share` (camps.cc) = min(gems short of the win, the enemy's gems short of the win, our tributed rate x rounds
  left) / living allies. So the enemy's state enters as a gem count, never as its pace or time to win.
- Charybdis puts the team's gems on the Prism, which keeps them until its bag wins or the game closes. `closing`,
  `race_left` and `bag_rounds_left` read only our own race; the comeback cook (enemy >= 400 tributed and 150 ahead)
  and the one-site altar guard (600 and 200) read tributed scores only. Nothing reads carried bags as standing.
- `min_bank` is gone in charybdis: the EOQ bank floor (CHANGES 508) sets it in play from the walk to an altar, our
  income and a carrier-death hazard learnt online, which is the "calculated somehow" the user asked for. The
  draft-time version (CHANGES 461) lost live; not repeated.

## Wheel against the Mite body (charybdis)

Mechanism suite (`tools/mksuite.py`, `tools/mech.sh`): wheel at 24 body noise seeds and 13 other weak ladder maps at
8, both sides, both bodies, 200k, 512 games a bot; read by `tools/mech.py`, `tools/ends.py`, `tools/cook.py`.

- chy18-cm2k3 wins 31% (15/48) of wheel against Mt3q, 92% against Flp4. Locally the Mite body never uses a crystal on
  wheel (0.0 a game), so the local loss is not the crystal hops live Mite makes.
- It is a lost race in standing (tributed + carried), not a hoard misread: when Mite reaches 600, our standing is
  ~370 in losses against ~640 in wins. We are out-captured in the ring: before either side reaches 600, we take 22
  gem-cluster captures a game in losses against Mite's 46 (wins 38 against 50); outside groups are level. We spend
  18% of champion-rounds in the ring against Mite's 30%, and 17% dead against 10%. Same draft every game (ours Ryth,
  Vesper, C&I, Prism, Willow against Vesper, Vendetta, HoR, C&I, Tavi): C&I die 7 times a game.
- The user's observation holds late: after the leader passes 600, half our captures are outside groups (wolf/elk with
  gold clusters) against a third of Mite's, while its pace says the game ends in ~400 rounds.
- The hoard is visible at the end: in 11 of the first 30 of the 33 losses our bags hold 300+ gems when Mite wins
  (mean standing 527 at the end).
- The score-only comeback cook fires in 64% of our wins against Mt3q (216 rounds a game; 69% of those rounds we are
  level or ahead counting bags), 93% of wheel wins. On standings it would fire in 15% of wins and still in 97% of
  losses.

## Arms (copies of chy18-cm2k3; diffs in [patches/](patches/))

| arm | change | rule it rests on |
|---|---|---|
| `gp-stand` | comeback cook and altar guard read standings (tributed + carried, ours as seen or posted, theirs as last seen) | carried gems score once tributed; a hoarding Prism keeps our score low while the race is level |
| `gp-horizon` | `gems_share`'s horizon ends at the enemy's win at its standing pace; the rest as now | gold pays only through gems farmed before the game ends |
| `gp-race` | `gems_share` in standings throughout: gems still needed = 1000 - our standing, at our standing pace, until the round limit or the enemy's win at its standing pace; the mid-game hump on the higher standing | the same, and the hoard is neither gems still to farm nor a slow pace |

`gp-horizon` is the user's lead in its plainest form; it differs from ocean's `bm-pace` (level) by taking the enemy's
bags and pace in standing and by repricing charybdis's carried bonus. `gp-race` also stops charybdis's hoard from
reading as a slow pace, which raised `per_gold` mid-game while we hoard (the tributed rate under-reads it) and lowers
it late when the enemy runs ahead.

Not built: crystal hops (the local Mite body makes none on wheel, so a local test cannot show what live Mite gains from
them, and `bm-tp` lost on fresh maps; a hop priced by its saving against crystal and channel is the remaining form),
a draft-time `min_bank` (see above).

## Results

Fresh-map gate (`tools/fgate.py`, `--fuel 200000 --screen --ci 0`, pool batches from 0, unmetered Flp4 / Mt3q,
REF runs shared with the allypos gates). Units are maps: 0.5 + CAND's mean minus REF's over the four paired games.

Results against chy18-cm2k3 (200k fuel):

| arm | win% (95% CI) | maps (games) | Fish | Mite | OOF turns a game (REF 0.046-0.047) | verdict |
|---|---|---|---|---|---|---|
| gp-race | 50.20% (49.99-50.42) | 40,960 (327,680) | +0.08 ±0.29 | +0.33 ±0.32 | 0.048 | ZONE (low H1 +6.68, high H0 -8.52) |
| gp-stand | 49.87% (49.64-50.10) | 20,480 (163,840) | +0.27 ±0.29 | -0.53 ±0.35 | 0.047 | no gain (high H0 -13.83; low LLR -0.08); closed |
| gp-horizon | 49.70% (49.43-49.98) | 20,480 (163,840) | -0.47 ±0.36 | -0.13 ±0.41 | 0.048 | loses (CI below 50, low LLR -2.20); closed |

Ladder side read: gp-race +0.28 ±1.00 (2,048 maps), gp-stand +0.41 ±0.99, gp-horizon -0.27 ±1.23. No failed games,
no early losses.

Mechanism (badmaps suite, 200k; n = 48 wheel games a body, 208 other a body: win rates here are noise-sized):

| bot | wheel vs Mt3q | other vs Mt3q | wheel vs Flp4 | late captures a game (wheel/Mt3q) | late outside-gold groups | Prism gems lost on death (wheel/Mt3q) |
|---|---|---|---|---|---|---|
| chy18-cm2k3 | 31.2% | 74.0% | 91.7% | 28.0 | 9.4 | 129 |
| gp-race | 35.4% | 79.3% | 85.4% | 17.0 | 4.3 | 197 |
| gp-stand | 33.3% | 72.6% | 93.8% | 27.3 | 9.8 | 158 |
| gp-horizon | 29.2% | 77.9% | 85.4% | 23.2 | 5.6 | 200 |

("Late": our captures while the enemy's score is 600+; "outside-gold groups": gold-only groups or gold over 10x gems. Crystal uses:
0.0 a game for every bot and for the Mite body on wheel.)

- gp-race does what the user asked for: once the enemy's pace says the game is ending, gold stops paying and late
  captures of outside gold groups fall by half on wheel. It does not fix wheel: wheel is lost earlier, in the ring,
  before either side reaches 600. Its fresh-map gain is +0.2, a zone.
- gp-stand turns the cook off in games we win, as designed (15% of wins on standings against 64% on scores), and loses
  half a point against the Mite body: the cook's mirror pull and denial were paying while we hoard, so the score gap was
  not a misread that cost games.
- gp-horizon (the enemy clock alone, on our tributed rate) makes gold too cheap all game for a hoarding team: our
  tributed rate under-reads our pace while the enemy's standing pace is read in full.

## Recommendation

- gp-race is the one candidate: +0.20 ±0.22 at 200k over 40,960 fresh maps, ZONE, no fuel cost. It is a principled
  repair (charybdis's hoard misprices gold through the tributed rate) rather than a wheel fix. A 100k read needs maps
  no gate has played (grow seeds clear of 2417384-2417583); it was not run because the 200k result is a zone, not a
  reviewed gain.
- Wheel stays unfixed. What the local data point at is the ring fight (time in the ring, deaths, gem-cluster captures
  before 600), i.e. the draft matchup and team fighting, not the gem price. Crystal hops can only be judged live: the
  local Mite body never hops on wheel.

## Files

- `tools/`: `mksuite.py` (suite), `mech.sh` (play + extract), `mech.py`, `ends.py`, `cook.py` (reads), `p1.sh`,
  `p2.sh` (gate chains). Extracts in `~/tmp-offload/gemprice/ext/`, logs in `~/tmp-offload/gemprice/logs/`.
- Gate logs: `~/tmp-offload/diverse/gate-logs/fgate-gp-*--chy18-cm2k3p4q-fuel200000-b0-batch.json`.
- Mechanism suite seeds: noise 1310000 + 880001..880128 (salt 880001..880128). Gates used pool batches 0-15 (shared,
  REF cached); no maps were grown.
