#pragma once
// Tuned constants (research/diana-2026-11-03/tunify.py): tune.py patches the values after the magic in the built wasm.
struct DianaTune {
    char magic[16];
    float f[17];
    int i[6];
};
extern "C" {
[[gnu::used, gnu::visibility("default")]] inline DianaTune diana_tune = {"DIANA-TUNE-BLK1", {0.5f, 500.0f, 300.0f, -1.0f, 1.0f, 0.5149115f, 1.6413994f, 0.511203f, 272.98257f, 16.016766f, 0.21658388f, 0.3555806f, 0.4412562f, 3.9086132f, 2.3171902f, 0.25f, 0.2f}, {5, 34, 19, 7, 4, 10}};
}
