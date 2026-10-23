import zipfile,glob,struct,sys,collections
z=zipfile.ZipFile(glob.glob(sys.argv[2])[0])
def rd(b): return [struct.unpack_from('<Q',b,13+8*i)[0] for i in range((len(b)-13)//8)]
a=rd(open(sys.argv[1],'rb').read())
b=rd(z.read(sys.argv[3] if len(sys.argv)>3 else 'team-a.fuel'))
diff=[i for i in range(min(len(a),len(b))) if a[i]!=b[i]]
print(len(a),len(b),'ndiff',len(diff), diff[:10], [(a[i],b[i]) for i in diff[:10]])
print(collections.Counter(b[i]-a[i] for i in diff).most_common(15))
