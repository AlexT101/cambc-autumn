# Macro overseer round mx (2026-11-13, 14:20 - ~22:30 UTC)

Six independent orchestrators (TETHYS, RHEA, PHOEBE, THEIA, CRIUS, IAPETUS), each owning a macro refactor of
charybdis 529 in its own worktree `/home/ubuntu/wt/mx-<name>` on branch `mx-<name>-20261113` (from main 822f6253b).
Brief: [orchestrator-brief.md](orchestrator-brief.md), filled per orchestrator in its branch's `research/mx-<name>/BRIEF.md`.

- Reference: `bots/variants/chy-ref` in each worktree = charybdis 529 (bbc7cddb6).
- Suites, `--mix ladder-v4` (340 maps a seed), under each worktree's `maps/suites/mx/`:

| Orchestrator | dev (5,100 maps) | hold (5,100 maps) | own range | Opening angle |
|---|---|---|---|---|
| TETHYS | 61400000-61400014 | 61400100-61400114 | 61401000-61409999 | where each champion's turns go in lost games |
| RHEA | 61410000-61410014 | 61410100-61410114 | 61411000-61419999 | what the enemy sees and predicts of us, and what we could infer of it |
| PHOEBE | 61420000-61420014 | 61420100-61420114 | 61421000-61429999 | the flow of gems and gold from camp to bag to altar or shop |
| THEIA | 61430000-61430014 | 61430100-61430114 | 61431000-61439999 | how the team shares the map, and when that changes |
| CRIUS | 61440000-61440014 | 61440100-61440114 | 61441000-61449999 | the turning points of lost games |
| IAPETUS | 61450000-61450014 | 61450100-61450114 | 61451000-61459999 | terrain: chokes, altars, spawns, bushes, walls |

Smoke before launch: chy-ref copy vs chy-ref, 256 ladder games at 2x fuel: 50.0%, 0 failed.

## Overseer reads at normal fuel (100k), vs `bots/charybdis` (529), own drafts, release builds

| Candidate | Frozen as | 2x read by its orchestrator (vs chy-ref) | 100k read | OOF CAND / REF |
|---|---|---|---|---|
| IAPETUS `ia-contest` (line B: contest judgement; branch mx-iapetus-20261113 @d250e0662) | `bots/variants/ia-contest-d250e06` | pooled held-out 51.1 (50.6-51.7) of 30,600 | **50.3 (49.8-50.8) of 40,120** (`overseer-mx-iacontest-100k`, suite `maps/suites/overseer-mx/iac100k` = seeds 61490000-61490058, ladder-v4, 20,060 maps) | 292,880 / 278,255 (+5%) |
| IAPETUS `ia-prism-v1` (line D v1: the Prism's bag, stop_due; branch mx-iapetus-20261113 @3bf1525b5) | `bots/variants/ia-prism-3bf1525` | pooled held-out 53.3 (52.8-53.8) of 40,800 | **52.9 (52.4-53.4) of 40,120** (`overseer-mx-iaprism-100k`, suite `maps/suites/overseer-mx/iap100k` = seeds 61490100-61490158, ladder-v4, 20,060 maps) | 318,049 / 309,008 (+3%) |
| THEIA `dnw-min` (deny_late + deny_alarm on 529; branch mx-theia-20261113 @ba7a6c500) | `bots/variants/theia-dnwmin-ba7a6c500` | pooled held-out 52.1 of 30,600 (vs 529) | **49.0 (48.5-49.5) of 40,120 against chy-530** (`overseer-mx-dnwmin-vs530-100k`, seeds 61490200-61490258) | 335,594 / 346,804 (-3%) |
| IAPETUS `ia-final` rebased onto 531 (branch @f32ce0a89) | `bots/variants/ia-final-531` | pooled held-out 53.2 (52.8-53.7) of 51,000 (vs 529) | **49.3 (48.8-49.7) of 40,120 against chy-531** (`overseer-mx-iafinal-vs531-100k`, seeds 61490400-61490458) | 357,693 / 343,175 (+4%) |
| THEIA `denyfix-531` (branch @b1e18da2d) | `bots/variants/denyfix-531-b1e18da` | smoke only (reads skipped at the user's request) | **50.1 (49.7-50.6) of 40,120 against chy-531** (`overseer-mx-denyfix531-vs531-100k`, seeds 61490600-61490658) | 361,751 / 351,030 (+3%) |

## Process notes
- 16:00 UTC: subagents are handed back after ~100 min of runtime (RHEA twice). Each hand-back is resumed by SendMessage.
- 17:20 UTC: tmux sessions lacked `CAMBC_SLOTS`, so most A/Bs (163 of 250 summaries) ran with 94 slots (cores - 2) instead of 86; set `tmux set-environment -g CAMBC_SLOTS 86`. Unthreaded `extract.mjs` runs (6-12 cores each) also overloaded the box (load 180); the three orchestrators doing it were told to pass `--threads 8`.

## Ended early at the user's request (17:30 UTC, to save usage)
- **RHEA** (branch mx-rhea-20261113 @9b225b1c6): no confirmed gain; bots/charybdis = chy-ref. C1-C7 level or losing (C5 race 32-41, C2 spacing -5). Open lead: **C8 `urgency`** (stop_game_ender's "whatever the risk" charge only when the ender's channel clock requires it) 52.5 (50.4-54.7) of 2,040 debug games, binds in 27% of games flipping 86 to wins vs 34 to losses, all late; unconfirmed at 10k. Tools: `research/mx-rhea/scripts/bind.py` (first divergence against the deterministic mirror). Insight: every cautious rule around the Prism and winning tributes lost; the bot sits on a flat optimum for caution.
- **PHOEBE** (branch mx-phoebe-20261113 @a5460af12; its bots/charybdis = p-nolock): no structural gain. Best `p-nolock` (never buy altar locks) pooled held out 50.35 of 20,400 (dev 51.2). A `phb-hub` (allies price groups the Prism can collect), B `phb-lethal` (no turn ends inside enemy Prism's lethal reach; unaudited), C `phb-stakes` (fight model prices lives/bags by output and Prism premium; unaudited, known bugs) all level. Insights: labour and walking bind, not supply (Prism ~54% of r1-400 moving); first Prism death decides most games (survivor's team 94%); the richer Prism wins the duel because its wealth reflects its own captures; lethal exposure predicts 39-55% next-round deaths but avoiding it trades farm time and reads level.
- **CRIUS** (branch mx-crius-20261113 @1267e53d1; bots/charybdis = chy-ref): no gain. A Prism collector, B Elk/Golem crews, C contact-loss hazard in farm pricing, D state-priced fight stakes all level (49.6-50.3 audited); E denial-valued middle groups -3 (gives up the middle: whoever wakes a middle group captures it 88%); F two-job farm lookahead unfinished. Insights: r300 economic gap is the middle (+43.7 vs +11.5 own half); Prism bag lead at r150 converts 63-72%; 43% of first Prism kills come without a 50+ gem edge, with the victim outnumbered by ~1 (the clearest swing left); only 5.9% of winning Prism channels complete.

## Merged
- 18:00 UTC: `ia-prism-v1` merged into main as **charybdis 530** (CHANGES 530, EXPERIMENTS "Macro round mx"), with
  IAPETUS's notes snapshot from its branch at cd3f88583 (`research/mx-iapetus/`). Not yet gated or live; a fuel pass first.

## Standing instructions (user, ~18:15 UTC)
- Codex fuel pass (`/home/ubuntu/wt/fuel-530`, branch fuel-530-20261113, tmux `codex-fuel530`): if it finds fuel cuts, squash into one commit and merge into main, provided they are behaviour-identical (not necessarily byte-identical; Codex states which).
- Any orchestrator's new improvement: A/B at normal fuel on a new 40k-game fresh suite against the merged 530 (`variants/chy-530`).
- Teammate live-test requests may be approved, with the caveat that the work is in progress and may vary on the ladder. Live scheduling stays with the teammate.

## Round closed (19:50 UTC)
All six orchestrators exited; their notes are under `research/mx-*/`. Main ships 530 (IAPETUS's stop_due + contest judgement) and 531 (Codex fuel pass). Every later candidate read level or below against 531 at 100k.

`results/` holds each overseer A/B's `summary.md` (win rates, intervals, out-of-fuel turns, batch names). The
orchestrators' mapgen logs (`logs/gen*.log`) stay on their branches; Codex's full transcript stays in
`/home/ubuntu/wt/fuel-530/research/fuel-530/codex.log` (its final summary: `research/fuel-530/CODEX-SUMMARY.md`).
