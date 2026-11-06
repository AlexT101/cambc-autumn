// Local builds only. cambc builds against this repo's sdk/cpp, so every local build (cambc build, run, run-batch,
// ab.py, bench.py, the draft lab, tune.py, debug or --release) finds this file; the platform builds a submission's
// src/ against its own SDK, which has none. Bots test for it with __has_include(<cambc_local.h>) to fail loudly on
// a broken draft handoff locally while keeping their graceful fallback on the ladder.
#pragma once
#define CAMBC_LOCAL 1
