#pragma once
// Tuned constants (tools/tune/tunify.py): tune.py patches the values after the magic in the built wasm.
struct DianaTune {
    char magic[16];
    float f[33];
    int i[34];
};
extern "C" {
[[gnu::used, gnu::visibility("default")]] inline DianaTune diana_tune = {"DIANA-TUNE-BLK1", {0.3555806f, 0.10935836f, 0.22716701f, 0.4412562f, 0.6881714f, 0.45716766f, 1.8913636f, 0.795274f, 1.4112711f, 0.90085506f, 0.62638295f, 1.6830473f, 0.511203f, 3.9086132f, 2.3171902f, 0.5149115f, 3.8296325f, 1.6413994f, 0.8934753f, 0.40265793f, 1.3968046f, 0.60775375f, 0.6832753f, 0.25452974f, 1.3611484f, 0.055977345f, 0.21658388f, 0.32032415f, 1.2148346f, 272.98257f, 16.016766f, 83.167366f, 66.34215f}, {7, 13, 11, 9, 4, 12, 12, 26, 12, 6, 5, 34, 6, 19, 10, 2, 76, 30, 13, 20, 10, 20, 2, 4, 5, 2, 70, 3, 512, 600, 200, 100, 3, 6}};
}
