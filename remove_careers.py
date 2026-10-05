#!/usr/bin/env python3
"""Strip career entries (current + history) with the given career IDs from every sim.

Usage: python3 remove_careers.py IN.save OUT.save CAREER_ID [CAREER_ID ...]
  CAREER_ID is decimal, as printed by careers.py.
The original file is never modified.
"""
import struct
import sys
import zlib
from pb_explore import parse
from remove_sim import varint, top_level_spans, read_dbpf, SAVEGAME_TYPE, SIMS_FIELD

SIM_ATTRS_FIELD = 30
CAREERS_FIELD = 12


def enc_varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b); return bytes(out)


def ld(fn, payload):
    return enc_varint((fn << 3) | 2) + enc_varint(len(payload)) + payload


def career_id(payload):
    for fn, wt, v in parse(payload) or []:
        if fn == 1 and wt == 0:
            return v
    return None


def rewrite(msg, fn_target, fn_fix):
    """Return (new_msg, changed): apply fn_fix to every length-delimited field fn_target."""
    out, changed = bytearray(), 0
    for fn, wt, s, e, v in top_level_spans(msg):
        if fn == fn_target and wt == 2:
            nv, c = fn_fix(v)
            if c:
                out += ld(fn, nv); changed += c; continue
        out += msg[s:e]
    return bytes(out), changed


def main():
    src, dst = sys.argv[1], sys.argv[2]
    targets = {int(x) for x in sys.argv[3:]}
    if not targets or src == dst:
        raise SystemExit(__doc__)
    data = open(src, 'rb').read()
    entries = read_dbpf(data)
    sg = [e for e in entries if e['t'] == SAVEGAME_TYPE][0]
    raw = data[sg['off']:sg['off'] + sg['size']]
    blob = zlib.decompress(raw) if sg['comp'] == 0x5A42 else raw

    removed = []

    def fix_careers(v):
        out, c = bytearray(), 0
        for fn, wt, s, e, p in top_level_spans(v):
            if wt == 2 and career_id(p) in targets:
                c += 1; removed.append((fn, career_id(p))); continue
            out += v[s:e]
        return bytes(out), c

    def fix_attrs(v):
        return rewrite(v, CAREERS_FIELD, fix_careers)

    def fix_sim(v):
        return rewrite(v, SIM_ATTRS_FIELD, fix_attrs)

    new_blob, n = rewrite(blob, SIMS_FIELD, fix_sim)
    print("Removed %d career entries (%d current, %d history/other)" %
          (n, sum(1 for f, _ in removed if f == 1), sum(1 for f, _ in removed if f != 1)))
    if not n:
        raise SystemExit("Nothing removed")

    new_raw = zlib.compress(new_blob, 6) if sg['comp'] == 0x5A42 else new_blob
    header = bytearray(data[:0x60]); body = bytearray(); pos = 0x60
    index = bytearray(struct.pack('<I', 0))
    placed = {}
    for e in sorted(entries, key=lambda e: e['off']):
        if e['comp'] == 0xFFE0 or e['size'] == 0:
            continue
        chunk = new_raw if e is sg else data[e['off']:e['off'] + e['size']]
        placed[id(e)] = (pos, len(chunk), len(new_blob) if e is sg else e['mem'])
        body += chunk; pos += len(chunk)
    for e in entries:
        off, size, mem = placed.get(id(e), (e['off'], e['size'], e['mem']))
        index += struct.pack('<7I', e['t'], e['g'], e['ih'], e['il'], off,
                             size | (0x80000000 if e['ext'] else 0), mem)
        if e['ext']:
            index += struct.pack('<HH', e['comp'], e['committed'])
    struct.pack_into('<I', header, 0x28, 0)
    struct.pack_into('<I', header, 0x2C, len(index))
    struct.pack_into('<Q', header, 0x40, pos)
    with open(dst, 'wb') as f:
        f.write(header); f.write(body); f.write(index)
    print("Wrote", dst)


if __name__ == '__main__':
    main()
