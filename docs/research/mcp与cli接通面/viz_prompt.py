import sys,re
data=open(sys.argv[1],'rb').read()
seen={}
for m in re.finditer(rb'### Visualizations', data):
    s=m.start()
    chunk=data[s:s+3000]
    end=len(chunk)
    for pat in (b'\n\n# ', b'\n\n# ', b'\n\n## ', b'\n\n## ', b'\n\n### ', b'\n\n### '):
        i=chunk.find(pat, 50)
        if i!=-1 and i<end: end=i
    txt=chunk[:end].decode('utf-8','replace').replace('\n','\n')
    seen.setdefault(txt,[]).append(s)
print(len(seen),'distinct')
for txt,offs in seen.items():
    print('=== offsets',offs[:5],'count',len(offs))
    print(txt)
    print()
