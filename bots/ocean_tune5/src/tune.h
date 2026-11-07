#pragma once
// Tuned constants (research/diana-2026-11-03/tunify.py): tune.py patches the values after the magic in the built wasm.
struct DianaTune {
    char magic[16];
    float f[18];
    int i[8];
};
extern "C" {
[[gnu::used, gnu::visibility("default")]] inline DianaTune diana_tune = {"DIANA-TUNE-BLK1", {0.611298f, 518.07043f, 0.82206106f, 0.4954379f, 1.3651814f, 0.4941909f, 271.7049f, 16.884615f, 0.22276546f, 0.29771978f, 0.48756322f, 3.9570758f, 2.360914f, 0.23589598f, 0.19388914f, 0.25f, 2.0f, 1.0f}, {6, 26, 19, 7, 3, 10, 8, 100}};
}
