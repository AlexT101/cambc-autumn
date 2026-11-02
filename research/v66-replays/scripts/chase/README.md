# Chase episodes (2026-11-02)

Chase episodes in the v66 ladder extract (`replays/v66-analysis/ex`): a pursuer that hit its target in the last
3 rounds, within 3 tiles, while the target steps homeward; followed for up to 40 rounds until a kill, the target
reaching its spawn, the pursuer dying, contact lost (`quit`: the pursuer stopped closing; `outrun`) or the target
turning (`stand`). Results in EXPERIMENTS "Chases and leaves on the ladder". Run from the repo root:

    python3 research/v66-replays/scripts/chase/episodes.py OUT/ep.json      # the episodes
    python3 research/v66-replays/scripts/chase/sum.py OUT/ep.json           # endings by state, both sides
    python3 research/v66-replays/scripts/chase/half.py OUT/ep.json          # by target health and half
    python3 research/v66-replays/scripts/chase/rate.py OUT/ep.json          # damage each way a round
    python3 research/v66-replays/scripts/chase/contact.py OUT/ep.json       # hit rate by distance a round
    python3 research/v66-replays/scripts/chase/dbl.py OUT/ep.json research/v66-replays/scripts/chase   # turn order
    M=0 python3 research/v66-replays/scripts/chase/leave.py OUT/ep.json     # our pursuer's decisions (v66 traces)
    python3 research/v66-replays/scripts/chase/paired.py AB_NAME_1 AB_NAME_2   # two ab.py runs against one REF, paired by map and side

Positions at first contact (an enemy within 8 after 5+ rounds with none), EXPERIMENTS "Positions at first contact":

    python3 research/v66-replays/scripts/chase/contact_pos.py OUT/cp.json && python3 research/v66-replays/scripts/chase/cp_sum.py OUT/cp.json
    python3 research/v66-replays/scripts/chase/joiners.py      # who joins the fights that follow, and what happens when they arrive
