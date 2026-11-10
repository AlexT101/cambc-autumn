from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model/safety.cc'
s=p.read_text();a=s.index('Blow Reach::at(');b=s.index('Blow Threat::at',a);t=s[a:b]
t=t.replace('Window from = tiles_[w.from] & box(dx + win_r, dy + win_r, w.range);', '''Window from = ws.stationary ? (d <= w.range ? win_bit(win_r, win_r) : Window{})
                                        : tiles_[w.from] & box(dx + win_r, dy + win_r, w.range);''')
s=s[:a]+t+s[b:];p.write_text(s)
