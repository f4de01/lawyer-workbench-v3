"""门禁原型: 只读 PDF, 输出事实. 用法 gate.py a.pdf [b.pdf...]"""
import sys, pymupdf
WANT_FONTS = {'FangSong', 'FZXiaoBiaoSong', '方正小标宋'}
for f in sys.argv[1:]:
    doc = pymupdf.open(f); out = {'file': f, 'pages': len(doc)}
    blank = []; fonts = set(); overflow = []; tall_rows = []
    for i, p in enumerate(doc):
        txt = p.get_text().strip(); dr = p.get_drawings()
        if not txt and not p.get_images(): blank.append(i+1)
        fonts |= {fi[3].split('+')[-1] for fi in p.get_fonts()}
        W, H = p.rect.width, p.rect.height
        for b in p.get_text('blocks'):
            x0,y0,x1,y1 = b[:4]
            if x0 < 0 or y0 < 0 or x1 > W or y1 > H: overflow.append((i+1, [round(v) for v in b[:4]]))
        for t in p.find_tables().tables:
            for r in t.rows:
                h = r.bbox[3]-r.bbox[1]
                if h > 100: tall_rows.append((i+1, round(h), r.cells[0] and [round(v) for v in r.cells[0]] ))
    out.update(blank_pages=blank, fonts=sorted(fonts), overflow=overflow, tall_rows=tall_rows)
    print(out)
