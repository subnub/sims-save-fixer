#!/usr/bin/env python3
"""Generic protobuf explorer for the SaveGameData blob (no schema needed)."""
import sys, struct, zlib
from collections import Counter, defaultdict

def varint(b, p):
    r = s = 0
    while True:
        x = b[p]; p += 1
        r |= (x & 0x7F) << s
        if not x & 0x80: return r, p
        s += 7

def parse(b):
    """Return list of (field, wiretype, value) or None if not a valid message."""
    out, p, n = [], 0, len(b)
    try:
        while p < n:
            k, p = varint(b, p); wt, fn = k & 7, k >> 3
            if fn == 0 or fn > 536870911: return None
            if wt == 0: v, p = varint(b, p)
            elif wt == 1: v = b[p:p+8]; p += 8
            elif wt == 5: v = b[p:p+4]; p += 4
            elif wt == 2:
                ln, p = varint(b, p); v = b[p:p+ln]; p += ln
            else: return None
            if p > n: return None
            out.append((fn, wt, v))
    except IndexError:
        return None
    return out

def looks_text(v):
    try: s = v.decode('utf-8')
    except UnicodeDecodeError: return False
    return len(s) > 0 and all(c.isprintable() for c in s)

def load_savegame(path):
    sys.path.insert(0, '.')
    import dbpf_check  # reuse nothing heavy; just re-read index here
    d = open(path, 'rb').read()
    ip = struct.unpack_from('<Q', d, 0x40)[0]; n = struct.unpack_from('<I', d, 0x24)[0]
    p = ip + 4
    for _ in range(n):
        t, g, ih, il, off, sz, ms = struct.unpack_from('<7I', d, p); p += 28
        comp = None
        if sz & 0x80000000: comp, _c = struct.unpack_from('<HH', d, p); p += 4
        if t == 0x0D:
            raw = d[off:off + (sz & 0x7FFFFFFF)]
            return zlib.decompress(raw) if comp == 0x5A42 else raw

if __name__ == '__main__':
    blob = load_savegame(sys.argv[1])
    top = parse(blob)
    c = Counter(); sizes = defaultdict(int)
    for fn, wt, v in top:
        c[(fn, wt)] += 1
        if wt == 2: sizes[fn] += len(v)
    for (fn, wt), cnt in sorted(c.items()):
        print("field %3d wt%d  x%-5d  %10d bytes" % (fn, wt, cnt, sizes[fn]))
