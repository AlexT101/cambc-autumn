# Line D: price denial with the enemy Prism's premium (CASTOR's consistency, applied to the other side)

You are an implementation subagent for TETHYS, the orchestrator of a macro refactor of the Cambridge Battlecode bot
charybdis. Worktree `/home/ubuntu/wt/mx-tethys` (branch `mx-tethys-20261113`). Work only there; never touch
`/home/ubuntu/cambc-autumn` (read-only: you may read its committed files) or other worktrees under `/home/ubuntu/wt/`;
never commit or push. Read `AGENTS.md`, `cambc-rules.yaml` and `docs/api/cpp.md` first. C++ only. Comment only
counterintuitive behaviour, concisely.

## Background
- The one large gain of the last programme (CASTOR, +5, now in charybdis) priced a mechanic consistently from the
  rules: `prism_premium` (economy/capture.cc) values a gem kept in our Prism's bag at 1 + expm1(k rho H), the Focus it
  compounds (+1.5 Focus a gem, which farms k rho more gems a round over the H rounds it stays kept). Every ally's crew,
  claim, handoff and holder choice prices it the same way.
- **The enemy side is priced flat.** A gem the enemy Prism captures compounds its Focus the same way, but nothing in
  the farm sees that. Denial is only the static middle weight (`params::mid_exposure` 1.36 in `exposure()`,
  economy/farm.cc) and a comeback-only `deny_scale`. Evidence that denial is under-priced: a control-map line in this
  programme found that plain denial (one gem denied = one gem gained) explains at most a ~1.3 middle premium, while the
  flat optimum sits at ~1.4-1.7. Static weights can't be pushed further (2.2 loses 2): a uniform push sends bodies into
  every contested group, not just the ones that matter.
- What matters (charybdis mirror, 2,720 games):
  - Middle captures decide games. Capture gems a game, winner vs loser: own half about equal (110 vs 107 in r1-150,
    135 vs 128 in r151-300); middle 61 vs 50 in r1-150, 96 vs 67 in r151-300, 190 vs 119 in r301-600.
  - The middle holds more gems than either half (259 gems in 8.3 groups vs ~113 a side). Both teams together capture
    ~22% of its r1-300 potential.
  - The Prism Focus race decides the Prism duel: with both Prisms alive at r250 and the Focus ratio at 1.6+, the
    higher-Focus team wins 80%, and the lower-Focus Prism dies first 48% of the time against 11%. The enemy Prism lands
    ~55% of all kills.
  So each middle gem the enemy Prism takes is worth far more to it than one gem: it is the Focus that kills our bodies.

## Design
1. **The enemy Prism's premium.** Mirror `prism_premium` for the enemy Prism, from what we can observe: its Focus
   (last read), whether it is alive, the enemy's collection pace (`world.score.enemy`, bags seen, kills, over the
   rounds, with the same prior shape `team_farm` uses for us), and the win horizon from the enemy's side. The formula
   (k from the enemy Prism's facts and Focus, rho the enemy's gems per output, H its rounds to the win or the round
   limit) is the same; derive it, don't tune it. If the enemy drafted no Prism, or it is dead, the premium is 0.
2. **Who would take the group if we don't.** For a candidate group g, the chance the enemy Prism (or an enemy body
   feeding it) captures g before its next respawn if we leave it. Derive this from the map and beliefs, e.g. from the
   enemy's side of the map (the mirror of our own home weighting) and the enemy Prism's believed position against
   ours, and say how in one comment. Keep it simple and monotone; no fitted constants.
3. **The denial term.** Farm's value of g gains P_enemy(g) x gems(g) x premium_enemy: only the premium part, since
   plain denial (P x gems) is already inside the tuned static side weights. Add it where farm builds a group's worth
   (the same place the gems and our own premium enter), and keep every prune bound valid: the term can raise a group's
   worth, so the bounds the prunes use (`PreUpper`, `exposure_most`, `rated_below`, `beyond`, `altar_below`) must cover
   its maximum, or the prunes will cut good groups.
4. **Optional, only if (1)-(3) read positive:** the same consistency for kills and deaths. Our body's death to the
   enemy Prism hands it the bag (rules: the killer takes all gems), so the bag's cost to us is also its premium in the
   enemy's hands; killing the enemy Prism removes its premium on its whole bag. Combat prices bags with a flat
   `params::gem_value`; a one-constant scaling of that was level both ways in this programme, so only a version that
   depends on the premium (and on who the killer would be) is worth trying.

Every quantity from the rules and the bot's existing models; no new hand-picked constants. The static side weights
stay as they are.

## Off limits
`draft/` and which emblem a champion builds toward. Never edit `bots/variants/chy-ref`.

## Work
1. `./copybot variants/chy-ref variants/mx-deny` from the worktree root (it leaves out `.cambc/`); work in
   `bots/variants/mx-deny`. `test_draft` stays off.
2. Build: `cambc build bots/variants/mx-deny --release` (without `--release` for debug traces).
3. Iterate with full A/Bs on the train suite (10,200 games, about 2-3 minutes of wall each):
   `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-tethys && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/mx-deny variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-tethys-deny-<tag>`
   Run each in a tmux session named `mx-tethys-deny-<tag>`; wait with a background command, never a foreground sleep.
   Leave `--threads` off. `--debug` (both sides debug) when you need D lines. Never use the dev, hold, conf1 or fin
   suites. Delete each `replays/batch-*` you create once you have read it (~3 GB each). Another implementer runs A/Bs
   on the same box at the same time; that is fine.
4. Check what changed, from replays (`node tools/replay/extract.mjs`, see tools/replay/README.md, `--threads 40` or
   fewer; scripts in `research/mx-tethys/scripts/`: `captures_ground.py` (capture gems by ground and phase),
   `prism_race.py` (Focus ratio at a round and outcomes), `all_deaths.py`, `prism_death.py`): middle captures by phase
   CAND vs REF, the Focus ratio at r150/r250, deaths, and the size of the term (how often it changes the farm's pick,
   and the premium's typical value over a game). When a version loses, find what the bodies stopped doing (farm time,
   captures, deaths, bags) before changing it.
5. Watch fuel: OOF turns must stay near chy-ref's.
6. Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
   change against this design and the rules for bugs; fix what it finds; build; run the smoke
   `py tools/ab.py variants/mx-deny variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, same env
   prefix): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK.

## Stop condition
Return when a version reads at least 51.5% on train over 10,200 games, or after at most six train A/Bs of real
versions (not counting crash/bug reruns), or when you have a clear diagnosis that the design fails. Report through
SubagentHandback: the variant path; each version's change and train read with interval and OOF; the mechanism
counts above, CAND side vs REF side; the auditor's findings and fixes; the final diff stat. Save the final diff with
`diff -ruN bots/variants/chy-ref/src bots/variants/mx-deny/src > research/mx-tethys/patches/mx-deny.diff`. Keep
earlier versions as `bots/variants/mx-deny-vN` if they matter.
