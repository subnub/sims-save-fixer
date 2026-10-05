#!/usr/bin/env python3
"""Remove sim record(s) from a Sims 4 save and write a new .save file.

Usage: python3 remove_sim.py IN.save OUT.save SIMID [SIMID ...]
  SIMID is hex, e.g. 0ef71483a0b72f8b

The original file is never modified. Refuses to remove a sim that is still
referenced elsewhere in the save (household member lists, relationships, ...).
"""
import struct
import sys
import zlib

SAVEGAME_TYPE = 0x0000000D
SIMS_FIELD = 6


def varint(b, p):
    r = s = 0
    while True:
        x = b[p]; p += 1
        r |= (x & 0x7F) << s
        if not x & 0x80:
            return r, p
        s += 7


def top_level_spans(b):
    """Yield (field, wiretype, start, end, payload) for each top-level field."""
    p, n = 0, len(b)
    while p < n:
        start = p
        k, p = varint(b, p)
        wt, fn = k & 7, k >> 3
        if wt == 0:
            _, p = varint(b, p); payload = None
        elif wt == 1:
            payload = b[p:p + 8]; p += 8
        elif wt == 5:
            payload = b[p:p + 4]; p += 4
        elif wt == 2:
            ln, p = varint(b, p); payload = b[p:p + ln]; p += ln
        else:
            raise ValueError("bad wire type %d at %d" % (wt, start))
        yield fn, wt, start, p, payload


def read_dbpf(data):
    count = struct.unpack_from('<I', data, 0x24)[0]
    idx_pos = struct.unpack_from('<Q', data, 0x40)[0] or struct.unpack_from('<I', data, 0x28)[0]
    p = idx_pos
    flags = struct.unpack_from('<I', data, p)[0]; p += 4
    if flags != 0:
        raise SystemExit("Index uses constant TGI flags (%d); not supported" % flags)
    entries = []
    for _ in range(count):
        t, g, ih, il, off, sz, ms = struct.unpack_from('<7I', data, p); p += 28
        ext = bool(sz & 0x80000000)
        comp, committed = (struct.unpack_from('<HH', data, p) if ext else (0, 0))
        if ext:
            p += 4
        entries.append(dict(t=t, g=g, ih=ih, il=il, off=off, size=sz & 0x7FFFFFFF, mem=ms,
                            ext=ext, comp=comp, committed=committed))
    return entries


def main():
    src, dst = sys.argv[1], sys.argv[2]
    targets = {int(x, 16) for x in sys.argv[3:]}
    if not targets:
        raise SystemExit(__doc__)
    if src == dst:
        raise SystemExit("Refusing to overwrite the input file")

    data = open(src, 'rb').read()
    entries = read_dbpf(data)
    sg = [e for e in entries if e['t'] == SAVEGAME_TYPE]
    if len(sg) != 1:
        raise SystemExit("Expected exactly one SaveGameData resource, found %d" % len(sg))
    sg = sg[0]
    raw = data[sg['off']:sg['off'] + sg['size']]
    blob = zlib.decompress(raw) if sg['comp'] == 0x5A42 else raw

    # Find the sim records to drop
    drop = []
    for fn, wt, start, end, payload in top_level_spans(blob):
        if fn == SIMS_FIELD and wt == 2:
            sid = struct.unpack_from('<Q', payload, 1)[0] if payload[:1] == b'\x09' else None
            if sid in targets:
                drop.append((start, end, sid))
    found = {d[2] for d in drop}
    for t in targets - found:
        print("WARNING: sim %016x not found" % t)
    if not drop:
        raise SystemExit("Nothing to remove")

    # Safety: the sim ID must not appear anywhere outside its own record
    for start, end, sid in drop:
        needle = struct.pack('<Q', sid)
        refs = blob.count(needle) - blob[start:end].count(needle)
        if refs:
            raise SystemExit("Sim %016x is referenced %d time(s) elsewhere; not removing" % (sid, refs))

    out_blob = bytearray()
    prev = 0
    for start, end, sid in sorted(drop):
        out_blob += blob[prev:start]
        prev = end
        print("Removing sim %016x (%d bytes)" % (sid, end - start))
    out_blob += blob[prev:]
    out_blob = bytes(out_blob)

    new_raw = zlib.compress(out_blob, 6) if sg['comp'] == 0x5A42 else out_blob

    # Rebuild the package: header, resource data in original order, then index
    header = bytearray(data[:0x60])
    body = bytearray()
    pos = len(header)
    new_entries = []
    for e in sorted(entries, key=lambda e: e['off']):
        ne = dict(e)
        if e['comp'] == 0xFFE0 or e['size'] == 0:
            new_entries.append(ne)
            continue
        chunk = new_raw if e is sg else data[e['off']:e['off'] + e['size']]
        ne['off'] = pos
        ne['size'] = len(chunk)
        if e is sg:
            ne['mem'] = len(out_blob)
        body += chunk
        pos += len(chunk)
        new_entries.append(ne)
    # keep original index order
    order = {id(e): i for i, e in enumerate(entries)}
    by_orig = sorted(zip(sorted(entries, key=lambda e: e['off']), new_entries), key=lambda x: order[id(x[0])])

    index = bytearray(struct.pack('<I', 0))
    for _, e in by_orig:
        sz = e['size'] | (0x80000000 if e['ext'] else 0)
        index += struct.pack('<7I', e['t'], e['g'], e['ih'], e['il'], e['off'], sz, e['mem'])
        if e['ext']:
            index += struct.pack('<HH', e['comp'], e['committed'])

    idx_pos = len(header) + len(body)
    struct.pack_into('<I', header, 0x24, len(entries))
    struct.pack_into('<I', header, 0x28, 0)
    struct.pack_into('<I', header, 0x2C, len(index))
    struct.pack_into('<Q', header, 0x40, idx_pos)

    with open(dst, 'wb') as f:
        f.write(header); f.write(body); f.write(index)
    print("Wrote %s (%d bytes; SaveGameData %d -> %d bytes)" %
          (dst, idx_pos + len(index), len(blob), len(out_blob)))


if __name__ == '__main__':
    main()
