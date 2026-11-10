import pathlib,zipfile,re,collections,json,sys
r=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '/home/ubuntu/tmp-offload/livelock-goals/captrace')
yre=re.compile(r'LGY (\d+) (\d+) g(-?\d+) farm(-?\d+) claim(-?\d+) from(-?\d+),(-?\d+) to(-?\d+),(-?\d+)')
dre=re.compile(r'LGD (\d+) (\d+) (.) farm(-?\d+) claim(-?\d+) from(-?\d+),(-?\d+) to(-?\d+),(-?\d+)')
count=collections.Counter();examples=[]
for p in r.glob('*.repl26a'):
    with zipfile.ZipFile(p) as z:
        texts=[z.read('team-'+x+'.stdout').decode(errors='replace') for x in 'ab']
    for t in texts:
        if 'LGY ' not in t:continue
        ds={(int(a[0]),int(a[1])):a for a in dre.findall(t)}
        for a in yre.findall(t):
            rr,i,g,f,c,*pos=map(int,a);count['yields']+=1
            count['own' if f==g or c==g else 'other' if f>=0 else 'no_goal']+=1
            nxt=ds.get((rr+1,i));again=ds.get((rr+2,i))
            if nxt and list(map(int,nxt[-2:]))==pos[:2]:
                count['next_back']+=1
                if len(examples)<30: examples.append({'file':str(p),'yield':a,'next':nxt,'after':again})
print(json.dumps(dict(count),indent=2));r.parent.joinpath(r.name+'-examples.json').write_text(json.dumps(examples,indent=2))
