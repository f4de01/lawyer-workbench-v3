import sys,re
data=open(sys.argv[1],'rb').read()
kw=sys.argv[2].encode(); before=int(sys.argv[3]); after=int(sys.argv[4]); limit=int(sys.argv[5])
n=0
for m in re.finditer(re.escape(kw), data):
    s=max(0,m.start()-before); e=min(len(data),m.end()+after)
    print('--- @',m.start()); print(data[s:e].decode('utf-8','replace')); n+=1
    if n>=limit: break
