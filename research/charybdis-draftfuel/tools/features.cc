// Native oracle for the actual baseline/candidate feature implementations, including scalar fallback paths.
// Build from the repo root with C++20, -O2 -ffp-contract=off -fsanitize=address,undefined.
#define aph before
#include "../../../bots/variants/chy-draftfuel-base/src/draft/map_features.cc"
#undef aph
namespace after { using namespace before; } // Identical generated headers may be coalesced by #pragma once.
#define aph after
#include "../../../bots/variants/chy-draftfuel-final/src/draft/map_features.cc"
#undef aph
#include <cstdio>
#include <random>
#include <string>

int main() {
    std::mt19937 rng(20261112);
    int connected = 0, disconnected = 0;
    for (int run = 0; run < 2500; ++run) {
        before::mapfeat::Input a;
        a.W = 7 + rng() % 94, a.H = 7 + rng() % 94, a.sym = rng() % 3;
        a.sw = a.sh = 3;
        a.t.resize(a.W * a.H);
        before::mapfeat::Grid grid{a};
        const int roughness = run % 5;
        for (int i = 0; i < grid.n; ++i) {
            const unsigned k = rng() % 100;
            a.t[i] = k < 4 * roughness ? before::mapfeat::wall
                     : k < 10 * roughness ? before::mapfeat::hole
                     : k < 15 * roughness ? before::mapfeat::bush : before::mapfeat::ground;
            a.t[grid.mirror(i)] = a.t[i];
        }
        for (int i : grid.spawn_tiles(0)) a.t[i] = a.t[grid.mirror(i)] = before::mapfeat::ground;
        for (int j = 0; j < 3; ++j) {
            int i = rng() % grid.n;
            if (i % a.W < 3 || i / a.W < 3 || i % a.W >= a.W - 3 || i / a.W >= a.H - 3) continue;
            a.t[i] = a.t[grid.mirror(i)] = before::mapfeat::altar;
        }
        after::mapfeat::Input b;
        b.W = a.W, b.H = a.H, b.sym = a.sym, b.sw = a.sw, b.sh = a.sh, b.t = a.t;
        before::mapfeat::Work wa;
        after::mapfeat::Work wb;
        std::array<double, before::mapfeat::count> va{}, vb{};
        std::string ea, eb;
        try { va = before::mapfeat::compute(a, nullptr, true, before::mapfeat::every, nullptr, &wa); }
        catch (const std::exception& e) { ea = e.what(); }
        try { vb = after::mapfeat::compute(b, nullptr, true, after::mapfeat::every, nullptr, &wb); }
        catch (const std::exception& e) { eb = e.what(); }
        if (ea != eb) return std::fprintf(stderr, "exception mismatch %d\n", run), 1;
        if (!ea.empty()) { ++disconnected; continue; }
        ++connected;
        for (int k = 0; k < before::mapfeat::count; ++k)
            if (va[k] != vb[k] && !(std::isnan(va[k]) && std::isnan(vb[k])))
                return std::fprintf(stderr, "feature mismatch %d %d: %a %a\n", run, k, va[k], vb[k]), 1;
        if (std::memcmp(&wa, &wb, sizeof(wa))) return std::fprintf(stderr, "work mismatch %d\n", run), 1;
        for (int picks = 3; picks <= 5; ++picks)
            if (before::mapfeat::model_team(va, picks) != after::mapfeat::model_team(vb, picks))
                return std::fprintf(stderr, "team mismatch %d %d\n", run, picks), 1;
        for (int side = 0; side < 2; ++side) {
            std::vector<int> da;
            after::mapfeat::Distances db;
            after::mapfeat::Grid other{b};
            grid.bfs(grid.spawn_tiles(side), grid.pass_for(side, nullptr), da);
            other.bfs(other.spawn_tiles(side), other.pass_for(side, nullptr), db);
            for (int level = 1; level <= 2; ++level) {
                std::vector<int> xa;
                after::mapfeat::Distances xb;
                int ca[2], cb[2];
                const int sa = grid.travel(side, da, level, &xa, ca), sb = other.travel(side, db, level, &xb, cb);
                if (sa != sb || !std::equal(xa.begin(), xa.end(), xb.begin(), xb.end()) || ca[0] != cb[0] || ca[1] != cb[1])
                    return std::fprintf(stderr, "travel mismatch %d %d %d\n", run, side, level), 1;
            }
        }
    }
    std::printf("2500 maps: %d connected / %d disconnected; features, work counters, teams and four travel fields match\n",
                connected, disconnected);
}
