# Opponent classifier: {Fish, Mite, other} from pick order and enemy priorities (2026-11-09)

A posterior over which team we face, kept by each of our champion instances from what it sees. It's in
`bots/variants/ocean-opp` (a copy of ocean-16d6f78) as `src/model/opp_class.{h,cc}`, `opp_token.h` and
`opp_tables.h`, with copies of those files here. It changes no behaviour: at 100M fuel, bench.py replays
are identical (52/52). It costs +280 fuel a turn on average (+0.56%).

## Interface (`namespace aph::opp`)

- `const Posterior& posterior(const World&)`: `{fish, mite, other}`, summing to 1, cheap to call.
- `const Evidence& evidence(const World&)`: counts of priority reads matching Fish's encoding, Mite's,
  neither, or zero, and the first round each team's encoding was seen.
- `observe(const World&)`: the last line of `World::update()`, once a turn.
- Hook: `#include "opp_class.h"` in model/world.cc, `opp::observe(*this);` at the end of `World::update`, and
  `#include "model/opp_class.cc"` in unity.cpp after model/world.cc.
- State: about 100 bytes of static memory per instance. Draft memory and shared memory are not used.
  Allies can disagree early, since each instance has seen different enemies.

## Model

1. **Prior**: Fish 0.25, Mite 0.25, other 0.5.
2. **Pick order given the champion** (the user's suggestion): for each enemy pick, log P(slot | champion,
   pick count, class). Which champions get picked is not used. Champion ids run in pick order, so this is read
   in play at round 1.
   - Tables are fitted on 11-08 and later games, with Dirichlet smoothing (2 pseudo-games spread over the slots).
   - "Other" averages its teams with equal weight.
3. **Priorities**: an enemy's current priority, read at our turn start while it is visible. A read counts
   when its value differs from the last one this instance read for that enemy. Each counted read becomes one
   token, the most specific test that matches:

   | token | test |
   |---|---|
   | fish_quiet | (-v) mod (N+1) = Fish's rank (2 + place by base health; HoR before Varg), and L = (-v - rank)/(N+1) is the health band (or band+5), within one band |
   | fish_contact | the same residue, with L in 99..116 or -117..-101 |
   | mite_quiet | v = 1000 + floor(20 hp/max), or 1025 + floor(24 hp/max) for HoR and Marcella |
   | mite_chan | v = 18965 |
   | mite_near | 1000..1049, within 2 of the quiet value |
   | mite_contact | 90..100 (100 - d) |
   | mite_offset | v - {2000, 3000, 5000, 6460, 7460, 9460} in 90..100 (3000 covers the 11-09 12:00 version's 3095-3099) |
   | fish_mod | Fish's residue alone |
   | res_same | the same residue mod N+1 as this enemy's first nonzero value (a rank-free structure test) |
   | zero / other | 0 / none of the above |

4. **Sub-models**: each class is a per-game mixture of its current encoding and a variant of it, so the class
   stays recognisable from the parts that still hold if one part changes.
   - Each variant re-tokenises the class's own games as if that part were gone.
   - Fish: 0.9 current, 0.1 "levels changed" (only the residue matches). The variant is left out when N+1
     divides 100: other teams' "per-champion constant + multiples of 100" values (test4 on 4-body rosters)
     then match residues too.
   - Mite: 0.85 current, 0.15 "quiet and channel constants gone".
   - Other: one model, with token frequencies averaged over teams.
5. **Scoring**: the posterior is prior + draft + logsumexp over sub-models of (log w + 0.5 x sum of log
   P(token | sub)).
   - P is smoothed and floored at eps = 0.02 / 11.
   - The 0.5 temper allows for correlated reads.

## Data

- 11-08 onwards only (user).
- Sides, after removing duplicates, excluding our own masked side: 4,450 other, 3,372 Mite, 814 Fish.
- Sources:
  - The "other" pull: ~4k games of the final teams (NEETCoders, test4, Nyx, Trzy Kwaterki, Sponge) and the
    top UK teams (BattleCats, Claudus Maximus, Team Kungarna, bentheboss, ...), plus Vvvvv, Ad Astra,
    caterpillow and a random ladder sample. Copied from big-arm's capture.db to
    `~/tmp-offload/oppre/replays/others/`.
  - mite-re's 11-09 Mite downloads.
  - 600 sampled Fish 11-08+ games from fish-re's pull.
- Split: train before 11-09 12:00, test from 11-09 12:00. The test set includes Mite's newest version.

## Encodings on the newest games (11-09 12:00 onwards)

- **Fish:** 95.3% of counted reads match the full formula (quiet 40.4%, contact 54.9%). The rest keep Fish's
  rank residue (4.7%).
- **Mite:** 96% are Mite tokens or 0: contact 41.9%, zero 21.9%, quiet 15.7%, offsets 14.5%, channel 2.1%.
  Fish's residue 1.3%, other 2.3%.
- Neither team masks its priorities; both are plain values. The shares are the same on 11-08, before 11-09
  12:00 and after it, across Mite's four draft versions.

## Accuracy on held-out games (test from 11-09 12:00)

Per champion instance (what one instance of our bot sees), 19,201 instance-games:

| round | acc | fish recall | mite recall | other recall | p(true)>0.8: fish / mite / other | wrong at >0.9: fish / mite / other |
|---:|---:|---:|---:|---:|---|---|
| 1 | 92.7% | 78.2% | 92.9% | 95.3% | 0.71 / 0.69 / 0.94 | 1.2% / 0.1% / 0.1% |
| 25 | 94.4% | 83.4% | 94.5% | 96.5% | 0.77 / 0.79 / 0.95 | 1.2% / 0.1% / 0.1% |
| 50 | 96.2% | 90.7% | 95.8% | 97.9% | 0.85 / 0.89 / 0.97 | 1.2% / 0.1% / 0.1% |
| 100 | 97.6% | 96.0% | 97.3% | 98.6% | 0.92 / 0.93 / 0.98 | 0.5% / 0.1% / 0.1% |
| 200 | 98.7% | 97.9% | 98.5% | 99.2% | 0.96 / 0.96 / 0.99 | 0.2% / 0.1% / 0.0% |
| 300 | 99.4% | 98.6% | 99.5% | 99.6% | 0.97 / 0.98 / 0.99 | 0.1% / 0.1% / 0.0% |
| 1000 | 99.8% | 97.6% | 100% | 100% | 0.97 / 0.99 / 1.00 | 0.0% |

- **Team view** (union of our champions' sightings, 3,643 games): 90.6% at r1, 96.1% at r50, 98.0% at r100,
  99.9% at r300.
- **Where the early accuracy comes from:** most of it is pick order. Without the draft, accuracy is 57.8% at
  r50 and 70.7% at r100 per instance, limited by sight: about half of games see any enemy priority by r50 and
  76% by r100.
- **Once a priority is read**, precision is ~99%.
- **Leave-one-team-out** for "other": each team is scored by a model fitted without it, i.e. an unseen
  team.
  - Misread at r300: NEETCoders 0.4%, test4 0.9%, BattleCats 0.4%, Claudus 0.9%, Kungarna 0.3%,
    bentheboss 4.6%, Nyx 0.4%, Trzy 0%, Sponge 0%.
  - Confidently (>0.9) misread as Fish or Mite at r300: at most 0.3%, except bentheboss 2.5% (a team that
    sets no priorities until 11-09).

## Robustness: test teams' reads re-tokenised as if their code changed (models unchanged)

| change | Fish or Mite recall at r100 / r300 | note |
|---|---|---|
| Fish changes its levels (residue kept) | 88.8% / 89.3% | without the variant: 54% / 36% |
| Mite drops its quiet and channel constants | 95.9% / 97.8% | without the variant: 92% / 89% |
| Fish changes everything | 44% / 23% | falls back to "other" (safe) |
| Mite changes everything | 50% / 26% | falls back to "other" |

- A third variant, Fish changing its rank order (only residue consistency), was dropped. It made test4 and
  BattleCats read as Fish (up to 16% at r1000).
- Drafts change between versions (Mite's did 4 times on 11-09). Capping the pick-order log ratio at 3
  changed little and lost accuracy, so there is no cap (`draft_cap` = 1e9).

## Bot equals offline

- **Native token check:** `token_test.cc` builds `opp_token.h` natively. It matches the Python tokens on all
  590,405 sampled real reads (Fish, Mite and other games).
- **Local games:** 10 games of ocean-opp (debug) against bots/fish, which writes Fish's encoding.
  - From the bot's own inputs (`OPPT` lines), every token and every `OPPC` posterior equals the offline
    code (2,014 tokens, 1,547 lines).
  - From the replays alone (enemy state at the end of the previous round), all 1,547 lines agree within
    0.002.
  - Before the one-band tolerance in fish_quiet, 3 lines in 1,581 differed: health read after Fish's write.
- **Live trace:** `ocean-opp-live` is the same with `live_trace = true`.
  - It prints `OPPL round handle fish mite other fish_hits mite_hits other_hits zero_hits` (plain printf)
    at the first read, on argmax changes and every 100 rounds.
  - Replays at 100M are identical (52/52); it costs +425 fuel a turn.
  - big-arm's capture keeps our team's stdout file in each zip (empty today, as release builds print
    nothing), so the trace can be read back from captured live games.

## Files

- `tokens.py`, `model.py`: tokens, model, fit, trajectory, `load_tables`.
- `build_ds.py`: extracted replays to per-side datasets.
- `evaluate.py`: time split, leave-one-team-out, `--ablate`, `--subs`.
- `gen_tables.py`: writes `opp_tables.h`.
- `check_bot.py`: OPPC/OPPT lines against offline.
- `token_test.cc`: native token check.
- Data and logs are in `~/tmp-offload/oppcls/`.
