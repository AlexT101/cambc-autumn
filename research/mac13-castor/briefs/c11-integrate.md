# Brief C11: integrate the programme's positive pieces into one bot (implementer)

Worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch `main` or
`/home/ubuntu/cambc-autumn` except to read). Follow `AGENTS.md` and `cambc-rules.yaml`. Don't change drafts or emblem
choices. Never edit `bots/variants/chy-ref`, `bots/charybdis` or another implementer's directory.

## Setup
`./copybot variants/c7-pgem variants/c11-int` (never copy `.cambc/`); edit only `bots/variants/c11-int/src`.

## The pieces (each a diff against its own base; all bases are c7-pgem v4 unless said)
PIECES

## The task
1. Apply every piece onto c11-int. Where two touch the same function, merge by meaning, not by text: the pieces
   share one valuation (gems at `1 + prism_premium` in a keeping Prism's bag, gold at `prices().per_gold`), so a merged
   decision must use both changes, each once. List each conflict and how you resolved it.
2. Build; a read-only auditor subagent (told explicitly not to edit anything) checks
   `diff -ruN bots/variants/c7-pgem/src bots/variants/c11-int/src` against the pieces' diffs for lost or doubled
   changes and for bugs. Fix what it finds.
3. Smoke: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c11-int variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c11-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`; out-of-fuel counts near chy-ref's.
4. One train reading: same command with `--suites maps/suites/mac13/train --name mac13-castor-c11-train1`
   (10,240 games) in a tmux session `mac13-castor-c11-train1`; wait for it (no foreground sleep).
5. Save `research/mac13-castor/patches/c11-int.diff` (against c7-pgem, `diff -ruN`) and `c11-int-full.diff`
   (against chy-ref). Don't commit. Kill your tmux sessions.

Return: the conflicts and resolutions, the auditor's findings and fixes, smoke and train readings (with OOF counts).
