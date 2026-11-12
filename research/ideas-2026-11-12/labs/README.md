# Lab filler (2026-11-12)

User, 2026-11-12: "if local queue is exhausted, add something to do like run some labs, tuning, emblem/item/draft,
etc at end of queue to use the compute", then "build off the best version". This is the documented decision to run
labs as filler, the lowest-priority work. It replaces, for filler use only, the earlier rule that every lab is a
separate decision. The reason for the first rounds: charybdis has changed a lot since its last fits. Draft18 was
refitted on 514; 517-520 changed Prism survival, its carry and its shards. Emblems are still ocean 504's, fitted on
ocean 501. No lab has run on 520.

## How it works

`filler.py` is a daemon. State lives in `~/tmp-offload/labs`; the file list is in its docstring.
- **Base.** The `BASE` file holds a bot directory (`bots/variants/chy-life` at the start). It is read when a round is
  created, so the coordinator switches it with `ctl.sh base bots/variants/X` and needs no restart. A round keeps its
  base, plays a private copy of it (`variants/labsrc-ID`), and names the base in its candidate.
- **Order.** `LIST` gives the kinds in priority order. The next round is the first kind with no round yet on the
  current base. When the list is done, the filler waits for `BASE` to change and then runs the list again on the new
  base.
- **Emblem opponents.** `EMB_OPPONENTS.json` (`opponents` shares, `opponent_bots` dirs), when present, replaces the emb
  round's default opponents; a round copies it at setup. elab plays plain bot dirs, so a run-time fgate body is used
  as baked one-member copies (`experiment_config.h` returning a fixed seed and salt), checked to replay the run-time
  body game for game first. From 2026-11-12 ~16:20 it holds the Fish r8 body (`fr8-g25-s952/953`) and `mf-f9-s952/953`
  at 0.5 each: 256/256 ladder games identical in winner and length to the run-time bodies at the same seed.
- **Start.** A round starts only after 3 polls a minute apart in which nobody else runs a gate, A/B, lab, bench or
  mapgen (Python or node running fgate, ab.py, run_batched, solo, lqgate, mapgen, the labs, tune or bench), and at
  most 6 main-pool slots are held by others.
- **Yield.** A started round runs to its end, at nice 19 and slot weight 0.001 in group `labs-ID`. Under fair share,
  a group below its weighted share, or one with no other waiting group below theirs, may take a free slot. So when a
  gate waits, the lab keeps at most one slot, and the gate gets every other slot as the lab's games end (seconds).
  Every phase (mapgen, games, fits) takes its slots from the pool.
- **Output.** Each round writes a candidate, never a merge. On success that is `bots/variants/lab-ID-BASENAME`, plus
  its patch against the base (`patches/lab-ID-BASENAME.patch`) and `candidate.json`. The filler then appends one line
  to `~/tmp-offload/handoff/parked/labs.ready`: `labs ID CANDIDATE|NO-CANDIDATE|FAILED base=... cand=... patch=...
  :: summary`. The coordinator gates each candidate on held-out fresh maps like any other change.
- **Control.** `ctl.sh status | start | pause | resume | stop | kill | base DIR`:
  - pause: no new rounds.
  - stop: the filler exits; a running round goes on.
  - kill: ends the running round's process group.
- **Recovery.** Each step of a round leaves a done-file, so a round can be resumed. To rerun a failed round, delete
  its `exit` and `posted` files and start its script again by hand with the filler's environment
  (`LABS_FILLER=1 CAMBC_SLOT_GROUP=labs-ID CAMBC_SLOT_WEIGHT=0.001`, fastrunner native). Alternatively, delete the
  round directory and the filler creates a new round.
- **Maps.** Seed block 7700000-7799999 (maps/SUITES.md), 10,000 seeds a round, under the round's own directory.

## The rounds, in order of expected shipping value

| # | kind | what it fits | why this place | games | time on a free box |
|---|---|---|---|---|---|
| 1 | `emb` (emblem round 6) | Round 5's edit lab: 331 whole-policy emblem and shop edits, screened by six rank cuts. The 20 survivors are replicated on new games. | Round 5 found gains its A/Bs confirmed (+0.6 to +1.0, CHANGES 504), and its notes say to rerun on the bot that will ship. Charybdis's Prism banks gems for Focus and buys Health first (520), so what each build pays has moved. It is the cheapest lab and the one checked most carefully against A/Bs. | ~3.4M | ~4 h |
| 2 | `draft` (draft19) | A draft18-style refit (1M games, F92) with the base as the lab player. | Refits on a changed Prism shipped gains: draft10 +0.70, draft18 +1.0 over 514. Since 514, 517-520 cut Prism deaths 18% and raised its gems 8%. It costs about as much as emb, and overfit is checked by parity, the first-turn fuel check and the coordinator's gate. | 1M | ~3.5-4 h |
| 3 | `tune` (tune9) | SPSA on tune1's 19 economy and fight knobs: 700 iterations, mostly against the Fish/Mite bodies. | Weakest record: tune1 read -0.19 (49.81%) and v87's SPSA +0.36 (ZONE). The knobs 507-520 added are derived from rules or measured (EOQ floor, carry reach, carried bonus), so they are not tuned. | ~700 iterations | ~7-10 h |

There is no separate item or shop lab. The emblem lab's 36 structural edits are the shop rules: Greed onset,
Collectors timing, stat order by ordinal. Consumables are not tuned by any lab.

## Candidate rules

- **emb:** replicated edits (new games only) at +0.25 points or more and z >= 2.0, chosen greedily without
  conflicts, placebos excluded. This is round 5's shipped set: one edit at z 6.8 and three near-misses at z 2.0-2.3,
  all of which held in A/Bs.
- **draft:** the lab's searched fit if it ends within 40 minutes, else draft18's plain fit at the starting penalties.
  Native parity must be exact, and the candidate must have no more first-turn drafts over 10M than the base.
- **tune:** the second-half (Polyak) mean. The tunified bot and the port must replay byte-identical at 100M.
