"""The live priority mask's per-game seed (tools/livemask/prio_stream.h, setup() and make()), from a game's facts.
Reads the key file; never prints the key or a seed."""
from pathlib import Path

M64 = (1 << 64) - 1
KEY_FILE = Path(__file__).resolve().parents[3] / 'tools/livemask/livemask.key'
GOLD = 0x9e3779b97f4a7c15


def mix(z):
    z = ((z ^ (z >> 30)) * 0xbf58476d1ce4e5b9) & M64
    z = ((z ^ (z >> 27)) * 0x94d049bb133111eb) & M64
    return z ^ (z >> 31)


def load_key(path=KEY_FILE):
    kb = Path(path).read_bytes()
    assert len(kb) >= 16
    return int.from_bytes(kb[:8], 'little'), int.from_bytes(kb[8:16], 'little')


def body_types(picks):
    """champion_type of each body, in id order, from champion_draft picks (Cassi and Issac are draft 3, types 3 and 4)."""
    out = []
    for p in picks:
        out += [p] if p < 3 else [3, 4] if p == 3 else [p + 1]
    return out


def mirror(sym, w, h, x, y):
    if sym == 'horizontal': return w - 1 - x, y
    if sym == 'vertical': return x, h - 1 - y
    return w - 1 - x, h - 1 - y


def spawn_centre(facts, team_a, inclusive=False):
    """World's central_tile of the ally spawn: a filled box's tile at the floored mean."""
    s = facts['spawnA']
    x0, y0, x1, y1 = s['minX'], s['minY'], s['maxX'] - (0 if inclusive else 1), s['maxY'] - (0 if inclusive else 1)
    if not team_a:
        ax, ay = mirror(facts['symmetry'], facts['width'], facts['height'], x0, y0)
        bx, by = mirror(facts['symmetry'], facts['width'], facts['height'], x1, y1)
        x0, x1, y0, y1 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)
    return (x0 + x1) // 2, (y0 + y1) // 2


def game_seed(key, facts, team_a, picks, groups=None, inclusive=False):
    cx, cy = spawn_centre(facts, team_a, inclusive)
    g = facts['groups'] if groups is None else groups
    pk = 0x5a if team_a else 0xa5
    for t in body_types(picks):
        pk = (pk * 0x100000001b3 + t + 1) & M64
    place = (facts['width'] << 48) ^ (facts['height'] << 32) ^ (g << 16) ^ (cx * 256 + cy)
    return mix((mix(place ^ key[1]) ^ pk) ^ key[0])


class Mask:
    """Champion `index`'s 14-bit payload mask in round w, and the round's 2-bit tag."""
    def __init__(self, seed):
        self.seed = seed
        self.tag = mix(seed ^ 0x7a6) & 3
        self.w, self.m = None, 0

    def tag_of(self, w):
        return (w + self.tag) & 3

    def mask_of(self, w, index):
        if self.w != w:
            self.w, self.m = w, mix(self.seed ^ ((w * GOLD) & M64))
        return (self.m >> ((index & 7) * 7)) & 0x3fff
