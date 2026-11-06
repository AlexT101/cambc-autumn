"""mkvar.py NAME key=val ...: bots/variants/oc-kill-NAME = oc-kill-dev with params::kill:: knobs set."""
import re, subprocess, sys
R = '/home/ubuntu/cambc-autumn'
name, sets = sys.argv[1], sys.argv[2:]
dst = f'variants/oc-kill-{name}'
subprocess.run([f'{R}/copybot', '-f', 'variants/oc-kill-dev', dst], cwd=R, check=True, stdout=subprocess.DEVNULL)
p = f'{R}/bots/{dst}/src/params.h'
s = open(p).read()
head, tail = s.split('namespace kill {', 1)
body, rest = tail.split('} // namespace kill', 1)
for kv in sets:
    k, v = kv.split('=')
    body, n = re.subn(rf'(inline constexpr \w+ {k} = )[^;]+;', rf'\g<1>{v};', body)
    assert n == 1, kv
open(p, 'w').write(head + 'namespace kill {' + body + '} // namespace kill' + rest)
print(dst, ' '.join(sets))
