// Native driver for astraeus's map_features.cc (tools/draftlab/native.mjs builds and feeds it).
// stdin, per map:  MAP W H sym sx sy sw sh picks camps / W*H tile digits (row-major) / camps lines "type x y".
// stdout, per map: FEAT key v1..v19 / TEAM key picks names (comma-separated, pick order).
#include <cstdio>
#include <string>
#include "../../bots/astraeus/src/draft_model.h"
#include "../../bots/astraeus/src/map_features.cc"

int main() {
    using namespace aph::mapfeat;
    char tag[8];
    while (std::scanf("%7s", tag) == 1) {
        Input in;
        int picks = 0, camps = 0;
        if (std::scanf("%d %d %d %d %d %d %d %d %d", &in.W, &in.H, &in.sym, &in.sx, &in.sy, &in.sw, &in.sh, &picks, &camps) != 9) return 1;
        std::string tiles(static_cast<std::size_t>(in.W * in.H), '0');
        if (std::scanf("%s", tiles.data()) != 1) return 1;
        for (const char c : tiles) in.t.push_back(static_cast<std::uint8_t>(c - '0'));
        for (int i = 0; i < camps; ++i) {
            Camp c{};
            if (std::scanf("%d %d %d", &c.type, &c.x, &c.y) != 3) return 1;
            in.camps.push_back(c);
        }
        const auto key = static_cast<unsigned long long>(map_key(in));
        try {
            const auto raw = compute(in);
            std::printf("FEAT %016llx", key);
            for (const double v : raw) std::printf(" %.17g", v);
            const auto team = model_team(raw, picks);
            std::printf("\nTEAM %016llx %d ", key, picks);
            for (std::size_t i = 0; i < team.size(); ++i) std::printf("%s%s", i ? "," : "", aph::draft_model::champion_names[team[i]]);
            std::printf("%s\n", team.empty() ? "-" : "");
        } catch (const std::exception& e) {
            std::printf("FAIL %016llx %s\n", key, e.what());
        }
        std::fflush(stdout);
    }
    return 0;
}
