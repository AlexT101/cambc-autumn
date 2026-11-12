#!/bin/bash
# waitgate.sh NAME...: returns once ~/tmp-offload/fightfuel/logs/gate-NAME.done exists for each, then prints their batch lines.
L=~/tmp-offload/fightfuel/logs
all() { for f in "$@"; do [ -e "$L/gate-$f.done" ] || return 1; done; }
until all "$@"; do sleep 30; done
for f in "$@"; do echo "== $f"; grep -E "^batch|ACCEPT|REJECT|ZONE|NARROW|Out-of-fuel|OOF" $L/gate-$f.log | cut -c1-260 | tail -12; done
