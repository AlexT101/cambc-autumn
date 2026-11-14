#pragma once
// Tuned constants (tools/tune/tunify.py): tune.py patches the values after the magic in the built wasm.
struct DianaTune {
    char magic[16];
    float f[33];
    int i[28];
};
extern "C" {
[[gnu::used, gnu::visibility("default")]] inline DianaTune diana_tune = {"DIANA-TUNE-BLK1", {0.3250693f, 0.144296984f, 0.329403f, 0.47014135f, 0.6121852f, 0.41559503f, 1.8318122f, 0.76902484f, 1.4890524f, 0.84065454f, 0.63785076f, 1.8913108f, 0.43417029f, 3.8462681f, 2.612499f, 0.531318933f, 4.026606f, 1.407893f, 0.7813574f, 0.48421214f, 1.2686848f, 0.55602146f, 0.6593026f, 0.291859f, 1.2420944f, 0.051062868f, 0.33384038f, 0.3250693f, 1.2420944f, 300.0f, 15.0f, 100.0f, 60.0f}, {6, 13, 12, 8, 4, 11, 12, 33, 11, 6, 4, 45, 5, 22, 8, 2, 64, 32, 15, 21, 10, 23, 2, 9, 5, 2, 55, 3}};
}
