"""Would the book start on a map it has no game for? Counts, over maps the book was not made from, how far each
gets through the bot's entry match (book.cc start(): side and size, tile counts, terrain id, camp layout).

    node mapids.mjs --full MAP... > IDS.json   (per map: id, layout, w, h, counts)
    py freshcheck.py WORK/book.jsonl IDS.json...
A map equal to an entry in terrain and camp layout would play the entry's game if the picks matched too."""
import json, sys


def main():
    ents = [json.loads(l) for l in open(sys.argv[1])]
    side = lambda e: 0 if e['side'] == 'a' else 1
    sizes = {(side(e), e['width'], e['height']) for e in ents}
    counts = {(side(e), e['width'], e['height'], tuple(e['counts'])) for e in ents}
    ids = {e['map_id'] for e in ents}
    lay = {(e['map_id'], e['layout']): e['key'] for e in ents}
    maps = {}
    for f in sys.argv[2:]:
        maps.update(json.load(open(f)))
    sz = cnt = idm = 0
    same = []
    for f, m in maps.items():
        for s in (0, 1):
            sz += (s, m['w'], m['h']) in sizes
            cnt += (s, m['w'], m['h'], tuple(m['counts'])) in counts
        idm += m['id'] in ids
        if (m['id'], m['layout']) in lay:
            same.append((f, lay[(m['id'], m['layout'])]))
    n = len(maps)
    print(f'{len(ents)} entries; {n} maps ({2 * n} map-sides): size listed {sz} ({100 * sz / (2 * n):.1f}%), tile counts equal {cnt}, '
          f'terrain equal {idm} maps, terrain and camp layout equal {len(same)}')
    for f, k in same:
        print('  SAME', f, k)


if __name__ == '__main__':
    main()
