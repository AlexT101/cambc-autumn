# Behaviour gaps by champion type: ocean against Fish and the top teams (ocean, 2026-11-07)

The Willow method ([willow.md](willow.md)) applied to every type: a census of how each type plays for us and for
Intercontinental Fish, Mite and the other top teams, then arms for the biggest gaps.

## Data

- **Ladder replays, decoded with `tools/replay/extract.mjs`**: 18,599 distinct games in
  `/home/ubuntu/tmp-offload/gaps/analysis/`.
  - 11-05, from that day's archive zips on big-arm (engine 3.0.0): every game of Fish (4,190) and Mite (3,915), and
    500 random games of each of the other 17 teams rated 2290+ (us excluded). Not filtered by champion, so the
    Willow-comp bias of willow.md's set is gone.
  - capture.db, 2026-11-06 21:00 to 11-07 14:39: all 9,498 games with a replay. In this window **every game of ours
    was played by v82** (live from 20:40, no other submission since; the scrims logged in
    `research/ladder-scrims-2026-11-06/data/games.jsonl` are all v82). 7,381 of them are ours: 340 ranked, the rest
    unranked (other teams' scrims against us, mostly Mite and caterpillow, and our Fish/Mite scrims). Identical replays
    (deterministic repeats) are counted once.
- **Sides** (one row per game, team and body): ours (v82) 4,466; Fish 3,450; Mite 4,328; top 17,654. Fish's 11-05 and
  11-06/07 games agree on every gap below to within noise (`bin/check.py`), so they are pooled. Our 11-05 games
  (proteus) are left out.
- **Pick rates** (share of sides): ours Cassi & Issac 95%, Prism 75, Vesper 61, Heart of Ruin 47, Willow 46,
  Marcella 41, Vendetta 25, Ren 19. Fish: C&I 99, HoR 93, Vendetta 83, Marcella 62, Willow 57, Vesper 46, Prism 3.
  Mite: C&I 96, HoR 94, Vendetta 89, Vesper 79, Marcella 51, Tavi 36. So Prism, Ren, Ryth, Tavi, Stellar and Varg have
  too few Fish or Mite sides to compare (Prism: 114 Fish and 85 Mite sides).
- Scripts in `/home/ubuntu/tmp-offload/gaps/bin/`: `select1105.py`, `remote_pull.py` (run on big-arm, streams the
  selected zip entries), `stage.py`, `features.py` (per game, side, body and phase), `report.py` (tables, logistic
  fits, ranking), `check.py` (by era and pick count). Full tables: `rep.txt`, `rep-rank.txt`.

**Measures**, per body and phase (rounds ≤250, 251-700, 701+), over its alive rounds. Distances are Chebyshev.
- `n4` allies alive within 4; `dnear` nearest ally; `dcent` the other allies' centroid; `dcarry` the ally with the
  biggest bag (10+ gems); `iscarry` share of rounds it holds the team's biggest bag (10+).
- `bag` carried gems; `bag_per_trib` gems a tribute; tributes and completed recalls per 100 alive rounds.
- Casts per 100 alive rounds by slot and target (enemy champion, camp); deaths and damage per 100 rounds of the phase.
- `capshare` its share of the team's capture gems; `front` its advance between the spawns minus the team's most
  advanced body (0 is the front).
- **Gap** d = (ours − Fish) / pooled SD. **Association** z: a logistic fit of the win on the standardised measure,
  the tributed lead at the phase's start and the rating gap, signed so that z > 0 means moving our value toward
  Fish's goes with winning. `z ours` fits our games, `z pool` Fish, Mite and top together. These are associations,
  not effects: they are confounded by game state and comp beyond the lead (e.g. farming volume rises with winning).

## Findings

The biggest gaps, one row per type and measure at the phase where the gap is largest (Willow omitted; it is
willow.md's and is already fixed). The rate unit is per 100 alive rounds.

| type | phase | measure | ours | Fish | Mite | top | d | z ours | z pool |
|---|---|---|---|---|---|---|---|---|---|
| Vendetta | 251-700 | dash casts | 11.3 | 7.3 | 9.3 | 7.8 | +2.84 | −3.7 | +2.3 |
| Vesper Vale | ≤250 | dash casts | 9.5 | 6.5 | 9.5 | 7.5 | +2.04 | +2.0 | +0.6 |
| Ren | ≤250 | dash casts | 9.5 | 7.2 | – | 8.1 | +2.09 | +1.8 | +4.4 |
| Issac | 251-700 | dash casts | 9.3 | 7.0 | 9.2 | 7.4 | +1.69 | +3.9 | +6.6 |
| Vendetta | ≤250 | allies within 4 | 1.02 | 1.92 | 1.48 | 1.23 | −1.67 | −1.5 | +0.2 |
| Heart of Ruin | ≤250 | allies within 4 | 1.10 | 2.10 | 1.54 | 1.36 | −1.62 | −1.1 | +4.6 |
| Vesper Vale | 251-700 | is the carry | 0.12 | 0.45 | 0.28 | 0.26 | −1.48 | −3.8 | +8.7 |
| Cassi | 251-700 | stuns on camps | 1.22 | 3.75 | 1.37 | 2.53 | −1.37 | +0.1 | +6.5 |
| Issac | ≤250 | allies within 4 | 1.33 | 2.15 | 1.64 | 1.75 | −1.24 | −0.4 | +4.5 |
| Vendetta | ≤250 | recalls | 1.79 | 1.06 | 1.26 | 1.07 | +1.16 | −2.0 | −10.7 |
| Marcella | 251-700 | is the carry | 0.08 | 0.25 | 0.28 | 0.24 | −1.11 | −4.3 | −3.9 |
| Marcella | 251-700 | damage spell on camps | 2.01 | 3.26 | 2.57 | 3.07 | −1.04 | +2.0 | +8.1 |
| Vesper Vale | 251-700 | recalls | 1.94 | 1.23 | 1.23 | 1.25 | +1.04 | −5.9 | −14.8 |
| Marcella | ≤250 | capture share | 0.26 | 0.45 | 0.37 | 0.36 | −1.00 | −2.4 | −1.0 |
| Heart of Ruin | ≤250 | nearest ally | 6.5 | 3.5 | 4.8 | 5.3 | +0.99 | +0.2 | +1.8 |
| Cassi | ≤250 | allies within 4 | 1.46 | 2.17 | 1.65 | 1.80 | −0.96 | −0.4 | +4.1 |
| Vendetta | ≤250 | gems a tribute | 18.5 | 38.5 | 30.5 | 26.1 | −0.72 | +2.9 | +2.2 |
| Vesper Vale | ≤250 | gems a tribute | 25.9 | 50.4 | 43.5 | 33.0 | −0.72 | +0.8 | +4.3 |
| Marcella | 251-700 | gems a tribute | 35.1 | 54.9 | 53.0 | 46.5 | −0.52 | +4.0 | +12.5 |
| Heart of Ruin | 251-700 | damage from camps | 573 | 881 | 674 | 606 | −0.57 | +0.9 | +14.1 |

They group into five behaviours.

**1. We dash about 40% more often.** Vendetta, Vesper Vale, Issac and Ren dash 9.3-11.3 times per 100 alive rounds
(the cooldown allows 12.5; ours 9.2-11.6 over the phases); Fish 6.2-7.6, the top teams 7.3-8.2. Mite dashes as often as we do. Within every pick
count and in both of Fish's eras (`check.py`). Heart of Ruin's dash (it lands with a stun) differs less: 10.9 against
9.3. Fewer dashes go with winning for Issac and Vesper in our games (z +2 to +5) and in the pool; for Vendetta the
signs disagree (ours −1.2 to −3.7, pool +1.5 to +2.3). ocean dashes to travel whenever no enemy is within 10 tiles
(`Pathing::travel_dash`), so most of the excess is likely travel.

**2. We spread out early.** At rounds ≤250 Fish's Heart of Ruin, Vendetta, Cassi and Issac have about 2 allies
within 4 (1.9-2.2); ours 1.0-1.5, top 1.2-1.8. The nearest ally: Heart of Ruin 6.5 against 3.5, Vendetta 6.6 against
4.5. Fish's Heart of Ruin takes 50% more camp damage (881 against 573 per 100 rounds, 251-700): it tanks for the
pack. The gap narrows after round 250 and is gone for Marcella and Prism. In the pool, more allies within 4 early
goes with winning (z +4.1 to +4.6 for Heart of Ruin, Issac and Cassi); in our games it does not (−0.4 to −1.5).

**3. We bank small bags often.** Gems a tribute, ours against Fish's: Vendetta 18.5 / 38.5, Vesper 25.9 / 50.4,
Marcella 27.6 / 37.2 (≤250) and 35.1 / 54.9 (251-700), Heart of Ruin 24.1 / 32.3, Cassi 20 / 28, Issac 18.5 / 24.8.
Mite and top lie between. We make ~60% more completed recalls (Vendetta 1.79 / 1.06, Vesper 1.96 / 1.24 per 100
alive rounds). Fish's Vesper Vale is the team's carry 40-45% of rounds (ours 12-14%), its Marcella 21-30% (ours
8-12%). Bigger tributes go with winning in both fits (z ours +0.8 to +5.2, pool +2 to +18); more trips go with
winning too, which is farming volume, not a recommendation.

**4. Our Cassi rarely stuns camps.** Fish's Cassi casts its stun on a camp 3.2-4.7 times per 100 alive rounds,
ours 1.1-1.6 (top 2.2-3.3, Mite as ours). Its damage spell on camps and its stuns on champions are level with ours.
ocean prices a camp stun at the monster's Strength (20 for a wolf) under a cast floor of 40, so a wolf is never
stunned and an Elk only when the damage spell is on cooldown. Pool z +3.6 to +6.5; ours 0.

**5. Our Marcella holds less.** Its share of the team's capture gems is 0.22-0.26 against Fish's 0.39-0.45 (top
0.31-0.36), its damage spell hits camps 2.0 times per 100 rounds against 3.3, and it kills half as often (0.37 against
0.79 per 100 rounds, 251-700). Fish lets Marcella take captures and tribute (2 gold a gem).

Smaller or untestable: our Prism takes 250-420 camp damage per 100 rounds where Fish's and Mite's take ~0, and recalls
1.1 times per 100 rounds against 0.1-0.4, but on 114 Fish and 85 Mite sides. Deaths are level early and higher late for us
(Cassi & Issac 0.26 against 0.18, Marcella 0.15 against 0.07 per 100 rounds after 700). Fish kills more with every
type (Vendetta 0.51 against 0.21, 251-700), a combat difference with no single knob.

**Willow sanity check.** v82's Willow takes 13.7% of the team's capture gems at ≤250 and 11.7% at 251-700
(Fish 2.9% and 3.1%), with 1.55 allies within 4 early against Fish's 2.43: the gap willow.md found, before oc-base16's
fix reached the ladder.

## Arms

(see below)
