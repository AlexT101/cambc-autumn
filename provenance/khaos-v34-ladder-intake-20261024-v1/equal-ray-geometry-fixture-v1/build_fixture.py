#!/usr/bin/env python3
"""Extract and compile exact equal-ray production excerpts against tiny mocks."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BOT = ROOT / "bots/variants/willow-v47-equal-ray-escape-work/src"
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def balanced(text, start):
    brace = text.index("{", start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unclosed source body")


pathing_path = BOT / "pathing.cpp"
header_path = BOT / "pathing.h"
util_path = BOT / "util.h"
pathing = pathing_path.read_text()
header = header_path.read_text()
util = util_path.read_text()
source_aggregate = subprocess.check_output(["sh", "-c", "shasum -a 256 src/* | shasum -a 256"], cwd=BOT.parent, text=True).split()[0]
expected_aggregate = "c1e19d45475ca18d2a74c344da8372d9112cc9215c8261eb4023b987db02b4e5"
if source_aggregate != expected_aggregate:
    raise SystemExit(f"candidate source aggregate mismatch: {source_aggregate}")

at_start = pathing.index("std::optional<int> Pathing::CampEscape::at(vec2 p) const")
at_end = balanced(pathing, at_start)
at_body = pathing[at_start:at_end]

loop_start = pathing.index("            for (unsigned i = 0; i < 8; ++i) {", pathing.index("const Pathing::CampEscape& Pathing::camp_escape"))
loop_end = balanced(pathing, loop_start)
ray_loop = pathing[loop_start:loop_end]
exact_text = "            if (out.steps != unreachable) out.exact = !any_within(goals, here, out.steps - 1);"
exact_start = pathing.index(exact_text, loop_end)
exact_end = exact_start + len(exact_text)
exactness_statement = pathing[exact_start:exact_end]

directions_start = util.index("inline constexpr vec2 directions[8]")
directions_end = util.index(";", directions_start) + 1
directions_decl = util[directions_start:directions_end]

required_header = "std::uint8_t rays = 0; // bits in directions order: tied shortest straight witnesses; 0 uses labels"
if required_header not in header:
    raise SystemExit("source/header shape mismatch: equal-ray mask declaration missing")
if "out.rays |= static_cast<std::uint8_t>(1u << i);" not in ray_loop:
    raise SystemExit("source shape mismatch: equal-ray insertion missing")

pins = {
    "schema": "equal-ray-geometry-fixture-source-pins-v1",
    "sourceAggregate": "c1e19d45475ca18d2a74c344da8372d9112cc9215c8261eb4023b987db02b4e5",
    "sources": [
        {"path": str(pathing_path), "sha256": sha(pathing_path)},
        {"path": str(header_path), "sha256": sha(header_path)},
        {"path": str(util_path), "sha256": sha(util_path)},
    ],
    "extracted": [
        {"source": "pathing.cpp", "symbol": "Pathing::CampEscape::at", "startByte": at_start,
         "endByte": at_end, "startLine": pathing[:at_start].count("\n") + 1,
         "endLine": pathing[:at_end].count("\n") + 1},
        {"source": "pathing.cpp", "symbol": "CampEscape shortest-ray scan/update loop", "startByte": loop_start,
         "endByte": loop_end, "startLine": pathing[:loop_start].count("\n") + 1,
         "endLine": pathing[:loop_end].count("\n") + 1},
        {"source": "pathing.cpp", "symbol": "CampEscape exactness assignment", "startByte": exact_start,
         "endByte": exact_end, "startLine": pathing[:exact_start].count("\n") + 1,
         "endLine": pathing[:exact_end].count("\n") + 1},
        {"source": "util.h", "symbol": "directions[8]", "startByte": directions_start,
         "endByte": directions_end, "startLine": util[:directions_start].count("\n") + 1,
         "endLine": util[:directions_end].count("\n") + 1},
    ],
    "limits": [
        "The exact production at() body and ray scan/update loop are compiled and executed.",
        "The goal/wall bitboards, bounds, direction vector arithmetic, and distance-field labels are declared host mocks.",
        "The exact production exactness assignment runs with an independent host-mock any_within; Pathing cache key/rebuild/invalidation, native distance-field construction, route ranking caller, SDK and gameplay are not executed. Invalidation is source-reviewed and stale-result refusal is tested by setting valid=false.",
        "The independent two-ray ranking case demonstrates that the newly labeled route is a usable candidate; it does not execute the production caller's ranking loop.",
    ],
}
(OUT / "SOURCE-PINS.json").write_text(json.dumps(pins, indent=2) + "\n")

prelude = r'''#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <optional>
#include <queue>
#include <cstdio>

constexpr int unreachable = 999;
struct vec2 {
    int x, y;
    static const vec2 north, north_east, east, south_east, south, south_west, west, north_west;
    friend bool operator==(vec2 a, vec2 b) { return a.x == b.x && a.y == b.y; }
    friend bool operator!=(vec2 a, vec2 b) { return !(a == b); }
    friend vec2 operator+(vec2 a, vec2 b) { return {a.x + b.x, a.y + b.y}; }
    friend vec2 operator-(vec2 a, vec2 b) { return {a.x - b.x, a.y - b.y}; }
};
inline constexpr vec2 vec2::north{0, 1};
inline constexpr vec2 vec2::north_east{1, 1};
inline constexpr vec2 vec2::east{1, 0};
inline constexpr vec2 vec2::south_east{1, -1};
inline constexpr vec2 vec2::south{0, -1};
inline constexpr vec2 vec2::south_west{-1, -1};
inline constexpr vec2 vec2::west{-1, 0};
inline constexpr vec2 vec2::north_west{-1, 1};

struct bitboard {
    bool cells[15][15]{};
    friend bool operator==(const bitboard& a, const bitboard& b) {
        for (int y = 0; y < 15; ++y) for (int x = 0; x < 15; ++x)
            if (a.cells[y][x] != b.cells[y][x]) return false;
        return true;
    }
    friend bool operator!=(const bitboard& a, const bitboard& b) { return !(a == b); }
};
struct Labels {
    int cells[15][15];
    int at(vec2 p) const { return cells[p.y][p.x]; }
};
struct Pathing {
struct CampEscape {
    vec2 origin{-1, -1};
    std::uint8_t rays = 0;
    int steps = unreachable;
    bool valid = false, exact = false, exhausted = false;
    bitboard walls{}, goals{};
    Labels label_storage{};
    Labels* labels = &label_storage;
    std::optional<int> at(vec2 p) const;
};
};
using CampEscape = Pathing::CampEscape;
bool in_bounds(vec2 p) { return p.x >= 0 && p.y >= 0 && p.x < 15 && p.y < 15; }
bool test(const bitboard& b, vec2 p) { return in_bounds(p) && b.cells[p.y][p.x]; }
void set(bitboard& b, vec2 p) { b.cells[p.y][p.x] = true; }
int dist(vec2 a, vec2 b) { return std::max(std::abs(a.x - b.x), std::abs(a.y - b.y)); }
int steps_at(const Labels& l, vec2 p) { return l.at(p); }
bool any_within(const bitboard& goals, vec2 origin, int radius) {
    for (int y = 0; y < 15; ++y) for (int x = 0; x < 15; ++x)
        if (goals.cells[y][x] && dist({x, y}, origin) <= radius) return true;
    return false;
}
'''

test_code = r'''
static void expect(std::optional<int> actual, int expected) {
    assert(actual.has_value() && *actual == expected);
}
static void init_labels(CampEscape& e, int value = unreachable) {
    for (auto& row : e.label_storage.cells) for (int& v : row) v = value;
}
static void discover_rays(CampEscape& out, vec2 here, int ray_limit,
                          const bitboard& walls, const bitboard& goals) {
    out.origin = here;
    out.steps = unreachable;
    out.rays = 0;
    out.exact = false;
    RAY_LOOP
    EXACTNESS_STATEMENT
    out.valid = true;
}

static int independent_best_ray(const CampEscape& e, const std::array<int, 8>& exposure,
                                vec2 home) {
    int best = -1;
    std::pair<int, int> score{100000, 100000};
    for (unsigned i = 0; i < 8; ++i) {
        if (!(e.rays & (1u << i))) continue;
        vec2 p = e.origin + vec2{directions[i].x, directions[i].y};
        std::pair<int, int> next{exposure[i], dist(p, home)};
        if (next < score) score = next, best = static_cast<int>(i);
    }
    return best;
}

int main() {
    // Unique east ray: exact production labels match the old single-ray contract.
    CampEscape one;
    bitboard open{}, east_goal{};
    set(east_goal, {9, 7});
    discover_rays(one, {3, 7}, 8, open, east_goal);
    assert(one.exact && one.steps == 6 && one.rays == (1u << 2));
    for (int k = 0; k <= 6; ++k) expect(one.at({3 + k, 7}), 6 - k);
    assert(!one.at({5, 8}));
    assert(!one.at({10, 7}));

    // Equal shortest north/east rays are both retained and both descend exactly.
    CampEscape equal;
    bitboard goals{};
    set(goals, {10, 7}); set(goals, {4, 13});
    discover_rays(equal, {4, 7}, 8, open, goals);
    assert(equal.exact && equal.steps == 6);
    assert(equal.rays == ((1u << 0) | (1u << 2)));
    for (int k = 0; k <= 6; ++k) {
        expect(equal.at({4, 7 + k}), 6 - k);
        expect(equal.at({4 + k, 7}), 6 - k);
    }
    assert(!equal.at({5, 8})); // unchecked diagonal chord stays unknown
    std::array<int, 8> exposure{0, 99, 9, 99, 99, 99, 99, 99};
    assert(independent_best_ray(equal, exposure, {4, 7}) == 0);
    // Positive ranking witness: the second equal ray is preferable by existing risk/home inputs.
    exposure = {8, 99, 1, 99, 99, 99, 99, 99};
    assert(independent_best_ray(equal, exposure, {4, 7}) == 2);
    assert(equal.at({5, 7}).has_value()); // formerly discarded ray is now an available option

    // A longer third ray is not stored as though it had the minimum length.
    CampEscape longer;
    bitboard three_goals{};
    set(three_goals, {10, 7}); set(three_goals, {4, 13}); set(three_goals, {11, 14});
    discover_rays(longer, {4, 7}, 8, open, three_goals);
    assert(longer.steps == 6 && longer.rays == ((1u << 0) | (1u << 2)));
    assert(!longer.at({5, 8})); // off both retained rays; the longer NE ray is not admitted

    // A blocker truncates a ray; that direction is not admitted even if a farther goal exists.
    CampEscape blocked;
    bitboard block{}, blocked_goals{};
    set(block, {4, 9}); set(blocked_goals, {4, 13}); set(blocked_goals, {10, 7});
    discover_rays(blocked, {4, 7}, 8, block, blocked_goals);
    assert(blocked.steps == 6 && blocked.rays == (1u << 2));
    assert(!blocked.at({4, 8}));
    assert(!blocked.at({4, 9}));

    // A closer off-ray goal makes the ray result non-exact; the existing field mode is then used.
    CampEscape field;
    bitboard field_goals{};
    set(field_goals, {10, 7}); set(field_goals, {6, 8});
    discover_rays(field, {4, 7}, 8, open, field_goals);
    assert(!field.exact && field.steps == 6 && field.rays == (1u << 2));
    field.steps = 1; field.rays = 0; field.exact = true;
    init_labels(field);
    field.label_storage.cells[7][4] = 1; field.label_storage.cells[8][6] = 0;
    expect(field.at({4, 7}), 1); expect(field.at({6, 8}), 0);
    assert(!field.at({7, 7}));

    // Existing exhausted/unreachable and unknown behavior is unchanged.
    CampEscape exhausted;
    exhausted.valid = exhausted.exact = exhausted.exhausted = true;
    exhausted.steps = unreachable;
    expect(exhausted.at({2, 2}), unreachable);
    CampEscape unknown;
    unknown.valid = true; unknown.exact = false;
    assert(!unknown.at({2, 2}));

    // Stale-key/post-move results must be invalidated before changing topology/origin.
    CampEscape stale = equal;
    stale.valid = false;
    set(stale.walls, {5, 7});
    stale.origin = {5, 7};
    assert(!stale.at({5, 7}));

    std::puts("equal-ray production excerpts passed: unique/equal/longer/blocked/field/off-ray/stale cases");
}
'''.replace("RAY_LOOP", ray_loop).replace("EXACTNESS_STATEMENT", exactness_statement)

source = prelude + "\n" + directions_decl + "\n" + at_body + "\n" + test_code
(OUT / "fixture.cpp").write_text(source)

compiler = "c++"
binary = OUT / "fixture"
cmd = [compiler, "-std=c++17", "-O0", "-Wall", "-Wextra", "-Werror", str(OUT / "fixture.cpp"), "-o", str(binary)]
result = subprocess.run(cmd, text=True, capture_output=True)
(OUT / "build.stdout.log").write_text(result.stdout)
(OUT / "build.stderr.log").write_text(result.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
run = subprocess.run([str(binary)], text=True, capture_output=True)
(OUT / "run.stdout.log").write_text(run.stdout)
(OUT / "run.stderr.log").write_text(run.stderr)
if run.returncode:
    raise SystemExit(run.returncode)
receipt = {
    "schema": "equal-ray-geometry-fixture-run-v1",
    "command": cmd,
    "buildExit": result.returncode,
    "runExit": run.returncode,
    "stdout": run.stdout,
    "sourcePinsSha256": sha(OUT / "SOURCE-PINS.json"),
    "fixtureSha256": sha(OUT / "fixture.cpp"),
    "coverageLimit": pins["limits"],
}
(OUT / "FIXTURE-RESULT.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(run.stdout, end="")
