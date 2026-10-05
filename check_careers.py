import sys, json, struct
from collections import defaultdict
from pb_explore import parse, load_savegame

idx = json.load(open('tuning_index.json'))
ea = set()
try:
    ea = set(json.load(open('ea_ids.json')))
except Exception:
    pass

def where(kind, i):
    if i is None:
        return 'n/a'
    s = idx[kind].get(str(i))
    if s:
        return 'MOD/pkg:' + ';'.join(sorted({p.split('\\')[-1] for p in s}))[:70]
    if i in ea:
        return 'EA'
    return '*** NOT FOUND ***'

blob = load_savegame(sys.argv[1])
rows = defaultdict(list)
for fn, wt, v in parse(blob):
    if fn != 6:
        continue
    s = parse(v); d = {k: val for k, _, val in s}
    name = ("%s %s" % (d.get(5, b'').decode(errors='replace'), d.get(6, b'').decode(errors='replace'))).strip()
    sid = struct.unpack('<Q', d[1])[0]
    for a, _, x in s:
        if a != 30: continue
        for b, _, y in parse(x):
            if b != 12: continue
            for sub, wt2, c in parse(y):
                if wt2 != 2: continue
                m = parse(c) or []
                dd = {k: val for k, w, val in m if w == 0}
                rows[(sub, dd.get(1), dd.get(2))].append('%s(%016x)' % (name, sid))
for (sub, cu, tu), sims in sorted(rows.items(), key=lambda r: (r[0][0], r[0][1] or 0)):
    if len(sys.argv) > 2 and sub != int(sys.argv[2]):
        continue
    print('30.12.%d career=%-20s [%s] track=%-20s [%s] sims=%d %s' % (
        sub, cu, where('career', cu), tu, where('track', tu), len(sims), ', '.join(sims[:3]) if 'NOT' in where('career', cu) + where('track', tu) else ''))
