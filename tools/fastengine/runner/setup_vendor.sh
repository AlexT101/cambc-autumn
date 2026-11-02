#!/bin/sh
# Recreate vendor/: upstream wasmtime 49.0.2 from the cargo registry plus cambc's fuel accounting, and
# wasmtime-internal-cranelift 49.0.2 plus a hook that reports bulk-memory fuel decisions (native mode).
set -e
cd "$(dirname "$0")"
reg="${CARGO_HOME:-$HOME/.cargo}/registry/src"
src=$(ls -d "$reg"/*/wasmtime-49.0.2 2>/dev/null | head -1)
if [ -z "$src" ]; then
  (cd ../floor && cargo fetch) && src=$(ls -d "$reg"/*/wasmtime-49.0.2 | head -1)
fi
rm -rf vendor/wasmtime && mkdir -p vendor && cp -r "$src" vendor/wasmtime
(cd vendor/wasmtime && patch -p1 < ../../wasmtime-49.0.2-cambc.patch)
cl=$(ls -d "$reg"/*/wasmtime-internal-cranelift-49.0.2 | head -1)
rm -rf vendor/wasmtime-internal-cranelift && cp -r "$cl" vendor/wasmtime-internal-cranelift
(cd vendor/wasmtime-internal-cranelift && patch -p1 < ../../wasmtime-internal-cranelift-49.0.2-cambc.patch)
