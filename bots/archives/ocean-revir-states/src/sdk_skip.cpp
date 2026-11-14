// The SDK's start-up builds globals the bot never reads: its champion designs (13 champions and their
// abilities from the host, ~5k fuel) and the draft memory snapshot (draft.cc reads its own). Each is
// an inline variable whose initialiser runs only while its guard is 0; these strong definitions
// override the guards' weak ones in unity.cpp. Not in unity.cpp: there they would clash with
// cambc.h's. Without cambc.h, so nothing here can read them. The initialisers test the guard's low bit
// (wasm's 32-bit guard ABI); a reader would see zeroed objects, so there must be none (draft.cc checks
// the names).
[[gnu::used]] int champion_designs_built __asm__("_ZGVN5cambc16champion_designsE") = 1;
[[gnu::used]] int draft_memory_built __asm__("_ZGVN5cambc12draft_memoryE") = 1;
