"""Replace a spar body's per-map pick table (patch_spar.py's spar_forced: draft.cc map_hash looked up in spar_draft.h)
with Fish's or Mite's feature pick model (fm_draft_<F|M>.h from fitgen.py): the same on every map, ladder or fresh.
Mite's model samples its comp from the logit's probabilities, seeded by map_hash and SALT (the noise seed); Fish's
takes the most likely.   py patch_fm.py BOT_DIR F|M SALT"""
import sys, re, shutil, os
from pathlib import Path
bot, o, salt = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]); T = Path(os.path.dirname(os.path.abspath(__file__)))
f = bot / 'src/draft/draft.cc'; s = f.read_text()
if 'fm_forced' in s: print('already patched'); sys.exit(0)
assert 'spar_forced' in s, 'not a spar body'
h = (T / f'fm_draft_{o}.h').read_text().replace('namespace fm {', f'namespace fm {{\ninline constexpr std::uint64_t salt = {salt}ull;', 1)
(bot / 'src/draft/fm_draft.h').write_text(h)
s = s.replace('#include "spar_draft.h"\n', '#include "spar_draft.h"\n#include "fm_draft.h"\n', 1)
s = s.replace('const std::vector<cambc::champion_draft>* spar_forced();\n',
              'const std::vector<cambc::champion_draft>* spar_forced();\nconst std::vector<cambc::champion_draft>* fm_forced();\n', 1)
old = re.search(r'        for \(const auto& e : spar::table\)\n.*?        return nullptr;\n', s, re.S)
assert old, 'spar table loop not found'
s = s[:old.start()] + '        return fm_forced();\n' + s[old.end():]
s = re.sub(r'        const auto h = test_compositions::map_hash\(\);\n        debug_block\(\{ std::printf\("SPARHASH[^\n]*\n', '', s, count=1)
s = s.replace("// Spar opponents (research/notes/ideas-2026-11-08/spar.md): a live opponent's exact picks for this map and side.", '// Spar opponents: Fish\'s or Mite\'s picks from the map\'s features (fm_forced).', 1)
s = s.replace('} // namespace model\n', '''} // namespace model

// The body's pick model (fm_draft.h): a comp chosen from the map's draft-lab features alone, the same rule on every map.
const std::vector<cambc::champion_draft>* fm_forced() {
    const int picks = static_cast<int>(cambc::draft::team_size());
    std::array<double, mapfeat::count> raw{};
    // As model::measure: the draft's work budget (work_budget) counts what the features cost only when told.
    features_measured = true;
    try {
        raw = mapfeat::compute(model::engine_input(), model::engine_walk, true, 0u, model::engine_clearance, &feature_work);
    } catch (...) {
        return nullptr;
    }
    double best = -1e300, total = 0, score[sizeof(fm::comps) / sizeof(fm::comps[0])];
    int arg = -1;
    for (std::size_t i = 0; i < sizeof(fm::comps) / sizeof(fm::comps[0]); ++i) {
        const auto& c = fm::comps[i];
        score[i] = -1e300;
        if (c.n != picks) continue;
        double s = c.b;
        for (int k = 0; k < mapfeat::count; ++k) {
            const double v = std::isfinite(raw[static_cast<std::size_t>(k)]) ? raw[static_cast<std::size_t>(k)] : 0.0;
            if (c.w[k] == 0) continue; // a feature the model leaves out (fitgen.py EXP): not measured
            s += c.w[k] * std::max(-4.0, std::min(4.0, (v - fm::mu[k]) / fm::sd[k]));
        }
        score[i] = s;
        if (s > best) best = s, arg = static_cast<int>(i);
    }
    if (arg < 0) return nullptr;
    if constexpr (fm::sample) {
        for (std::size_t i = 0; i < sizeof(score) / sizeof(score[0]); ++i)
            if (fm::comps[i].n == picks) total += std::exp(score[i] - best);
        std::uint64_t h = test_compositions::map_hash() ^ (fm::salt * 0x9E3779B97F4A7C15ull);
        h ^= h >> 33, h *= 0xff51afd7ed558ccdull, h ^= h >> 33, h *= 0xc4ceb9fe1a85ec53ull, h ^= h >> 33;
        double u = static_cast<double>(h >> 11) / 9007199254740992.0 * total;
        for (std::size_t i = 0; i < sizeof(score) / sizeof(score[0]); ++i) {
            if (fm::comps[i].n != picks) continue;
            u -= std::exp(score[i] - best);
            if (u <= 0) { arg = static_cast<int>(i); break; }
        }
    }
    const auto& c = fm::comps[static_cast<std::size_t>(arg)];
    debug_block({ std::printf("FMTEAM %d %d\\n", arg, picks); });
    return new std::vector<cambc::champion_draft>(c.picks, c.picks + c.n);
}
''', 1)
assert s.count('fm_forced') >= 3
f.write_text(s); print('patched', f)
