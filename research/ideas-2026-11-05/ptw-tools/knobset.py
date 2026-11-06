import os, re
s = open('params.h').read()
for kv in os.environ['SET'].split(','):
    k, v = kv.split('=')
    s, n = re.subn(rf"(inline constexpr \w[\w ]* {k} = )[^;]+;", rf"\g<1>{v};", s)
    assert n == 1, k
open('params.h', 'w').write(s)
