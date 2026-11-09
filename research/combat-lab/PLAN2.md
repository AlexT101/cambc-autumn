# Combat lab, round 2: behaviours, not knobs (plan, 2026-11-08)

Planning only: nothing run, nothing changed. Base: current `bots/ocean` (oc-base29 + 472/473), frozen at the start as
`variants/oc-cl2-base`.

**Target:** ≥ 55% against that frozen copy, on fresh `--mix ladder-v2` suites, held out, then the panel. Fewer
deaths, better predictions, or a small significant gain are intermediate evidence, not completion.

## Why round 1 found nothing

Round 1 showed that particular predictors and score reweightings didn't help. It did not show that ocean's combat is
near optimal.

- **It tested only alternatives ocean already generates.**
  - Rollout k banned the search's choices 0..k-1 (`lab.h` LabBan), so it saw ocean's next-best candidates.
  - Those survive guards, the exact-pricing cap and `Front::admit`, which keeps each end tile's candidates by
    immediate score and enemies removed (`plan.cc:307`).
  - A plan that is worse now but leaves a different follow-up never reached the lab. Nor did behaviours ocean has
    no generator for: occupying an exit, an escape that takes one hit to break sight.
- **What it learned were weights.**
  - Exp 1 refit the score's own terms.
  - The reply model was a better predictor, trained on ocean's and astraeus's replies. It reached only about one
    exactly priced tile a search, and its cost fell in the heaviest turns.
- **Its scenarios had low fidelity:** fresh fighter memory, empty shared memory, teammates idle at spawn, no
  captures or channels (RUNNER.md "Not set exactly"). These are exactly the states that pursuit persistence, ally
  commitment and reinforcements depend on.
- **The measurement was weak:** each fighter's first decision only, a 30-round health-and-deaths reward that
  ignores farm time, averaged over 20k frames, and no frames read by hand.

## Gaps in ocean's combat reasoning

The common thread: ocean searches one turn well, but it judges safety on the state before acting, prunes plans by
immediate score, and has no model of how a pursuit or a team fight unfolds over the next few turns.

### G1. Escape and pursuit (first)

**Retreat.** Spawn is the right default goal: allies are near, enemies are fewer, and arriving heals. The gaps are in
how the route there is chosen.
- A step farther from home is dropped if anything can hit it (`fight.cc:217`). That rules out taking one hit to
  round an obstacle, break sight (attacks need a visible target), cross a hole only our dash crosses, or reach a tile
  the pursuer cannot keep up with.
- Steps are ranked one at a time by the damage tallied before our next turn. HomeWalk checks the whole walk, but
  only when no step is clear.
- `fixc_commit` (turn and fight) fires only with exactly one enemy within 8.
- The ally on the way home is ignored. The fix weights the home field toward a healthy, non-carrier ally when the
  stand with them is won.
- History:
  - 88% of deaths follow a retreat within 4 turns.
  - Retreat deaths happen at a median of full health, 22 steps from home.
  - The old "doomed, so stand and shoot" change lost because its worst-case reach called survivable walks doomed
    (EXPERIMENTS "Ranged retreat steps"). The comparison has to be better; retreat reasoning should not be dropped.

**Chase.**
- `chase()` and the strike search's aim both head for attack range of the target's *current* tile (`fight.cc:797`,
  `plan.cc:2101`). The dash fires whenever we are more than range + 1 away.
- Nothing chooses between following, holding an exit, keeping sight, or approaching from the side a teammate can
  finish from.
- 11.5% of chases kill. Top teams' lone pursuers kill hurt targets at twice our rate, and TODO.md still marks that
  open.
- The fleer's route is **not** assumed to be its shortest path home. It gets its real options: turning, dashing,
  counterattacking, running to its allies. A futility stop ships only if the lab shows it.

**One mechanism serves both sides.**
- A short continuation comparison over 2-4 turns, for us against the visible pursuers or fleer: our candidate
  routes against their best legal replies, with dash and stun cooldowns and turn-order seats.
- Retreat candidates: direct, lateral or sight-breaking, hit or stun then go, dash now or later, counterattack.
- Chase candidates: follow, cut off an exit, flank with a second pursuer.
- Camp fire is part of each route's price on both sides: who is a camp's nearest champion when it strikes. It is not
  credited as a separate hit; that was level in "Camp aggro", 2026-11-03.
- Second-order costs are priced: whether following costs the pursuer its ranged attack, dragging a pursuer onto a
  Willow, Cassi or carrier, and losing sight of the fleer.
- Runs only on turns inside an enemy's reach, under a fuel budget, judged against a burn arm of equal cost.

### G2. Safety after the action, not before it

- `Search::offer` removes guarded end tiles (`ends &= ~guarded`, `plan.cc:1579`) before applying the candidate's kills
  and stuns.
- The grid-edge `lethal(p)` check (`plan.cc:2230`) reads the turn-start roster.
- So the search knows an attack removes a threat, yet still excludes the destination on the earlier state. Affected
  plans: attack then step out, kill through a blocker, stun then step in.
- Fix: re-judge guarded and lethal tiles only for candidates that kill or stun a threat, on the remaining enemies,
  with retaliation and the exact turn the stun takes. Safety limits are not removed globally.

### G3. Team fights: commitment and coherent replies

- **Coordination:**
  - `want_home` is decided by each champion alone, on visible allies within 4.
  - A teammate's leave is learned a turn late, though shared-memory writes reach teammates acting later in the same
    round.
  - History: with allies near, top teams' death rate at contact falls from 16% to 5%; ours stays near 18%.
- **The fight model:**
  - The fight sim pools each side's damage on the other's weakest member and gives stuns to the strongest eligible
    opponent (`safety.cc:96`).
  - The danger in the search counts each enemy's blow in full against every ally it can reach (`plan.cc:2199`).
  - Lead to verify: kill bids may count teammates' damage without committing them to deal it.
- **Mechanisms:**
  - A leave/commit bit in comms' free bits.
  - Short coordinated sequences instead of independent choices: pin and finish, cover an exit, peel for a
    retreating or weak body (Cassi in C&I, 87% of our games), protect a carrier, keep the healer in range, move off a
    target a teammate already kills.
  - Enemy replies are coherent legal sequences: an enemy that hits us does not also hit our ally, but it can hit
    one and cast at the other.

### Quick checks, not phases

Ocean already remembers enemy Strength, Focus and emblems through fog. Two narrower discrepancies to check along the
way:
- An enemy that walks home out of sight and heals stays hurt in our beliefs. Only a respawn or a recall we saw resets
  it (`world.cc:1887-1924`).
- The fight sim drops an unseen enemy's shield (`safety.cc:259`), while other health calculations keep it. The right
  treatment is the uncertainty, not either extreme.

### Not pursued (evidence against)

- Focus fire: 92-94% of first hits have one target in reach.
- When to start fights: Fish engages less than we do in every state.
- Exclusive-spell rate: H0 at 1.5-3.0.
- Turn order: closed by 464.
- Camp-hit credit: level.

## Three phases

### 1. Lab v2

The deliverable is trustworthy counterfactuals, with the situation tables as a free by-product.

- **Stateful forks.**
  - Play full local games in the scenario runner (wasm engine, all champions live) and snapshot at sampled
    encounters: first contact, mid-fight turning points, retreats, aborted engagements and won fights.
  - Fork from there with every bot's memory, shared memory, captures and channels intact.
  - Reconstructed scenarios stay for isolated mechanism tests only.
- **Wider alternatives:**
  - force any concrete action at a fighter's turn (walk, dash, target, cast or nothing), ocean playing on after;
  - log what `Front::admit`, the guard and the cap discarded;
  - lab-only mechanism switches, so candidate and control are one copy.
- **Search for the best action** at each sampled decision, against two continuation opponents (ocean, and astraeus
  or a spar-gated Fish model), keeping only results that repeat.
- **Reward v2** at 10, 30 and 60 rounds: deaths priced by respawn and income, bags, kill gold, time off work,
  reported per part.
- **Read 20-30 high-loss frames per gap by hand**, winning and losing counterfactuals alike.
- Run the two quick checks alongside.

### 2. Build behaviours, in order G1 → G2 → G3

Per behaviour:
1. implement it as a mechanism in a lab copy;
2. paired lab result on its situation, then across all sampled frames for side effects;
3. read the frames where it lost;
4. revise before going on.

Stack them as each passes. Count fuel against a burn arm of equal cost.

### 3. Full games

1. Port the stack to a release ocean variant.
2. `ab.py` against `oc-cl2-base` at real fuel on fresh `ladder-v2`, `--no-test-draft`: 20k games, held out on an
   unused suite, then the panel and `--mix varied`.
3. Report against the 55% target, with uncertainty and per-opponent results.
4. Record everything in EXPERIMENTS.md, including what lost.
