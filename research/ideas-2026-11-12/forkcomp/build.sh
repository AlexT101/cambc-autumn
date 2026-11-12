#!/bin/sh
# Builds the livefork runner copy into replays/forkcomp/runner (gitignored): the current runner source plus livefork.rs.
# The shared runner (tools/fastengine/runner) is not touched. Run from the repo root.
set -e
R=replays/forkcomp/runner
mkdir -p $R
cp -r tools/fastengine/runner/src tools/fastengine/runner/wengine tools/fastengine/runner/Cargo.toml tools/fastengine/runner/Cargo.lock \
      tools/fastengine/runner/build.rs tools/fastengine/runner/fastrunner $R/
ln -sfn "$PWD/tools/fastengine/runner/vendor" $R/vendor
cp research/ideas-2026-11-12/forkcomp/livefork.rs $R/src/
(cd $R/src && patch -p0 lib.rs < ../../../../research/ideas-2026-11-12/forkcomp/lib.rs.patch)
cd $R && FASTRUNNER_ENGINE_WASM="$OLDPWD/tools/replay/engine/v3_0_0.wasm" cargo build --release
