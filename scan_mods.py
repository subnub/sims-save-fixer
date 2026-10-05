#!/usr/bin/env python3
"""Search a Sims 4 Mods folder for the custom careers this save uses.

Usage: python3 scan_mods.py "/path/to/The Sims 4/Mods"
Needs only Python 3 (no extra packages). Works on Windows and Mac.
"""
import os
import struct
import sys

# Custom (mod) career + track tuning IDs found in Slot_ffffffff.save
WANTED = {
    9597272116101309544: "career A (13 sims, 2 currently employed)",
    12117131909491602471: "career A track",
    13353481704870670235: "career B (14 sims, history only)",
    11612804652156179940: "career B track",
    14045674399464473055: "career B track (alt)",
    15554726041101812524: "career C (7 sims, history only)",
    14638994455164074472: "career C track",
    6693958541354755771: "career C track (alt)",
    17417120968435530887: "career D (4 sims, currently employed)",
    12337638034494195839: "career D track",
}


def package_instances(path):
    with open(path, 'rb') as f:
        head = f.read(0x60)
        if head[:4] != b'DBPF':
            return
        count = struct.unpack_from('<I', head, 0x24)[0]
        idx_size = struct.unpack_from('<I', head, 0x2C)[0]
        idx_pos = struct.unpack_from('<Q', head, 0x40)[0] or struct.unpack_from('<I', head, 0x28)[0]
        f.seek(idx_pos)
        idx = f.read(idx_size)
    p = 0
    flags = struct.unpack_from('<I', idx, p)[0]; p += 4
    const = {}
    for bit in range(3):
        if flags & (1 << bit):
            const[bit] = struct.unpack_from('<I', idx, p)[0]; p += 4
    for _ in range(count):
        vals = []
        for bit in range(3):
            if bit in const:
                vals.append(const[bit])
            else:
                vals.append(struct.unpack_from('<I', idx, p)[0]); p += 4
        t, g, ih = vals
        il, off, sz, mem = struct.unpack_from('<4I', idx, p); p += 16
        if sz & 0x80000000:
            p += 4
        yield t, (ih << 32) | il


def main():
    root = sys.argv[1]
    found = {}
    n = 0
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.lower().endswith('.package'):
                continue
            n += 1
            full = os.path.join(dirpath, fn)
            try:
                for t, inst in package_instances(full):
                    if inst in WANTED:
                        found.setdefault(inst, []).append(os.path.relpath(full, root))
            except Exception as e:
                print("  could not read %s: %s" % (full, e))
    print("Scanned %d .package files\n" % n)
    for inst, label in WANTED.items():
        where = found.get(inst)
        print("%-45s %s" % (label, "FOUND in: " + ", ".join(sorted(set(where))) if where else "** MISSING **"))


if __name__ == '__main__':
    main()
