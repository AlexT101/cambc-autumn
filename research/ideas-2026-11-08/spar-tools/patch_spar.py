"""Patch an ocean-family bot dir so its draft plays a forced per-(map, side) pick order from src/draft/spar_draft.h
(keyed by draft.cc's map_hash, which includes our team), else its own draft; and print SPARHASH <hash> in draft
round 0 (local builds). Idempotent.   py patch_spar.py bots/variants/NAME"""
import sys, re
from pathlib import Path
bot = Path(sys.argv[1]); f = bot / 'src/draft/draft.cc'; s = f.read_text()
if 'spar_forced' in s: print('already patched'); sys.exit(0)
hdr = bot / 'src/draft/spar_draft.h'
if not hdr.exists():
    hdr.write_text('#pragma once\n#include <cstdint>\nnamespace spar {\nstruct Entry { std::uint64_t hash; int n; cambc::champion_draft picks[5]; };\n'
                   'inline constexpr Entry table[] = {{0, 0, {}}};\n}\n')
s = s.replace('#include "draft_model.h"\n', '#include "draft_model.h"\n#include "spar_draft.h"\n', 1)
# forward declaration in the first anonymous namespace
s = s.replace('const std::vector<cambc::champion_draft>* model_draft();\n',
              'const std::vector<cambc::champion_draft>* model_draft();\nconst std::vector<cambc::champion_draft>* spar_forced();\n', 1)
s = s.replace('bool vesper_allowed() {\n    return params::test_draft ||', 'bool vesper_allowed() {\n    return spar_forced() != nullptr || params::test_draft ||', 1)
s = s.replace('bool team_locked() {\n    return !params::test_draft;', 'bool team_locked() {\n    return !params::test_draft && spar_forced() == nullptr;', 1)
# definition after test_compositions
s = s.replace('} // namespace test_compositions\n', '''} // namespace test_compositions

// Spar opponents (research/ideas-2026-11-08/spar.md): a live opponent's exact picks for this map and side.
const std::vector<cambc::champion_draft>* spar_forced() {
    static const std::vector<cambc::champion_draft>* forced = [] () -> const std::vector<cambc::champion_draft>* {
        const auto h = test_compositions::map_hash();
        debug_block({ std::printf("SPARHASH %llu\\n", static_cast<unsigned long long>(h)); });
        for (const auto& e : spar::table)
            if (e.n && e.hash == h && e.n == static_cast<int>(cambc::draft::team_size()))
                return new std::vector<cambc::champion_draft>(e.picks, e.picks + e.n);
        return nullptr;
    }();
    return forced;
}
''', 1)
s = s.replace('std::vector<cambc::champion_draft> draft_order() {\n', 'std::vector<cambc::champion_draft> draft_order() {\n    if (const auto* f = spar_forced()) return *f;\n', 1)
s = s.replace('void play_draft(DraftState& state) {\n', 'void play_draft(DraftState& state) {\n    spar_forced();\n', 1)
assert s.count('spar_forced') >= 6, s.count('spar_forced')
f.write_text(s); print('patched', f)
