import os, re
s = open('params.h').read()
for k in os.environ['KNOBS'].split(','):
    old = f"inline constexpr bool {k} = true;"
    assert s.count(old) == 1, k
    s = s.replace(old, f"inline constexpr bool {k} = false;")
open('params.h', 'w').write(s)
