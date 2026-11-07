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
# simde headers for the wasm engine backend (FASTRUNNER_ENGINE=wasm; wasm2c's SIMD needs them): from the system
# (libsimde-dev) or extracted from its .deb into vendor/simde/include. Optional: without them (or without wabt's
# wasm2c) build.rs builds the runner without that backend.
if [ ! -d /usr/include/simde ] && [ ! -d vendor/simde/include/simde ]; then
  t=$(mktemp -d)
  if (cd "$t" && apt-get download libsimde-dev >/dev/null 2>&1 && dpkg-deb -x libsimde-dev_*.deb pkg); then
    mkdir -p vendor/simde && cp -r "$t/pkg/usr/include" vendor/simde/
  else
    echo "setup_vendor.sh: no simde headers; the wasm engine backend will not be built" >&2
  fi
  rm -rf "$t"
fi
