# hecate: open work

## Direction

- A robust, intuitive, logical bot: behaviour derived from the rules (reach, sight, cooldowns, health, walking
  distance, measured rates) over tuned constants, fixed decision orders or special cases.
- Logical changes stay even when level or slightly below 50%; drop only what is clearly worse (below ~47% over 1102
  games) or wrong.
- No new fuel gates. Make work cheap or bounded instead; the plan is [FUEL-GATES.md](FUEL-GATES.md).
- Keep the teleport, Tavi and Willow code.

## Candidates

Each needs an A/B (see [../EXPERIMENTS.md](../EXPERIMENTS.md) first). Bundle removals and keep them if level.

- Removals: `killable_now` with want_home's kill plumbing and `Safety::fight`'s `exclude` (its experiment was level);
  `keep_walk`'s free-stun logic in `enemy_cast`, replaced by a plain threshold; ground casts at unseen enemies
  (`max_unseen_tiles`); the rally bit (`post_rally`, `sight_fight`), which nothing reads; big-group sieges on normal
  maps (`big_rounds`, `big_respawn_wait`; sieges there lost 39.6%); the delayed tribute stun (`tribute_to_stun_later`,
  the D branch, the `hold` parameter; keep `can_stop_winning_tribute`).
- Behaviour: one `run_home()` for `retreat()` and `carry_bag`'s retreat; give kite's stations line of sight, as
  `spell_clear` has; drop kite's contested branch; pack-zone ratio `(home || hurt) ? 2.0 : none`;
  `Safety::expected_damage` as a tie-break in `retreat_step` and `flee_camps`; walk to lock an altar where a visible
  enemy tributes a big bag (`Altar::lock_tiles()` as goals); spell-clear pricing (`spell_clear_rounds`) tested both
  ways; probabilistic `threatened()` removed (risky: it gates recalls). Ren's specials change only on ladder evidence.

## Don't remove

These have evidence behind them: `step_guard`, `pursuit`, `threat_strike`; Monolith sieges; kite on shared-gem maps.
