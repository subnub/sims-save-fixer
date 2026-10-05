#!/usr/bin/env python3
"""Targeted fix for Slot_ffffffff.save.

1. Strip careers whose tuning no longer exists in the game or Mods folder (current + history), all sims.
2. For sims holding University course-slot careers without a university enrollment
   (degree_tracker.current_university == 0), drop those *current* careers and reset
   enrollment_status to NONE. This is what crashes careers/career_base.py:4592/4597
   (populate_set_career_op -> degree_tracker.get_course_data()/get_university() is None).

Usage: python fix_save.py IN.save OUT.save
"""
import struct, sys, zlib
from pb_explore import parse
from remove_sim import top_level_spans, read_dbpf, SAVEGAME_TYPE, SIMS_FIELD
from remove_careers import ld, enc_varint, career_id, rewrite

MISSING_CAREERS = {9597272116101309544, 15554726041101812524}
UNI_CAREERS = {209979, 209984, 209988, 209989, 223698}  # university_CourseSlot_A-D + university base career
ATTRS, CAREERS, DEGREE = 30, 12, 30
log = []


def sim_name(sim):
    d = {k: v for k, _, v in parse(sim)}
    return ('%s %s' % (d.get(5, b'').decode(errors='replace'), d.get(6, b'').decode(errors='replace'))).strip()


def fix_sim(sim):
    name = sim_name(sim)
    attrs = [v for fn, wt, v in parse(sim) if fn == ATTRS]
    deg = {}
    for fn, wt, v in parse(attrs[0]) if attrs else []:
        if fn == DEGREE:
            deg = {k: val for k, w, val in parse(v) if w == 0}
    enrolled = deg.get(2, 0) != 0

    def fix_careers(v):
        out, c = bytearray(), 0
        for fn, wt, s, e, p in top_level_spans(v):
            cid = career_id(p) if wt == 2 else None
            if cid in MISSING_CAREERS:
                c += 1; log.append('%s: removed missing career %d (%s)' % (name, cid, 'current' if fn == 1 else 'history'))
                continue
            if fn == 1 and cid in UNI_CAREERS and not enrolled:
                c += 1; log.append('%s: removed orphan university career %d' % (name, cid))
                continue
            out += v[s:e]
        return bytes(out), c

    def fix_degree(v):
        if enrolled:
            return v, 0
        out, c = bytearray(), 0
        for fn, wt, s, e, p in top_level_spans(v):
            if fn == 10 and wt == 0:
                val = parse(v[s:e])[0][2]
                if val != 0:
                    c += 1; log.append('%s: reset degree_tracker.enrollment_status %d -> 0 (NONE)' % (name, val))
                    continue
            out += v[s:e]
        return bytes(out), c

    def fix_attrs(v):
        v, a = rewrite(v, CAREERS, fix_careers)
        had_uni = any(name in l and 'university' in l for l in log)
        b = 0
        if had_uni:
            v, b = rewrite(v, DEGREE, fix_degree)
        return v, a + b

    return rewrite(sim, ATTRS, fix_attrs)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    assert src != dst
    data = open(src, 'rb').read()
    entries = read_dbpf(data)
    sg = [e for e in entries if e['t'] == SAVEGAME_TYPE][0]
    raw = data[sg['off']:sg['off'] + sg['size']]
    blob = zlib.decompress(raw) if sg['comp'] == 0x5A42 else raw
    new_blob, n = rewrite(blob, SIMS_FIELD, fix_sim)
    print('\n'.join(log)); print('total edits:', n)

    new_raw = zlib.compress(new_blob, 6) if sg['comp'] == 0x5A42 else new_blob
    header = bytearray(data[:0x60]); body = bytearray(); pos = 0x60
    placed = {}
    for e in sorted(entries, key=lambda e: e['off']):
        if e['comp'] == 0xFFE0 or e['size'] == 0:
            continue
        chunk = new_raw if e is sg else data[e['off']:e['off'] + e['size']]
        placed[id(e)] = (pos, len(chunk), len(new_blob) if e is sg else e['mem'])
        body += chunk; pos += len(chunk)
    index = bytearray(struct.pack('<I', 0))
    for e in entries:
        off, size, mem = placed.get(id(e), (e['off'], e['size'], e['mem']))
        index += struct.pack('<7I', e['t'], e['g'], e['ih'], e['il'], off, size | (0x80000000 if e['ext'] else 0), mem)
        if e['ext']:
            index += struct.pack('<HH', e['comp'], e['committed'])
    struct.pack_into('<I', header, 0x28, 0)
    struct.pack_into('<I', header, 0x2C, len(index))
    struct.pack_into('<Q', header, 0x40, pos)
    with open(dst, 'wb') as f:
        f.write(header); f.write(body); f.write(index)
    print('Wrote', dst)


if __name__ == '__main__':
    main()
