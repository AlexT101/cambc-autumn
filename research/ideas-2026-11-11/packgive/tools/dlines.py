# dlines.py OUT BATCH...: per replay, our bot's (the first bot's) decision and PG lines from its stdout.
import sys,zipfile,json,gzip,os,re
out=gzip.open(sys.argv[1],'wt')
for b in sys.argv[2:]:
    for f in sorted(os.listdir(b)):
        if not f.endswith('.repl26a'): continue
        side='a' if f.endswith('-12.repl26a') else 'b'
        try:
            z=zipfile.ZipFile(os.path.join(b,f)); txt=z.read('team-%s.stdout'%side).decode('utf8','replace')
        except Exception as e:
            print('skip',f,e); continue
        D=[l for l in txt.split('\n') if l.startswith('D ') or l.startswith('PG')]
        out.write(json.dumps(dict(batch=os.path.basename(b),file=f,side=side,lines=D))+'\n')
out.close()
