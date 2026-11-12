"""Decode Mite's priority value into (state, arg, k, fl). From 11-11 values are base << 10 | k << 7 | fl (k = slot),
or small k << 7 | fl with base 0; older plain bases persist."""
def split(v):
    if v >= 92160: return v >> 10, (v >> 7) & 7, v & 127, 'shift'
    if v < 768 and not (90 <= v <= 100) and v != 50: return 0, v >> 7, v & 127, 'small'
    return v, None, None, 'plain'
def state(b):
    if b == 0: return 'zero', None
    if 1000 <= b <= 1024: return 'quiet', b - 1000
    if 1025 <= b <= 1049: return 'quietT', b - 1025
    if b == 1050: return 'dead', None
    if b == 18965: return 'chan', None
    if 90 <= b <= 100: return 'contact', 100 - b
    if 2090 <= b <= 2100: return 'retreat', 2100 - b
    if 3090 <= b <= 3100: return 'kill', 3100 - b
    if 5090 <= b <= 5100: return 'retkill', 5100 - b
    if b in (50, 4050, 21262, 21158): return 'c%d' % b, None
    if 6450 <= b <= 9500: return 'off%d' % (b // 100 * 100), b % 100
    return 'other', b
def decode(v):
    b, k, fl, form = split(v)
    s, arg = state(b)
    return s, arg, k, fl, form
