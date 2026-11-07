# modes.cc's per-game draw: levels[state][knob] in {-1,0,1} from (W, H, walls, altar sum, team A).
M = (1 << 64) - 1
def mix(z):
    z = (z + 0x9E3779B97F4A7C15) & M
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
    return z ^ (z >> 31)
def levels(k, team_a, S=5, K=4):
    key = mix(mix(mix(k['W'] * 1000 + k['H']) ^ k['walls']) ^ k['altars']) ^ (0x5151 if team_a else 0xA2A2)
    return [[mix(key ^ (s * 16 + kk + 1)) % 3 - 1 for kk in range(K)] for s in range(S)]
if __name__ == '__main__':
    import json, sys
    keys = {k['map']: k for k in json.load(open(sys.argv[1]))}
    for m in sys.argv[2:]:
        print(m, 'A', levels(keys[m], True)); print(m, 'B', levels(keys[m], False))
