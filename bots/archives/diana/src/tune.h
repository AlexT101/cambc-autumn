#pragma once
// Tuned constants (research/diana-2026-11-03/tunify.py): tune.py patches the values after the magic in the built wasm.
struct DianaTune {
    char magic[16];
    float f[27];
    int i[24];
};
extern "C" {
[[gnu::used, gnu::visibility("default")]] inline DianaTune diana_tune = {"DIANA-TUNE-BLK1", {0.35f, 0.18f, 0.35f, 0.35f, 0.6f, 0.35f, 2.0f, 0.6f, 1.5f, 0.8f, 0.6f, 2.0f, 0.5f, 3.5f, 3.0f, 0.6f, 4.0f, 1.5f, 0.75f, 0.6f, 1.3f, 0.6f, 0.6f, 0.35f, 1.2f, 0.05f, 0.4f}, {6, 12, 12, 8, 4, 10, 10, 30, 12, 8, 4, 45, 5, 25, 6, 3, 60, 30, 20, 20, 10, 20, 2, 10}};
}
