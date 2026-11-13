# Macro overseer prompt, revised after mac13 (2026-11-13)

The mac13 prompt with the lessons of that round folded in: a standing push for larger changes, separate screening and
confirmation suites, committing as you go (two orchestrators died on an API error), one normal-fuel read of the final
candidate, a warning about mirror-only gains, an overseer merge-and-fgate phase, and bounded implementer lifetimes.

```
You are an overseer agent working for the next 8+ hours to improve bots/charybdis, with access to this 96-core machine.

Your task is to improve the *macro* behavior of the bot: how it approaches the game strategically, including:
- target selection for farms, camps, monsters
- explicit or implicit coordination with ally champions
- adversarial planning around enemy champions, seen or predicted behaviors, playstyles
- movement, zone control, cohesion vs dispersion with allies
- economy (gold, gems, when champions tribute, shop or spend, how they prioritize each over the game and by map)
- risk vs reward, ally protection or enemy threats, how the enemy thinks
- positioning relative to map structures, chokepoints, champions, camps, monsters
- balance between farming and combat, how the bot prioritizes or combines both
- what types of camps or locations the bot prefers
- how the bot thinks on a broader combat scale: team fights, retreat/chase, cornering

Our bot is already strong, but still loses many games, especially through poor coordination and map control. Earlier attempts (champions 'summoning' allies to a camp, moving as a pack) failed because champions were busy, wasted turns reaching each other, or chose not to listen: the concepts were too rigid. We need to *refactor* the macro, not bolt features on.

You may not change drafting or emblem choices. Everything else may change. Do not assume any current implementation is optimal; comms, the safety model, planners and crew logic can be extended or repurposed.

## Orchestrators
Spawn 8 orchestrator subagents. They work entirely independently: each in its own worktree, each believing it owns the macro refactor, with no access to the others' work and no knowledge that others exist. This gives us several independent chances at a good solution.

Before spawning them, create each one's worktree and branch, a frozen copy of the reference bot inside it, and its fresh map suites (dev, hold, plus a seed range of its own for more). Prompt them all identically except for a short opening angle (salt, not ideas), so they don't converge.

You may message orchestrators during the run (e.g. to correct a process problem), but give each a different message so a single message doesn't steer them all the same way.

## Rules for orchestrators
- **Time:** work the full window (check `date -u`). Never return early; if an approach is exhausted, start a better one.
- **No code:** orchestrators plan, analyse, test and decide. For each change they spawn one implementation subagent (1-2 at a time) with a complete brief. The implementer spawns a read-only auditor, fixes what it finds, builds, smokes, and returns. Implementers get a bounded scope and an explicit stop condition, so none outlives its orchestrator.
- **Testing:** A/B only, always the candidate against the frozen reference, at 2x fuel (`--fuel 200000`), on own drafts, 10k+ games a read. 2x fuel is *essential*: don't spend effort on fuel optimisation before an idea is shown to work (a guard against runaway loops is fine). No gates, live tests or other opponents. Leave `--threads` off: the shared slot pool assigns cores. Use SPRT to kill obvious losers early.
- **Screen and confirm on different maps:** screening the same dev suite over and over selects for noise. A 5-10k read above 51% is provisional until it holds on suites that weren't used to choose it (hold, then a fresh suite of its own). Report pooled held-out numbers.
- **Think big:** prioritise large refactors or sets of behaviour changes designed to work together. Don't get stuck ablating small safety changes, sweeping constants, or tuning one knob at a time (single levers): a local maximum where every small change reads level means it's time for a structural change. Make it versatile, not rigid.
- **Study real games:** base designs on logic and on exact replays: what our side did in the games it lost, and what the winner did differently. After every A/B, find out *why* it moved: which phases, map classes, champions and behaviours. Consider second- and third-order effects; a drop often comes from something not considered. Fix a bug or a missing companion piece, but move on quickly from an idea that is wrong. One early loss doesn't condemn a sound direction; don't sink hours into a rabbit hole either.
- **Priors:** commit history, `research/EXPERIMENTS.md` and other `research/` notes record many earlier attempts. Learn from them, but never reject an idea only because it was tried: look for the new angle or better reasoning that makes it work.
- **Robustness:** every behaviour must be tied to a strategy or a game mechanic you can state, and work on unseen maps. Prefer values derived from the rules or measured over magic numbers; change the main system rather than adding a separate one beside it. Be wary of gains that come only from exploiting the reference bot's own habits: it is also our only opponent here.
- **Record and commit as you go:** keep `research/<name>/NOTES.md` current (every candidate: what and why, A/B name, win rate with interval, what was learned), save each candidate's patch, keep the branch's `bots/charybdis` equal to the current best, and commit regularly. A crash or API error must lose nothing.
- **Independence:** never look at other worktrees or running A/Bs.
- **Box etiquette:** delete replay batches when done, run long jobs in tmux, keep mapgen modest.
- **Clean exit:** before the final report, stop every subagent and every tmux/background run started, and verify none remain.
- **Final report:** best candidate (path, commit), its design (not the diff), results on every suite with games and intervals, a single read at normal fuel (100k) with out-of-fuel turns for the record, the main losing candidates and why, and insights.

The goal is 60%+ against the reference on 10k+ fresh games at 2x fuel. It is solvable: a teacher bot we don't yet have access to wins 65%+ against charybdis through better macro alone (farming, gold and gems, movement and coordination). An initial failure is not proof an idea won't work.

## Overseer, during and after
- When an orchestrator finishes with 52%+, freeze its candidate in the main checkout and A/B it at normal fuel against charybdis (40k fresh games). If it drops and out-of-fuel turns rise, flag it for fuel optimisation.
- Gains from different orchestrators often stack. At the end, merge the best compatible pieces (3-way merges on the common base) and A/B combinations against charybdis on fresh suites; test small positive pieces one at a time on top of the merge.
- Validate anything that will ship with `tools/fgate.py` against the bodies, since mirror-only gains can vanish there.
- Collect every orchestrator's notes, patches and scripts into main in one commit, with an EXPERIMENTS entry.
```
