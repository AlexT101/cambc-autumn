# Brief s3: the Prism war, turn by turn (study, no bot change kept)

A bounded measurement study for the orchestrator of a macro refactor of the C++ bot `charybdis`. Read
`/home/ubuntu/wt/mac13-kronos/AGENTS.md` and `cambc-rules.yaml` first. Work ONLY in `/home/ubuntu/wt/mac13-kronos`
(do not touch `/home/ubuntu/cambc-autumn` or other worktrees; do not commit; no A/Bs, no bot edits).

## Data (already played and extracted)
`replays/batch-20261113-034628-ab-mac13-kronos-bel-study512` holds 1,024 debug mirror games (`kr-beliefs` = chy-ref
with a belief dump flag, against `chy-ref`; same play). Extracted under `replays/.analysis/<sha>/` (meta.json,
rounds.json.gz: per-champion per-round x, y, hp, alive, gems, foc, chan, cd0/cd1, sees, ...; events.jsonl.gz:
moves, casts, attacks, deaths with killer `by`, captures, tributes). Use `CAMBC_ANALYSIS=replays/.analysis`; match by
`meta.json` `source` containing `bel-study512`. The replay zips' `team-a.stdout` / `team-b.stdout` carry debug
traces, including per-turn `D <round> <id> <branch> <farm_group> <claim>` lines (see `bots/variants/chy-ref/src`
for the format and the branch letters; grep `"D %` / `debug_block`). Example scripts: `research/mac13-kronos/scripts/`
and `/tmp/kr/pvp.py`, `/tmp/kr/dom.py`, `/tmp/kr/dom3.py`.

## What is known
- In both-Prism games, the first Prism death decides 91% of them (485 of 532); 75% of Prism deaths are by the
  enemy Prism; 390 of 922 both-Prism games have no Prism death.
- Prism-vs-Prism encounters (both within 6, a new episode after 20 rounds apart): 3.3 a game. By Focus x health
  ratio at the encounter: <1.2: 5% weak dies within 20 rounds; 1.5-2: 16%; 2-3: 22%; 3+: 53% (40% of encounters).
- A Focus ratio of 2+ is first reached at mean round 493 in 894 games, yet that Prism's team wins only 62%:
  later 253 weak deaths (median 85 rounds after), 392 recoveries to <1.5 (234 with the strong Prism's bag down
  to <60%), 219 game ends. The two Prisms' mean distance over the next 100 rounds has median 20.6 tiles.
- Earlier first-Prism-death study: victim/killer Focus median 0.85 (a third of victims were the stronger), victim
  mostly in the retreat branch 'R' for ~5 rounds at distance 3-4, often under 60% health 5 rounds before; the victim
  saw the killer; an allied stunner near the killer in only 6 of 64.

## Questions (answer with counts per game and the code that decides)
1. **How encounters start.** For encounters with a power ratio >= 1.5: who closed the distance (each Prism's moves
   in the 10 rounds before), each one's branch (D lines), what each was doing (farm group, hold, bank, chase), and
   whether the weak one could see / had recently seen the strong one. How often was the weak Prism's farm target
   inside the strong Prism's reach?
2. **Weak Prism deaths.** For each: rounds from first sight to death, the weak one's branches and moves, its
   distance to its own spawn / nearest ally / nearest altar, whether a recall was started and cancelled, whether it
   fought back (casts at the killer) and the killer's health at the end. Would fighting back from the start have
   won (sum of its burst against the killer's health)?
3. **Strong Prism conversion.** When our Prism is dominant (Focus >= 2x the enemy Prism's, both alive), what does
   it do round by round (branch shares)? How often does it chase the weak Prism when it sees it, and why does the
   chase end (lost sight, chase gate, enemy allies, its own health)? How often does it know where the weak Prism is?
4. **Dominant team losses (the 38%).** Classify them: strong Prism killed later, enemy out-tributed us while
   our Prism held its bag (the Prism keeps gems until its bag wins: `keeps_gems`, `economy/bank.cc` ~905), a long
   winning tribute channel cancelled by a stun, others. Give counts.
5. For the top 2-3 levers, estimate the games a fix could swing per 1,000 games, and point to the deciding code
   (file, function).

## Stop condition
Write scripts and a short `README.md` with the tables under `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/s3/`
and return the findings (tables, counts, code locations, the 2-3 most promising levers with estimated size). Do not
delete the batch (other studies use it).
