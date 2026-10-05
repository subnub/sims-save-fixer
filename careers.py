#!/usr/bin/env python3
"""List every career referenced in a Sims 4 save (sim attributes field 30.12).

High-bit (>= 2**63) tuning IDs are almost always custom content / mod careers.
Usage: python3 careers.py SAVE
"""
import struct, sys
from collections import defaultdict
from pb_explore import parse, load_savegame

def careers_of(sim):
    out = []
    for fn, wt, v in sim:
        if fn != 30: continue
        for a, b, x in parse(v):
            if a != 12: continue
            for sub, wt2, c in parse(x):
                if wt2 != 2: continue
                m = parse(c) or []
                d = {k: val for k, _, val in m}
                out.append((sub, d.get(1), d.get(2), d))
    return out

if __name__ == '__main__':
    blob = load_savegame(sys.argv[1]); top = parse(blob)
    by_career = defaultdict(list)
    for fn, wt, v in top:
        if fn != 6: continue
        s = parse(v); d = {k: val for k, _, val in s}
        name = "%s %s" % (d.get(5, b'').decode(errors='replace'), d.get(6, b'').decode(errors='replace'))
        sid = struct.unpack('<Q', d[1])[0]
        for sub, cuid, tuid, raw in careers_of(s):
            by_career[(sub, cuid)].append((name.strip() or '<no name>', sid, tuid))
    for (sub, cuid), lst in sorted(by_career.items(), key=lambda x: (x[0][0], -(x[0][1] or 0) >= 0, x[0][1] or 0)):
        tag = "CUSTOM/MOD" if cuid and cuid >= 1 << 63 else ""
        print("30.12.%d career %-22s %-10s %d sim(s)" % (sub, cuid, tag, len(lst)))
        if tag:
            for n, sid, t in lst:
                print("      %-28s %016x track %s" % (n, sid, t))
