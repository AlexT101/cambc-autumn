# Remaining native preparation delay

Read-only diagnosis after the 16-worker compile-only rollout; no games, cache warming, engine changes or active-helper changes were performed for this diagnosis.

Completed ward blocks 623 and 624 each took 20.21s. Their C++/WASM bodies were already built 140–177s before the first native cache use. Mapping exact `bot-injected.wasm` bytes through the runner's FNV128 key to its existing native cache gives first lock-file creation to published-library mtime intervals:

| Block | Flp4 | Mt3q | Sum |
| --- | ---: | ---: | ---: |
|623|6.447s|6.558s|13.005s|
|624|6.457s|6.302s|12.759s|

These filesystem intervals include Cranelift translation, native PGO setup and native compilation; they do not separately measure those phases. The two bodies are demanded sequentially by the existing four-job gate. Full paths/timestamps are in `/home/ubuntu/tmp-offload/compile-ahead-ward16/native-cache-timing.json`; the eight existing A/B summaries per block are recorded in `native-cache-batches.json` there. This is substantial preparation on the scored critical path, despite prebuilt WASM.

`run_batched.build_bots` warms each frozen bot while holding its ordinary `build.lock`. Fastrunner's native cache additionally locks its exact content/flags key. `native.rs::compile` chooses up to 16 compiler processes from available CPU parallelism; `--jobs1` bounds match workers and RAYON controls Cranelift, neither bounds native clang. Restricting CPU affinity would also change the default translation-unit count, so it is not an equivalent scheduling-only solution. No active library change is proposed.

Minimal prospective improvement: a separate serialized prewarm coordinator considers only existing ready bodies in the current+8 window. It attempts up to 16 shared slots and immediately releases/skips if fewer than 16 are actually granted, avoiding retained partial acquisitions. With all 16 held, it takes the same frozen build lock, runs the existing one-round self warm with `--jobs1 --release --rounds1 --log-limit0`, RAYON1 and no nested slot acquisition, then releases all slots. The unchanged native cache/PGO implementation supplies the same reusable artifact; its usual internal PGO self-play is setup, not scored evidence. Owner identity and stop/drain rules still bound the coordinator. No candidate, map, seed, score or stopping rule changes. A single coordinator takes roughly 13s per block of native preparation, so measured steady throughput—not an assumed elimination of all 13s—must justify deployment. Coordinator approved the bounded prototype and ops found no review blocker. The ward then terminated naturally before launch. No prewarm ran, so no speed/resource benefit has been measured and future default warming remains disabled. The prototype and three resource/failure tests are preserved here; offload manifest5a1fd586…08947. No extra warm work was launched after the owner exited.
