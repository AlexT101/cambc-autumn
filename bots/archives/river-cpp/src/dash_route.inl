// Function bodies; src/unity.cpp includes this after every header.

namespace aph::dash_route {
bool Board::in(vec2 p) const
{ return p.x >= 0 && p.y >= 0 && p.x < w && p.y < h; }

int Board::at(vec2 p) const
{ return p.y * w + p.x; }

vec2 Board::tile(int i) const
{ return {i % w, i / w}; }

bool Board::standable(vec2 p) const
{ return in(p) && stand[at(p)]; }

void Board::read(const bitboard& stand_b, const bitboard& cross_b, const bitboard& goals_b)
{
        const auto& layout = cambc::detail::layout();
        w = layout.width, h = layout.height;
        stand.assign(static_cast<std::size_t>(w * h), 0);
        cross.assign(stand.size(), 0);
        goal.assign(stand.size(), 0);
        const auto bit = [&](const bitboard& b, int x, int y) {
            return (b.ptr()[(y >> 3) * layout.chunk_stride + (x >> 3)] >> (((y & 7) << 3) | (x & 7))) & 1;
        };
        for (int y = 0; y < h; ++y)
            for (int x = 0; x < w; ++x) {
                const int i = y * w + x;
                stand[i] = static_cast<std::uint8_t>(bit(stand_b, x, y));
                cross[i] = static_cast<std::uint8_t>(bit(cross_b, x, y) | stand[i]);
                goal[i] = static_cast<std::uint8_t>(bit(goals_b, x, y) & stand[i]);
            }
    }

std::uint16_t Exact::value(vec2 p, int c) const
{ return b->in(p) ? v[static_cast<std::size_t>(b->at(p) * phases + c)] : never; }

void Exact::solve(const Board& board, bool dashes)
{
        b = &board, dasher = dashes;
        const int n = board.w * board.h;
        v.assign(static_cast<std::size_t>(n * phases), never);
        std::vector<std::uint32_t> queue;
        queue.reserve(static_cast<std::size_t>(n * phases));
        const auto label = [&](vec2 p, int c, std::uint16_t value) {
            auto& slot = v[static_cast<std::size_t>(board.at(p) * phases + c)];
            if (slot != never) return;
            slot = value;
            queue.push_back(static_cast<std::uint32_t>(board.at(p) * phases + c));
        };
        for (int i = 0; i < n; ++i)
            if (board.goal[i])
                for (int c = 0; c < phases; ++c) label(board.tile(i), c, 0);
        for (std::size_t head = 0; head < queue.size(); ++head) {
            const int s = static_cast<int>(queue[head]);
            const vec2 p = board.tile(s / phases);
            const int c = s % phases;
            const auto next = static_cast<std::uint16_t>(v[static_cast<std::size_t>(s)] + 1);
            // Without a dash: from cooldown c + 1, or 0 to 0.
            for (const int from : {c + 1, c == 0 ? 0 : -1}) {
                if (from < 0 || from >= phases) continue;
                label(p, from, next);
                board.walks(p, [&](vec2 q) { label(q, from, next); });
            }
            if (!dasher || c != phases - 1) continue;
            // With one, from cooldown 0: a dash, a walk then a dash, or a dash then a walk.
            board.dashes(p, [&](vec2 l) {
                label(l, 0, next);
                board.walks(l, [&](vec2 q) { label(q, 0, next); });
            });
            board.walks(p, [&](vec2 q) { board.dashes(q, [&](vec2 l) { label(l, 0, next); }); });
        }
    }

Move ExactPolicy::decide(vec2 p, int c) const
{
        Move best;
        int best_v = e.value(p, c);
        e.b->turns(p, c, e.dasher, [&](vec2 q, bool dashed) {
            const int v = e.value(q, after(c, dashed));
            if (v < best_v) best_v = v, best = {q, dashed};
        });
        return best;
    }

int RoutedPolicy::beyond(vec2 p) const
{
        if (fc[b.at(p)] == never || (fw[b.at(p)] != never && fc[b.at(p)] >= fw[b.at(p)])) return -1;
        vec2 q = p;
        for (int a = 0; a <= reach; ++a) {
            const int here = fc[b.at(q)];
            if (here == 0) return -1;
            vec2 next{-1, -1};
            for (const auto d : steps8) {
                const vec2 x = q + d;
                if (!b.in(x) || fc[b.at(x)] != here - 1) continue;
                if (crossing[b.at(x)]) return here - 2;
                if (next.x < 0 && b.stand[b.at(x)]) next = x;
            }
            if (next.x < 0) return -1;
            q = next;
        }
        return -2;
    }

Move RoutedPolicy::decide(vec2 p, int c) const
{
        const int rest = beyond(p);
        const auto score = [&](vec2 q, int cq) {
            const int i = b.at(q);
            int v = fw[i] == never ? 1 << 20 : paced(fw[i], cq);
            if (rest == -2 && fc[i] != never) v = std::min(v, paced(fc[i], cq));
            if (rest >= 0 && fc[i] != never) {
                const int a = fc[i] - 2 - rest;
                v = std::min(v, a < 0 ? paced(fc[i], cq) : crossing_turns(a, rest, cq));
            }
            return v >= (1 << 20) ? 1 << 30 : v * 4096 + (fc[i] == never ? 4095 : fc[i]);
        };
        Move best;
        int best_s = 1 << 30;
        const auto consider = [&](vec2 q, bool dashed) {
            if (q == p && c == 0 && !dashed) return;
            const int s = score(q, after(c, dashed));
            if (s < best_s || (s == best_s && !dashed && best.dashed)) best_s = s, best = {q, dashed};
        };
        if (ends == 0) {
            b.turns(p, c, true, consider);
            return best;
        }
        consider(p, false);
        b.walks(p, [&](vec2 q) { consider(q, false); });
        const vec2 step = best.end;
        if (c != 0) return best;
        b.dashes(p, [&](vec2 l) {
            consider(l, true);
            b.walks(l, [&](vec2 q) { consider(q, true); });
        });
        if (ends == 2 && step.x >= 0 && step != p) b.dashes(step, [&](vec2 l) { consider(l, true); });
        return best;
    }

Move TreePolicy::decide(vec2 p, int c) const
{
        const Board& b = routed.b;
        const auto field = [](std::uint16_t v) { return v == never ? -1 : static_cast<int>(v); };
        const int rest = routed.beyond(p), h = b.at(p);
        Move best;
        std::int64_t best_s = std::int64_t{1} << 40;
        b.turns(p, c, true, [&](vec2 q, bool dashed) {
            if (q == p && c == 0 && !dashed) return;
            const int i = b.at(q), ca = after(c, dashed);
            const auto f = tree_features(field(routed.fw[h]), field(routed.fc[h]), c, rest, field(fx[h]), field(routed.fw[i]), field(routed.fc[i]), ca,
                                         dashed, dist(p, q), field(fx[i]));
            const std::int64_t s = std::int64_t{tree_turns(f)} * 4096 + (routed.fc[i] == never ? 4095 : routed.fc[i]);
            if (s < best_s || (s == best_s && !dashed && best.dashed)) best_s = s, best = {q, dashed};
        });
        return best;
    }

void Router::prepare(const bitboard& goals, const bitboard& walls, const bitboard& no_dash, const bitboard* crossings, vec2 me, int cap)
{
        static bitboard open{cambc::uninitialized};
        walls_ = &walls, no_dash_ = &no_dash, crossings_ = crossings, me_ = me;
        layers_ = static_cast<std::uint16_t>(std::min(cap, static_cast<int>(unreachable)));
        const bool same = kept_ && crossed_ == (crossings != nullptr) && layers_ == kept_layers_ && boards_equal(goals, goals_)
                          && boards_equal(walls, kept_walls_) && steps_at(fc_, me) != unreachable;
        crossed_ = crossings != nullptr;
        if (same) return;
        trace_n_ = 0, fw_ready_ = !crossed_, kept_ = true, kept_layers_ = layers_;
        copy_into(goals, goals_);
        copy_into(walls, kept_walls_);
        if (crossed_) {
            copy_into(walls, open);
            drop(open, *crossings);
        }
        search(crossed_ ? open : walls, fc_);
    }

int Router::fc(vec2 p) const
{ return in_bounds(p) ? field(steps_at(fc_, p)) : -1; }

int Router::fw(vec2 p) const
{
        if (!in_bounds(p)) return -1;
        if (!crossed_) return fc(p);
        if (!fw_ready_) search(kept_walls_, fw_), fw_ready_ = true;
        return field(steps_at(fw_, p));
    }

int Router::beyond(vec2 p, int reach) const
{
        if (!crossed_) return -1;
        for (int k = 0; k < trace_n_; ++k)
            if (trace_[k] == p) return trace_rest_;
        int here = fc(p);
        if (here < 0) return -1;
        if (!any_within(*crossings_, p, reach + 1)) return -2;
        trace_n_ = 0;
        vec2 q = p;
        int last = 0; // the direction last stepped: tried first
        for (int a = 0; a <= reach; ++a) {
            if (here == 0) return trace_n_ = 0, -1;
            if (trace_n_ < static_cast<int>(trace_.size())) trace_[trace_n_++] = q;
            if (test(*near_crossings_, q))
                for (const auto d : steps8) {
                    const vec2 x = q + d;
                    if (in_bounds(x) && test(*crossings_, x) && fc(x) == here - 1) return trace_rest_ = here - 2;
                }
            int next = -1;
            for (int k = 0; k < 8 && next < 0; ++k) {
                const int d = (last + k) & 7;
                const vec2 x = q + steps8[d];
                if (in_bounds(x) && fc(x) == here - 1 && !test(*crossings_, x)) next = d;
            }
            if (next < 0) return trace_n_ = 0, -1;
            q = q + steps8[next], last = next, --here;
        }
        trace_n_ = 0;
        return -2;
    }

int Router::turns_from(vec2 q, int rest, int ca) const
{
        const int f = fc(q);
        if (rest < 0) return f < 0 ? no_estimate : paced(f, ca);
        return estimate(fw(q), f, rest, ca);
    }

bool Router::lands(vec2 from, vec2 l) const
{
        if (!in_bounds(l) || l == from || dist(from, l) > 2 || test(*walls_, l)) return false;
        if (dist(from, l) == 1) return true;
        for (int y = std::max(from.y, l.y) - 1; y <= std::min(from.y, l.y) + 1; ++y)
            for (int x = std::max(from.x, l.x) - 1; x <= std::min(from.x, l.x) + 1; ++x)
                if (const vec2 m{x, y}; m != from && m != l && in_bounds(m) && !test(*no_dash_, m)) return true;
        return false;
    }

auto Router::decide(vec2 p, int c, std::optional<vec2> aim, bool walk) const -> Plan
{
        const int rest = beyond(p, c + phases + 4);
        const auto nearest = [&](vec2 q) {
            const int f = fc(q);
            return f < 0 ? 1 << 29 : f;
        };
        Plan best;
        int best_fc = 1 << 30;
        const auto consider = [&](vec2 q, int ca, const Plan& plan) {
            if (q.x < 0) return;
            const int f = fc(q), t = turns_from(q, rest, ca), fq = f < 0 ? 1 << 29 : f;
            if (t < best.turns || (t == best.turns && fq < best_fc)) best = plan, best.turns = t, best_fc = fq;
        };
        // The nearest tile of a kind from `from`: equally near ones by the tiebreak, read only on a tie.
        struct Nearest {
            vec2 q{-1, -1};
            int f = 1 << 30, tie = -1;
        };
        // Takes q if it beats n and `allowed` (read only then) passes.
        const auto offer = [&](Nearest& n, vec2 from, vec2 q, int f, auto allowed) {
            if (f > n.f || f >= (1 << 29)) return;
            int t = -1;
            if (f == n.f && n.q.x >= 0) {
                if (n.tie < 0) n.tie = step_tiebreak(*map_, from, n.q, aim);
                if ((t = step_tiebreak(*map_, from, q, aim)) >= n.tie) return;
            }
            if (!allowed()) return;
            n.q = q, n.f = f, n.tie = t;
        };
        // The best landing from `from`, never `back`: done once one gains the whole 2.
        const auto best_landing = [&](vec2 from, vec2 toward, vec2 back) {
            Nearest n;
            const int floor = nearest(from) - 2;
            const vec2 d{toward.x - from.x, toward.y - from.y};
            for (const auto& o : landing_order(d)) {
                const vec2 l = from + o;
                if (!in_bounds(l)) continue;
                offer(n, from, l, nearest(l), [&] { return l != back && lands(from, l) && !skips_bush(*map_, from, l); });
                if (n.f <= floor && n.q.x >= 0) break;
            }
            return n;
        };
        const int here_fc = nearest(p);
        // The best step (every one read: the tiebreak picks among equals), or staying while the dash cools.
        Nearest steps;
        if (walk)
            for (const auto d : steps8)
                if (const vec2 q = p + d; in_bounds(q)) offer(steps, p, q, nearest(q), [&] { return !test(*walls_, q); });
        const vec2 step = steps.q;
        if (c > 0 || !walk) consider(p, std::max(0, c - 1), Plan{});
        {
            Plan plan;
            plan.walk = step;
            consider(step, std::max(0, c - 1), plan);
        }
        if (c != 0) return best;
        // The best landing, the best walk from it, and the best dash after the step.
        const auto lands_ = best_landing(p, step.x >= 0 ? step : p, p);
        const vec2 land = lands_.q;
        if (land.x < 0) return best;
        {
            Plan plan;
            plan.land = land;
            consider(land, phases - 1, plan);
        }
        Nearest afters;
        if (walk)
            for (const auto d : steps8) {
                const vec2 q = land + d;
                if (!in_bounds(q) || q == p) continue;
                offer(afters, land, q, nearest(q), [&] { return !test(*walls_, q); });
            }
        if (afters.q.x >= 0) {
            Plan plan;
            plan.land = land, plan.walk = afters.q;
            consider(afters.q, phases - 1, plan);
        }
        // A dash after the step reaches 3 nearer at best: only worth looking if the others did not.
        if (step.x >= 0 && std::min(lands_.f, afters.f) > here_fc - 3) {
            const auto jumps = best_landing(step, step + vec2{step.x - p.x, step.y - p.y}, p);
            if (jumps.q.x >= 0) {
                Plan plan;
                plan.walk = step, plan.land = jumps.q, plan.walk_first = true;
                consider(jumps.q, phases - 1, plan);
            }
        }
        return best;
    }

const std::array<vec2, 24>& Router::landing_order(vec2 d)
{
        static std::array<std::array<vec2, 24>, 9> orders = [] {
            std::array<std::array<vec2, 24>, 9> t{};
            for (int k = 0; k < 9; ++k) {
                const vec2 dir{k % 3 - 1, k / 3 - 1}, aim{2 * dir.x, 2 * dir.y};
                int n = 0;
                for (int y = -2; y <= 2; ++y)
                    for (int x = -2; x <= 2; ++x)
                        if (x != 0 || y != 0) t[k][n++] = {x, y};
                std::stable_sort(t[k].begin(), t[k].end(), [&](vec2 a, vec2 b) {
                    const int da = std::max(std::abs(a.x - aim.x), std::abs(a.y - aim.y)), db = std::max(std::abs(b.x - aim.x), std::abs(b.y - aim.y));
                    const int ra = std::max(std::abs(a.x), std::abs(a.y)), rb = std::max(std::abs(b.x), std::abs(b.y));
                    return da != db ? da < db : ra > rb;
                });
            }
            return t;
        }();
        return orders[static_cast<std::size_t>((std::clamp(d.y, -1, 1) + 1) * 3 + std::clamp(d.x, -1, 1) + 1)];
    }

void Router::set_map(const StaticMap* map)
{ map_ = map, near_crossings_ = &map->near_crossable; }

int Router::field(int v)
{ return v == unreachable ? -1 : v; }

void Router::search(const bitboard& walls, cambc::distance_field& f) const
{
        static bitboard origin, visited{cambc::uninitialized};
        clear_board(origin);
        set_tile(origin, me_);
        f.compute_to_with_expansion_count(walls, goals_, origin, visited, layers_);
    }

Move RouterPolicy::decide(vec2 p, int c) const
{
        const auto plan = router.decide(p, c);
        if (plan.turns >= no_estimate) return {};
        const vec2 end = plan.walk_first ? plan.land : plan.walk.x >= 0 ? plan.walk : plan.land.x >= 0 ? plan.land : p;
        return {end, plan.land.x >= 0};
    }

Move TheirPolicy::descend(vec2 p, const std::vector<std::uint16_t>& f, bool dashed) const
{
        Move best{p, dashed};
        int best_f = f[b.at(p)];
        b.walks(p, [&](vec2 q) {
            if (f[b.at(q)] < best_f) best_f = f[b.at(q)], best = {q, dashed};
        });
        return best;
    }

Move TheirPolicy::decide(vec2 p, int c) const
{
        if (c != 0) return descend(p, walk, false);
        constexpr int R = 3, N = 2 * R + 1;
        std::array<int, N * N> to_go;
        to_go.fill(1 << 30);
        const auto cell = [&](vec2 q) { return (q.y - p.y + R) * N + (q.x - p.x + R); };
        const auto inside = [&](vec2 q) { return std::abs(q.x - p.x) <= R && std::abs(q.y - p.y) <= R && b.in(q); };
        // Dijkstra by levels over the window, from the goals and the seeded rim.
        std::vector<std::pair<int, vec2>> heap;
        bool seeded = false;
        for (int dy = -R; dy <= R; ++dy)
            for (int dx = -R; dx <= R; ++dx) {
                const vec2 q = p + vec2{dx, dy};
                if (!inside(q) || !b.stand[b.at(q)]) continue;
                int seed = 1 << 30;
                if (b.goal[b.at(q)]) seed = 0;
                else if ((std::abs(dx) == R || std::abs(dy) == R) && walk[b.at(q)] != never) seed = 2 * walk[b.at(q)];
                if (seed < (1 << 30)) to_go[cell(q)] = seed, heap.push_back({seed, q}), seeded = true;
            }
        if (!seeded) {
            if (open[b.at(p)] == never) return {p, false};
            // route_on with crossings open; a first step onto a crossing is dash_over.
            bool to_crossing = false;
            int best_f = open[b.at(p)];
            for (const auto d : steps8) {
                const vec2 q = p + d;
                if (b.in(q) && crossing[b.at(q)] && open[b.at(q)] < best_f) to_crossing = true;
            }
            if (to_crossing) {
                Move best;
                int best_at = open[b.at(p)] - 1;
                b.dashes(p, [&](vec2 l) {
                    if (open[b.at(l)] < best_at) best_at = open[b.at(l)], best = {l, true};
                });
                if (best.end.x >= 0) return best;
            }
            return descend(p, open, false);
        }
        const auto relax = [&](vec2 q, int cost) {
            if (!inside(q) || !b.stand[b.at(q)] || cost >= to_go[cell(q)]) return;
            to_go[cell(q)] = cost;
            heap.push_back({cost, q});
        };
        while (!heap.empty()) {
            auto it = std::min_element(heap.begin(), heap.end(), [](const auto& x, const auto& y) { return x.first < y.first; });
            const auto [cost, q] = *it;
            *it = heap.back();
            heap.pop_back();
            if (cost > to_go[cell(q)]) continue;
            b.walks(q, [&](vec2 r) { relax(r, cost + 2); });
            b.dashes(q, [&](vec2 r) { relax(r, cost + price); });
        }
        int step = 1 << 30, jump = 1 << 30;
        Move walk_move{p, false}, dash_move;
        b.walks(p, [&](vec2 q) {
            if (2 + to_go[cell(q)] < step) step = 2 + to_go[cell(q)], walk_move = {q, false};
        });
        b.dashes(p, [&](vec2 l) {
            if (price + to_go[cell(l)] < jump) jump = price + to_go[cell(l)], dash_move = {l, true};
        });
        if (jump < step) {
            if (!walk_after) return dash_move;
            Move m = descend(dash_move.end, walk, true);
            return m;
        }
        return step < (1 << 30) ? walk_move : Move{p, false};
    }

}
