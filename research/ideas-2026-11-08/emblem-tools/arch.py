"""Archive days as numpy column dicts: S per side (2 rows a game), U per unit, with side-level fields joined."""
import numpy as np, json, os
A = os.path.expanduser('~/tmp-offload/emblem/archive/')
FAM = ['Monster','Power','Durability','Treasure','Jungle','Home','Bruiser','Tribute','Capture','Prospector','Hunter','Skirmish','Greed','Collectors']
CP = [50,100,150,200,250,300,350,400,500,600,800,1000,1200,1400,1600,1800,2000]
def day(d):
    p = A + d + '/'; m = json.load(open(p + 'meta.json')); names = np.array([t['name'] for t in m['teams']] + ['?'])
    L = lambda f: np.load(p + f + '.npy')
    win = L('g_winner'); rating = L('g_rating'); st = L('s_team'); G = len(win)
    gi = np.repeat(np.arange(G), 2); side = np.tile([0, 1], G)
    S = dict(g=gi, side=side, team=names[st], opp=names[st.reshape(-1, 2)[:, ::-1].ravel()], win=(win[gi] == side).astype(int),
             rating=rating[gi, side], orating=rating[gi, 1 - side], rounds=L('g_rounds')[gi], kind=L('g_kind')[gi], map=L('g_map_hash')[gi],
             gold=L('s_gold'), gems=L('s_gems'))
    S['ogold'] = S['gold'].reshape(G, 2, -1)[:, ::-1].reshape(2 * G, -1)
    ug = L('u_game'); us = L('u_side'); row = 2 * ug + us
    U = dict(row=row, g=ug, side=us, type=np.array(m['champions'])[L('u_type')], pick=L('u_pick'), earned=L('u_earned'), spent=L('u_spent'),
             unspent=L('u_unspent'), kills=L('u_kills'), deaths=L('u_deaths'), nemb=L('u_emblems'),
             e=np.stack([L(f'u_emblem_{k}') for k in range(1, 13)], 1), r=np.stack([L(f'u_emblem_round_{k}') for k in range(1, 13)], 1))
    for k in ('team', 'opp', 'win', 'rating', 'orating', 'rounds'): U[k] = S[k][row]
    return S, U, m
def fam(e): return 'none' if e == 255 else FAM[e // 6] + '-' + 'SFH'[(e % 6) // 2]
