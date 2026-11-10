from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model';h=(p/'safety.h').read_text();h=h.replace('    int reach() const; // Chebyshev', '    bool geometry_ready() const { return geometry_ready_; }\n    int reach() const; // Chebyshev');h=h.replace('    void set_bounds();','''    void set_bounds();
    void build_geometry();
    const ChampionBelief* enemy_ = nullptr;
    int turn_round_ = 0;
    bool geometry_ready_ = false, dash_ = false;''');(p/'safety.h').write_text(h)
s=(p/'safety.cc').read_text();a=s.index('void Reach::build(');b=s.index('void Reach::set_bounds()',a);t=s[a:b]
key='    // Our champions around it,';i=t.index(key)
start=t[:i];geometry=t[i:]
stationary='ways_->stationary' in start
if stationary:
    start=start[:start.index('    splash_ =')]

geometry=geometry.replace('        build_ways(e, ready, ready2, twice);\n','').replace('    build_ways(e, ready, ready2, twice);\n','')
start+='''    enemy_ = &e;
    turn_round_ = turn_round;
    dash_ = dash;
    geometry_ready_ = false;
    build_ways(e, ready, ready2, twice);
}

void Reach::build_geometry() {
    geometry_ready_ = true;
    const auto& world = *world_;
    const auto& e = *enemy_;
    const auto& f = e.facts();
    const int turn_round = turn_round_;
    const bool twice = twice_, dash = dash_;
'''
if stationary:
    start+='''    splash_ = f.passive == Passive::splash_attack;
    const int sets_radius = splash_ ? win_r : (twice ? 1 : 0) + (dash ? (f.ranged ? 2 : 3) : 1);
    if (ways_->stationary && !splash_) {
        tiles_[here] = win_bit(win_r, win_r);
        extent_[here] = 0;
        set_bounds();
        return;
    }
'''
s=s[:a]+start+geometry+s[b:]
s=s.replace('int Reach::reach() const {','int Reach::reach() const {\n    if (!geometry_ready_) const_cast<Reach*>(this)->build_geometry();')
s=s.replace('        int ward = -1;\n        const auto seen', '        if (!geometry_ready_) const_cast<Reach*>(this)->build_geometry();\n        int ward = -1;\n        const auto seen')
s=s.replace('(r.reach() > s.reach || b.damage', '((r.geometry_ready() && r.reach() > s.reach) || b.damage')
(p/'safety.cc').write_text(s)
