"""Draft-only release probe: exact features/work counters/plans and optional full travel-field comparison.

Copies the supplied bot, instruments only that copy, runs both seats and every draft round at 100M,
and keeps compact JSON rows. --plain measures uninstrumented release fuel; --real uses the real budget.
"""
import argparse
import json
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import cambc_env
import cpu_slots


def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def instrument(bot, target, travel, profile, coverage):
    shutil.copytree(bot / "src", target / "src", dirs_exist_ok=True)
    p = target / "src/draft/draft.cc"
    s = p.read_text()
    s = replace(s, "namespace model {", '''namespace model {
void dump_features(const std::array<double, mapfeat::count>& raw) {
    std::printf("RAW");
    for (double v : raw) std::printf(" %a", v);
    std::printf("\\nWORK %d %d %d %d %d %d\\n", feature_work.sight_sources, feature_work.sight_steps,
                feature_work.dash[0], feature_work.dash[1], feature_work.crystal[0], feature_work.crystal[1]);
}
''')
    s = replace(s, "    const auto team = mapfeat::model_team(raw, picks);", "    dump_features(raw);\n    const auto team = mapfeat::model_team(raw, picks);")
    s = replace(s, "    write_plan(state);", '''    write_plan(state);
    char hex_plan[2 * sizeof(state.plan.bytes) + 1];
    constexpr char digits[] = "0123456789abcdef";
    for (std::size_t i = 0; i < sizeof(state.plan.bytes); ++i) {
        hex_plan[2 * i] = digits[state.plan.bytes[i] >> 4];
        hex_plan[2 * i + 1] = digits[state.plan.bytes[i] & 15];
    }
    hex_plan[2 * sizeof(state.plan.bytes)] = 0;
    std::printf("PLAN %d %s\\nPICKS %d", draft_round(), hex_plan, draft_round());
    for (const auto c : draft_order()) std::printf(" %d", static_cast<int>(c));
    std::printf("\\n");''')
    if coverage:
        s = replace(s, "    if (far.is_empty()) return 0;", '    if (far.is_empty()) { std::printf("WARDZERO %d\\n", site); return 0; }')
        c = target / "src/draft/map_features.cc"
        t = c.read_text()
        t = '#include <cstdio>\n' + t
        t = replace(t, "    int seen = 0, far = 0;", "    int seen = 0, far = 0, fast2 = 0, fast3 = 0, slow = 0;")
        t = replace(t, "            if (steps) *steps += 2;", "            ++fast2;\n            if (steps) *steps += 2;")
        t = replace(t, "            if (steps) *steps += 3;", "            ++fast3;\n            if (steps) *steps += 3;")
        t = replace(t, "        p[0] = take", "        ++slow;\n        p[0] = take")
        t = replace(t, "    return r3(static_cast<double>(far) / std::max(1, seen));", '    std::printf("GAP %d %d %d\\n", fast2, fast3, slow);\n    return r3(static_cast<double>(far) / std::max(1, seen));')
        c.write_text(t)
    if profile:
        for label, before in [
            ("start", "    if (params::test_draft || model_draft() || cambc::draft::team_size() != 3) draft_order();"),
            ("model", "    const auto afford = [](std::uint64_t cost)"),
            ("map", "    if (!a.budgeted) work_budget(map, a, spawn_fields)"),
            ("fields", "    if (!header.steps) {"),
            ("steps", "    a.dash_spawn = a.dash_spawn && header.spawn_offsets;"),
            ("dash", "    make_leads(map, a, first ? floor(0) : draft_reserve());"),
            ("leads", "    for (; !a.attacks_done && a.attack_group"),
            ("attacks", "    if (a.ward_bits < 0) {"),
            ("index", "    for (; a.ward_site < static_cast<int>(a.ward_codes.size());"),
            ("wards", "    if constexpr (params::open_plan::on)"),
            ("candidate_fields", "    float value = 0;\n    int iterations = 0;"),
            ("search", "    op::Lists worked;"),
            ("finish", "    write_plan(state);"),
        ]:
            s = replace(s, before, f'    std::printf("LAP {label} %llu\\n", static_cast<unsigned long long>(cambc::fuel_remaining()));\n' + before)
    if travel:
        h = target / "src/draft/map_features.h"
        h.write_text(h.read_text().replace("using TravelField =", "int reference_travel(const Input&, const std::vector<int>&, int, std::vector<int>*, int*);\nusing TravelField ="))
        c = target / "src/draft/map_features.cc"
        t = c.read_text()
        t = replace(t, "std::uint32_t model_features() {", '''int reference_travel(const Input& in, const std::vector<int>& base, int level, std::vector<int>* out, int* work) {
    return Grid{in}.travel(0, base, level, out, work);
}

std::uint32_t model_features() {''')
        c.write_text(t)
        s = replace(s, "struct Measured {", '''int checked_travel(const mapfeat::Input& in, const std::vector<int>& base, int level, std::vector<int>* out, int* work) {
    std::vector<int> before, after;
    int wb[2], wa[2];
    const auto f0 = cambc::fuel_remaining();
    const int vb = mapfeat::reference_travel(in, base, level, &before, wb);
    const auto f1 = cambc::fuel_remaining();
    const int va = engine_travel(in, base, level, &after, wa);
    const auto f2 = cambc::fuel_remaining();
    std::printf("TRAVEL %d %d %d %d %d %d %llu %llu\\n", level, before == after, vb == va, wb[0] == wa[0], wb[1] == wa[1],
                static_cast<int>(before.size()), static_cast<unsigned long long>(f0 - f1), static_cast<unsigned long long>(f1 - f2));
    if (work) work[0] = wa[0], work[1] = wa[1];
    if (out) *out = std::move(after);
    return va;
}

struct Measured {''')
        s = s.replace("engine_clearance, &feature_work, engine_travel)", "engine_clearance, &feature_work, checked_travel)")
    p.write_text(s)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bot")
    ap.add_argument("name")
    ap.add_argument("--maps", default="research/charybdis-draftfuel/maps.txt")
    ap.add_argument("--travel", action="store_true")
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--plain", action="store_true")
    ap.add_argument("--direct", action="store_true", help="with --plain, build the supplied bot in place")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--jobs", type=int, default=32)
    args = ap.parse_args()
    if args.direct and not args.plain:
        ap.error("--direct requires --plain")
    target = ROOT / args.bot if args.direct else ROOT / "bots/variants" / f"probe-{args.name}"
    out = ROOT / "replays/draftlab" / args.name
    out.mkdir(parents=True, exist_ok=True)
    if args.plain and not args.direct:
        shutil.copytree(ROOT / args.bot / "src", target / "src", dirs_exist_ok=True)
    elif not args.plain:
        instrument(ROOT / args.bot, target, args.travel, args.profile, args.coverage)
    with (out / "build.log").open("w") as log:
        subprocess.run(["cambc", "build", "--release", str(target)], stdout=log, stderr=subprocess.STDOUT, check=True)
    maps = [ROOT / p for p in (ROOT / args.maps).read_text().splitlines() if p]
    manifest = out / "manifest.txt"
    manifest.write_text("".join(f"{target} {target} {p} {out / f'{i}.repl26a'}\n" for i, p in enumerate(maps)))
    runner = ROOT / "tools/fastengine/runner/fastrunner"
    env = cambc_env.env()
    env["FASTRUNNER_MODE"] = "native"
    with (out / "run.log").open("w") as log:
        subprocess.run([str(runner), "run-batch", str(manifest), "--release", "--rounds", "0",
                        "--jobs", str(args.jobs), "--slot-dir", str(cpu_slots.DIR), "--slots", str(cpu_slots.SIZE)]
                       + ([] if args.real else ["--fuel-quantum", "100000000"]),
                       stdout=log, stderr=subprocess.STDOUT, env=env, check=True)
    rows = []
    for i, p in enumerate(maps):
        bundle = out / f"{i}.repl26a"
        with zipfile.ZipFile(bundle) as z:
            for side in "ab":
                lines = z.read(f"team-{side}.stdout").replace(b"\0", b"").decode().splitlines()
                fuel = z.read(f"team-{side}.fuel")
                rows.append(dict(map=str(p.relative_to(ROOT)), side=side,
                                 fuel=[v[0] for v in struct.iter_unpack("<Q", fuel[77:])],
                                 lines=[s for s in lines if s.split(" ")[0] in {"RAW", "WORK", "PLAN", "PICKS", "TRAVEL", "LAP", "GAP", "WARDZERO", "DRAFT-CAPPED"}]))
        bundle.unlink()
    (out / "rows.json").write_text(json.dumps(rows))
    failures = [r for r in rows if (not args.plain and not any(l.startswith("PLAN") for l in r["lines"])) or
                any(l.startswith("TRAVEL") and l.split()[2:6] != ["1"] * 4 for l in r["lines"])]
    print(f"{len(rows)} drafts, {len(failures)} missing plans or travel mismatches; {out / 'rows.json'}")
    for r in failures[:10]:
        print(r["map"], r["side"], [l for l in r["lines"] if not l.startswith(("PLAN", "RAW"))])
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
