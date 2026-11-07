"""Compile the candidate's actual bit-packing code against scalar bit oracles.

Usage: python3 research/hyperion/fuel-campaign-13/check_windows.py [bots/ocean]
Requires a C++20 compiler; writes only to a temporary directory.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

bot = Path(sys.argv[1] if len(sys.argv) > 1 else 'bots/ocean')
header = (bot / 'src/model/safety.h').read_text()
window = header[header.index('    struct Window {'):header.index('\nprivate:', header.index('    struct Window {'))]
safety = (bot / 'src/model/safety.cc').read_text()
start = safety.index('    Reach::Window chunk_window(')
chunk = safety[start:safety.index('\n};', start)]
plan = (bot / 'src/combat/plan.cc').read_text()
start = plan.index('        static_assert(grid_n == 7 && view_n == 9);')
end = plan.index('\n        return g |', start)
grid = plan[start:end].replace('        auto w = viewer_window(p, r);\n', '').replace('        const int dx = p.x - here.x, dy = p.y - here.y;\n', '')
source = r'''
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>
struct vec2 { int x,y; };
struct Reach {
''' + window + r'''
};
using Window = Reach::Window;
using Grid = std::uint64_t;
constexpr int win_r=4, win_n=9, grid_n=7, view_n=9;
struct Tables { std::array<std::array<Window,9>,9> columns{},rows{}; };
const Tables tables = [] {
    Tables t;
    for(int a=0;a<9;++a) for(int b=a;b<9;++b)
        for(int y=0;y<9;++y) for(int x=0;x<9;++x) {
            if(a<=x && x<=b) t.columns[a][b] |= Window::bit(9*y+x);
            if(a<=y && y<=b) t.rows[a][b] |= Window::bit(9*y+x);
        }
    return t;
}();
struct Terrain { int width,height,across;
''' + chunk + r'''
};
Grid viewer_grid(Window w, int dx,int dy) {
''' + grid + r'''
    return g;
}
bool bit(Window w,int i) { return (i<64 ? w.lo>>i : w.hi>>(i-64))&1; }
int main() {
    std::mt19937_64 rng(934141);
    int chunks=0, grids=0;
    for(int W=1;W<=100;++W) for(int H : {1,7,8,9,31,64,99,100}) {
        Terrain t{W,H,(W+7)/8};
        std::vector<std::uint64_t> data(t.across*((H+7)/8));
        for(auto& v:data) v=rng(); // deliberately include garbage in edge padding
        for(int trial=0;trial<100;++trial) {
            vec2 p{int(rng()%W),int(rng()%H)};
            Window actual=t.chunk_window(data.data(),p);
            for(int y=0;y<9;++y) for(int x=0;x<9;++x) {
                int xx=p.x-4+x, yy=p.y-4+y;
                bool expect=xx>=0 && yy>=0 && xx<W && yy<H && (data[(yy/8)*t.across+xx/8]>>(8*(yy%8)+xx%8)&1);
                if(bit(actual,9*y+x)!=expect) { std::printf("chunk mismatch %d %d %d %d\n",W,H,p.x,p.y);return 1; }
            }
            ++chunks;
        }
    }
    for(int dx=-8;dx<=8;++dx) for(int dy=-8;dy<=8;++dy) for(int trial=0;trial<200;++trial) {
        Window w{rng(),rng()&Window::hi_mask};
        Grid actual=viewer_grid(w,dx,dy),expect=0;
        for(int y=0;y<7;++y) for(int x=0;x<7;++x) {
            int xx=x+1-dx, yy=y+1-dy;
            if(xx>=0 && yy>=0 && xx<9 && yy<9 && bit(w,9*yy+xx)) expect|=Grid{1}<<(7*y+x);
        }
        if(actual!=expect) { std::printf("grid mismatch %d %d\n",dx,dy);return 1; }
        ++grids;
    }
    std::printf("%d chunk windows and %d viewer grids match scalar oracles\n",chunks,grids);
}
'''
with tempfile.TemporaryDirectory(prefix='fc13-windows-') as tmp:
    src, exe = Path(tmp)/'check.cc', Path(tmp)/'check'
    src.write_text(source)
    subprocess.run([os.environ.get('CXX', 'clang++'), '-std=c++20', '-O2', '-fsanitize=undefined', str(src), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
