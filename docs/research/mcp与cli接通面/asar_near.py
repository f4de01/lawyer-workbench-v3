import sys,re
data=open(sys.argv[1],'rb').read()
a=sys.argv[2].encode(); b=sys.argv[3].encode(); win=int(sys.argv[4]); limit=int(sys.argv[5]); ctx=int(sys.argv[6]) if len(sys.argv)>6 else 250
n=0
for m in re.finditer(re.escape(a), data):
    s=max(0,m.start()-win); e=min(len(data),m.end()+win)
    if b in data[s:e]:
        cs=max(0,m.start()-ctx); ce=min(len(data),m.end()+ctx)
        print('--- @',m.start()); print(data[cs:ce].decode('utf-8','replace')); n+=1
        if n>=limit: break
print('matches',n)
