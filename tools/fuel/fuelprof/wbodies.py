def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7f) << s; s += 7
        if x < 0x80: return r, i
def bodies(path):
    b = open(path, 'rb').read(); i = 8; out = []; code_start = None
    while i < len(b):
        sid = b[i]; i += 1; size, i = leb(b, i); end = i + size
        if sid == 10:
            code_start = i; n, j = leb(b, i)
            for _ in range(n):
                sz, j = leb(b, j); out.append((j, j + sz)); j += sz
        i = end
    return b, code_start, out
