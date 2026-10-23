// probe-fuel-b: never yields. The draft bot burns fuel forever without picking (tests the
// "random pick on fuel exhaustion" rule and the 10x-first-draft-turn budget); every champion
// then runs an infinite loop from its first play turn (tests whether the game keeps going and
// whether each round resumes the loop with a fresh budget).
// Run: cambc run probe-fuel probe-fuel-b --map corners --rounds 12 -o <dir>
// bot.cpp / draft.cpp from the template are unused.
#include <cambc.h>
#include <cstdint>
#include <iostream>
#include <string>

static std::uint64_t F() { return cambc::fuel_remaining(); }

int main() {
    const std::uint64_t f0 = F();
    const bool draft = cambc::is_draft();
    const std::string name = draft ? "draft" : cambc::to_string(cambc::self().champion_name());
    std::cout << "PROBE " << cambc::round_number() << " " << name << " main_entry fuel=" << f0 << '\n';
    if (!draft) {
        auto p = cambc::self().position();
        std::cout << "PROBE " << cambc::round_number() << " " << name << " pos=(" << p.x << "," << p.y << ")\n";
    }
#ifdef DRAFT_SCRIPT
    // Variant (probe-fuel-c / probe-fuel-d define DRAFT_SCRIPT): draft turn 1 picks
    // normally, draft turn 2 yields without picking (or picks prism if DRAFT_PICK2, probe-fuel-d), draft
    // turn 3+ falls through into the burn loop.
    if (draft) {
        for (int t = 1;; ++t) {
            const auto ally = cambc::draft::current_draft(cambc::team::ally);
            std::cout << "PROBE " << cambc::round_number() << " draft script_turn=" << t << " ally_picks=" << ally.size()
                      << " fuel=" << F() << '\n';
            if (t == 1) cambc::draft::pick(cambc::champion_draft::stellar);
#ifdef DRAFT_PICK2
            if (t == 2) cambc::draft::pick(cambc::champion_draft::prism);
#endif
#ifdef DRAFT_PICK3
            if (t == 3) cambc::draft::pick(cambc::champion_draft::vendetta);  // pick, then burn (probe-fuel-e)
#endif
            if (t >= 3) break;
            cambc::end_turn();
        }
    }
#endif
    std::uint32_t last_round = cambc::round_number();
    std::uint64_t prev_f = F(), max_seen = 0;
    std::uint32_t low_round = 0xFFFFFFFF;
    volatile std::uint64_t x = 0;
    // Infinite loop; report the first marker of each new round (budget refilled) and the
    // lowest fuel reading seen before each suspension.
    for (std::uint64_t i = 0;; ++i) {
        x = x * 6364136223846793005ULL + 1;
        if (i % 200 == 0) {
            const std::uint64_t f = F();
            const std::uint32_t r = cambc::round_number();
            if (r != last_round || f > prev_f) {
                std::cout << "PROBE " << r << " " << name << " resumed i=" << i << " fuel=" << f
                          << " last_fuel_before=" << prev_f << " prev_round=" << last_round;
                if (draft) std::cout << " ally_picks=" << cambc::draft::current_draft(cambc::team::ally).size();
#ifdef DRAFT_PICK3
                if (draft) { try { cambc::draft::pick(cambc::champion_draft::varg); std::cout << " picked_varg_after_resume=1"; } catch (const std::exception& e) { std::cout << " pick_err=[" << e.what() << "]"; } }
#endif
                std::cout << '\n' << std::flush;
                last_round = r;
            }
            if (f < 8000 && low_round != r) { low_round = r; std::cout << "PROBE " << r << " " << name << " near_empty i=" << i << " fuel=" << f << '\n' << std::flush; }
            prev_f = f;
            (void)max_seen;
        }
    }
}
