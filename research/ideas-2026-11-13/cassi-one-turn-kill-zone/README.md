# Cassi's one-turn kill zone against Fish r8's Vesper (2026-11-13): she dies in a chase she is already running; leaving earlier changes nothing

Base and REF: `variants/chy-525` (= bots/charybdis 525). Arms in `bots/variants/cassi-one-turn-kill-zone*` (gitignored;
diffs in `patches/`).

## The idea

Fish r8's fed Vesper two-shots Cassi from late in the game. Ranged, with attack reset and dash, she strikes from up
to 5 tiles (dash 2, range 3) and walks as fast as Cassi. Cassi's farm is small, so the idea was to keep the linked
pair out of that reach plus Vesper's approach, before the run starts. The stand would read the pursuers whenever a
seen enemy can kill the weaker body in one turn, and the guard would keep the pair's steps out of that zone.

## What the live data says

Scripts: `deaths2.py`, `onset.py`, `window.py`. The data is 161 live r8 games: 157 with our C&I, 132 of them against
Fish's Vesper.

- **A counting fix.** A pair death logs two death events. The one with `linked` is the body that died through the
  link. Counting the body actually hit, her 130 late (r300+) pair kills split as follows:
  - Cassi: 72 (0.55 a game against her);
  - Issac: 58 (0.44).

  The ideation's "Cassi in 129 of 129" read the first event of each pair.
- **Cassi's 72 deaths:**
  - Four rounds before, Vesper was within 6 in 59 of them and within 8 in 70.
  - In 62, two of her basics killed Cassi from full health: median Strength 545 against Cassi's 665 maximum.
  - Cassi was first hit in the death round or the one before in 41.
  - She saw Vesper continuously for a median 7 rounds before dying. The first of those sightings was at a median
    6.5 tiles: walls and bushes keep Vesper hidden until she is already that close.
  - In the last 6 rounds she walked toward Vesper 164 times and away 125.
  - She dealt no champion damage in 38 of 72, and had 1-3 allies within 4 in 54.
- **Issac's 58 are fights:** his health falls from 0.78 to 0.25 of maximum over the last three rounds, with Cassi
  about 9 tiles away.
- **Recall events are no signal.** Cassi starts a recall in 90% of her late turns (a start-cancel pattern), so a
  recall start does not mark a retreat.

## The body reproduces it

Base chy-525 against fr8-g25 at 200k, pool-v4 batch 0 parts p6-p7, 1,280 games (`prof.sh`, `deaths_local.py`):
- Late deaths to Vesper, per C&I game with her: Cassi 0.279, Issac 0.237. That is about half of live.
- Same shape:
  - Cassi was first hit in the death round or the one before in 164 of 283 deaths.
  - She dealt no champion damage in the last 6 rounds in 204.

## Arms

| arm | change |
|---|---|
| `cassi-one-turn-kill-zone` (czk-a) | `stand_lost_at`: a linked body loses the own-ground exemption from pursuit while a seen enemy's whole-kit one-turn strike (`strike_with`, both slots ready) covers its health plus shield. The stand then reads walkers out to reach + `pursuit_steps` (7 for a dash-ready Vesper). |
| `cassi-one-turn-kill-zone-w` (czk-w) | czk-a, and the work guard (`keep_out`) also keeps the linked body off neighbouring tiles where `stand_lost_at` holds, pursuers included, while such an enemy is seen |

**Death profile** (1,280 games each against fr8-g25 at 200k, the same maps; `profstats.py`):

| bot | Cassi deaths to Vesper, a C&I game | Issac's | out-of-fuel turns | win |
|---|---|---|---|---|
| chy-525 | 0.251 | 0.211 | 82 | 74.0% |
| czk-a | 0.251 | 0.191 | 78 | 74.7% |
| czk-w | 0.245 | 0.198 | 303 | 74.8% |

Neither arm moves the mechanism. czk-w also costs 3.7x the out-of-fuel turns at 200k, so it was not gated.

**Results against chy-525** (fgate `--pool v4 --fish-body fr8-g25 --mite-body mf-f9 --fuel 200000`, batches 0-3; `logs/`):

| arm | fuel | read | win% (95% CI) | maps | games | outcome |
|---|---|---|---|---|---|---|
| czk-a | 200k | fresh (decides) | 49.87 (49.64-50.10) | 10,240 | 81,920 | NARROWED, level |
| czk-a | 200k | fresh, Fish | 49.70 (49.38-50.01) | 10,240 | 40,960 | |
| czk-a | 200k | fresh, Mite | 50.04 (49.70-50.38) | 10,240 | 40,960 | |
| czk-a | 200k | ladder (side read) | 50.93 (49.84-52.01) | 512 | 4,096 | |

- About 600 of 10,752 games a batch differ.
- The high SPRT reached H0 at batch 1 (LLR −13.4 by batch 4). The low SPRT stayed at −0.12: a 49.87 read sits midway
  between its hypotheses and would not decide over the whole pool.
- The upper bound (50.10) cannot pass the 50.5 bar. No 100k run: there was no 200k gain.

## Why: the trace (`variants/czk-trace`, debug, the same 1,280 games; `patches/czk-trace.diff`, `trace_read.py`, `steps.py`)

- **She is already leaving.** On Cassi's last turn alive she was retreating in 181 of 283 deaths. The pack zone sent
  (or the recall line) sent her in 128 of all deaths (drawn_home), a lost stand in about 54. She was farming in 65 and banking in 20. Two turns before:
  retreat 162, farm 81.
- **The guard already works.** Her steps with Vesper in sight, against Vesper's strike reach (5 with dash ready, 4
  with reset ready, else 3):
  - retreat steps: 325 ended out of reach, 191 stayed in it;
  - steps into reach, in every branch: 25.

  Vesper closes on her own turn, and one step cannot get out of a reach of 4-5.
- **A chase on foot.** Vesper walks as fast as Cassi. Each dash gains her 2 tiles, and each reset lands a basic from
  4. Both come back every 8 turns. In the open a two-shot Cassi who steps away each turn survives the chase, so the
  deaths come from:
  - one-shots: Vesper's Strength was at least Cassi's health in 94 of 283 cases three rounds before;
  - a first hit already taken, or damage from others;
  - blocked steps (unseen units);
  - retreat routes home that bend toward Vesper.
- **The stun cannot reach.** Cassi's stun has range 4, and the chasing Vesper sits at 5. With the stun ready, Vesper
  was within 4 and seen at the start of Cassi's last turn in only 13 of 283 (`stunready.py`).
- **Geometry.** Against a two-shot, stepping away each turn, Vesper's two-turn kill reach equals her one-turn strike
  reach (5), which `step_guard` already prices. Only a one-shot adds a tile. czk-a's pursuit adds walkers out to 7,
  but the retreat it starts leads into the same chase.

## Cassi's late value (`contrib.py`, base profile)

From r300 Cassi makes, a C&I game:

| | Cassi | share of ours |
|---|---|---|
| stuns on enemy champions | 3.6 | 42% (the Prism has the other 42%) |
| champion damage | | 7% |
| capture gems | | 9% |

The idea's premise that her absence costs almost nothing leaves out her fight role. A hard-avoidance arm (Cassi held
out of every fight with a killer in it) would give up half our late stuns. It belongs to the avoidance family that
lost before (mitere mvf −3.66, fr8x-pgf −2.64, prismlife dis3/dis5 −3 to −5), and was not built.

## Verdict

Nothing ships.
- czk-a is level at 200k (49.87, CI 49.64-50.10; Fish 49.70) and leaves Cassi's deaths to Vesper unchanged.
- czk-w changes them by −2% (noise) for 3.7x the out-of-fuel turns.

The mechanism the idea named does not hold: the pair already leaves, and Cassi dies in the chase that follows.

**Don't retry:**
- leaving Vesper's zone earlier;
- guarding the pair's steps against pursuers;
- Cassi's stun against a chasing Vesper;
- Cassi out of fights while a killer is seen.

A revival needs a way through the chase itself. The open levers are an earlier sight of her (she is first seen at
6.5 tiles, already inside her approach) and retreat routes away from her rather than home through her (prismlife's
pl-flee was level for the Prism).

## Files

- `tools/`:
  - live: `deaths.py` (the first pass, before the counting fix), `deaths2.py`, `onset.py`, `window.py`;
  - local: `deaths_local.py`, `profstats.py`, `trace_read.py`, `steps.py`, `stunready.py`, `contrib.py`;
  - runs: `gate.sh`, `prof.sh`, `profd.sh`.

  Working data is in `~/tmp-offload/cassizone/`.
- `patches/`: `czk-a.diff` (against chy-525), `czk-w-over-a.diff`, `czk-trace.diff` (CZS/CZW trace lines).
- `logs/`: the czk-a fgate log.
