"""Apply draft6's lower-confidence-bound team rule (model.mjs lcbTeam) to a bot's src/draft/map_features.cc.
    python3 lcb_patch.py BOT_DIR
The header (model.mjs cpp, a lab config with "deploy") supplies kappa, draws, top and draw_models; the header must then carry draws > 0 (kappa > 0): its
draw arrays are named here, so a kappa-0 bot keeps the unpatched file."""
import sys
from pathlib import Path

f = Path(sys.argv[1]) / "src" / "draft" / "map_features.cc"
s = f.read_text()
if "lcb_pick" in s:
    sys.exit("already patched")


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:70]
    s = s.replace(old, new)


helper = '''// draft6 (model.mjs lcbTeam): the top `top` teams by the mean score, each re-scored as its mean score - kappa x the
// sd over the header's posterior draws of its score less the candidates' mean score in the same draw; the first best
// wins. Sums in lcbTeam's order, so the team matches the JS exactly.
struct LcbTeam {
    double s;
    std::int8_t ids[5];
};
inline std::vector<LcbTeam> lcb_all;
inline void lcb_pick(int picks, const double* z, int* best) {
    namespace m = draft_model;
    if constexpr (m::draws > 0) {
        const m::PickDraws* dm = nullptr;
        for (const auto& d : m::draw_models)
            if (d.picks == picks) dm = &d;
        if (!dm || lcb_all.empty()) return;
        std::stable_sort(lcb_all.begin(), lcb_all.end(), [](const LcbTeam& a, const LcbTeam& b) { return a.s > b.s; });
        const int n = std::min<int>(m::top, static_cast<int>(lcb_all.size()));
        static double S[m::top][m::draws];
        for (int d = 0; d < m::draws; ++d) {
            double v[m::champions];
            for (int c = 0; c < m::champions; ++c) {
                double x = dm->b[d][c];
                for (int k = 0; k < m::features; ++k) x += dm->w[d][c][k] * z[k];
                v[c] = x;
            }
            double mean = 0;
            for (int i = 0; i < n; ++i) {
                const auto* ids = lcb_all[static_cast<std::size_t>(i)].ids;
                double x = 0;
                for (int a = 0; a < picks; ++a) {
                    x += v[ids[a]];
                    for (int b = a + 1; b < picks; ++b) x += dm->syn[d][m::pair(ids[a], ids[b])];
                }
                S[i][d] = x;
                mean += x;
            }
            mean /= n;
            for (int i = 0; i < n; ++i) S[i][d] -= mean;
        }
        double bs = -std::numeric_limits<double>::infinity();
        int arg = 0;
        for (int i = 0; i < n; ++i) {
            double mu = 0;
            for (int d = 0; d < m::draws; ++d) mu += S[i][d];
            mu /= m::draws;
            double vv = 0;
            for (int d = 0; d < m::draws; ++d) {
                const double x = S[i][d] - mu;
                vv += x * x;
            }
            const double sc = lcb_all[static_cast<std::size_t>(i)].s - m::kappa * std::sqrt(vv / (m::draws - 1));
            if (sc > bs) bs = sc, arg = i;
        }
        for (int a = 0; a < picks; ++a) best[a] = lcb_all[static_cast<std::size_t>(arg)].ids[a];
    } else {
        (void)picks, (void)z, (void)best;
    }
}

std::vector<int> model_team('''
rep("std::vector<int> model_team(", helper)
rep("""                if ((mask & m::required) == m::required && !(mask & m::banned) && s > best_s) best_s = s, std::copy(cur, cur + P, best);
""", """                if ((mask & m::required) == m::required && !(mask & m::banned) && s > best_s) best_s = s, std::copy(cur, cur + P, best);
                if constexpr (m::draws > 0 && !m::counters) {
                    if ((mask & m::required) == m::required && !(mask & m::banned)) {
                        LcbTeam team{s, {}};
                        for (int i = 0; i < P; ++i) team.ids[i] = static_cast<std::int8_t>(cur[i]);
                        lcb_all.push_back(team);
                    }
                }
""")
rep("""        else rank.template operator()<5>();
""", """        else rank.template operator()<5>();
        if constexpr (m::draws > 0 && !m::counters) {
            lcb_pick(picks, z.data(), best);
            lcb_all.clear();
        }
""")
if "#include <limits>" not in s:
    s = s.replace("#include", "#include <limits>\n#include", 1)
f.write_text(s)
print(f"patched {f}")
