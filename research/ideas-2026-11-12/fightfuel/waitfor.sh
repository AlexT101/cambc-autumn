#!/bin/bash
# waitfor.sh FILE...: returns once every file exists (checks every 20 s).
all() { for f in "$@"; do [ -e "$f" ] || return 1; done; }
until all "$@"; do sleep 20; done
