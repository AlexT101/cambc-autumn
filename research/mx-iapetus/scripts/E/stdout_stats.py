# Debug A/B batch: CAND's relay/watch traces. Usage: stdout_stats.py BATCH_DIR
import zipfile,sys,os,re,collections
from multiprocessing import Pool
B=sys.argv[1]
def one(f):
    c=collections.Counter()
    side='a' if re.search(r'-12\.repl26a$',f) else 'b'
    try: z=zipfile.ZipFile(os.path.join(B,f)); out=z.read(f'team-{side}.stdout').decode(errors='replace')
    except Exception: return c
    c['games']+=1
    lay=set()
    for l in out.splitlines():
        if l.startswith('LAYOUT'):
            if l not in lay: lay.add(l); c['layout']+=1; c['tribute_fits']+=' tribute 1' in l; c['tiles8']+=' tiles 8' in l and ' tribute 1' in l; c['ally_on']+=' ally 1' in l
        elif l.startswith('RELAY-POST'): c['post']+=1; c['post_cancel']+=l.endswith('class 0'); c['post_win']+=l.endswith('class 7')
        elif l.startswith('RELAY-READ'): c['read']+=1
        elif l.startswith('STOP-ENDER'):
            c['stop']+=1; c['stop_unseen']+=' unseen ' in l; c['stop_relayed']+=(' unseen ' in l and ' relayed -1 ' not in l)
        elif l.startswith('WARD '): c['ward']+=1; c['ward_watch']+=l.endswith('watch')
        elif l.startswith('D '):
            p=l.split()
            if len(p)>3: c['dec_'+p[3]]+=1
        elif l.startswith('OOF'): c['oof']+=1
    return c
if __name__=='__main__':
    fs=sorted(f for f in os.listdir(B) if f.endswith('.repl26a'))
    t=collections.Counter()
    with Pool(32) as p:
        for c in p.imap_unordered(one,fs): t.update(c)
    g=t['games']
    for k in sorted(t): print(k,t[k],'%.2f/game'%(t[k]/max(1,g)))
