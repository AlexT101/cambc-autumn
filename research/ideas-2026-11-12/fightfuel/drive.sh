#!/bin/bash
# drive.sh J ARM...: arm.sh for each arm (debug, --fuel 200000 unless FUEL is set), J at a time.
J=$1; shift
export DEBUG=${DEBUG-1} FUEL=${FUEL-200000}
printf '%s\n' "$@" | xargs -P $J -I{} $(dirname $0)/arm.sh {}
