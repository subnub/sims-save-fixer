import sys, struct
from pb_explore import parse, load_savegame

UNI = {209979, 209984, 209988, 209989, 223698}

def fields(b):
    return parse(b) or []

blob = load_savegame(sys.argv[1])
for fn, wt, v in parse(blob):
    if fn != 6: continue
    s = parse(v); d = {k: val for k, _, val in s}
    sid = struct.unpack('<Q', d[1])[0]
    name = '%s %s' % (d.get(5, b'').decode(errors='replace'), d.get(6, b'').decode(errors='replace'))
    cur, hist, deg = [], [], None
    for a, _, x in s:
        if a != 30: continue
        for b, _, y in fields(x):
            if b == 12:
                for c, w, z in fields(y):
                    if w != 2: continue
                    dd = {k: val for k, ww, val in fields(z) if ww == 0}
                    (cur if c == 1 else hist if c == 2 else []).append(dd.get(1))
            elif b == 30:
                deg = {}
                for k, w, val in fields(y):
                    deg.setdefault(k, []).append(val if w != 2 else '<%d>' % len(val))
    hasuni_cur = UNI & set(cur)
    hasuni = hasuni_cur or (UNI & set(hist))
    has_univ = deg and deg.get(2, [0])[0]
    if hasuni or has_univ:
        print('%016x %-22s cur_uni=%s hist_uni=%s deg=%s' % (sid, name, sorted(hasuni_cur), sorted(UNI & set(hist)),
              {k: v for k, v in (deg or {}).items() if k in (1, 2, 3, 5, 6, 7, 8, 10)}))
