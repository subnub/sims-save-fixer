#!/usr/bin/env python3
"""Integrity checker for Sims 4 DBPF save files (.save / .package).

Usage: python3 dbpf_check.py Slot_xxxxxxxx.save [--extract OUTDIR]
"""
import struct
import sys
import zlib
import os
from collections import Counter

TYPE_NAMES = {
    0x0000000D: "SaveGameData",
    0x3BD45407: "HouseholdThumbnail",
    0x0580A2B4: "Thumbnail(png)",
    0x3C1AF1F2: "CASPartThumbnail",
    0x3C2A8647: "BuyBuildThumbnail",
    0xCD9DE247: "SimThumbnail",
    0x6B6D837E: "SimThumbnail(lg)",
    0x9C925813: "SimThumbnail(sm)",
    0x3BD45408: "LotThumbnail",
    0xAD366F96: "SimThumbnail(xl)",
    0xD84E7FC5: "LotPreview",
}
COMP_NAMES = {0x0000: "none", 0x5A42: "zlib", 0xFFFF: "refpack", 0xFFFE: "streamable", 0xFFE0: "deleted"}


def refpack_decompress(data, expected):
    """EA RefPack/QFS decompression."""
    if len(data) < 2:
        raise ValueError("too short")
    flags = data[0]
    if data[1] != 0xFB:
        raise ValueError("bad refpack magic %02x" % data[1])
    size_bytes = 4 if flags & 0x80 else 3
    pos = 2
    if flags & 0x01:
        pos += size_bytes
    out_size = int.from_bytes(data[pos:pos + size_bytes], "big")
    pos += size_bytes
    out = bytearray()
    n = len(data)
    while pos < n:
        b0 = data[pos]
        if b0 < 0x80:
            b1 = data[pos + 1]; pos += 2
            plain = b0 & 3
            copy = ((b0 >> 2) & 7) + 3
            off = ((b0 & 0x60) << 3) + b1 + 1
        elif b0 < 0xC0:
            b1, b2 = data[pos + 1], data[pos + 2]; pos += 3
            plain = (b1 >> 6) & 3
            copy = (b0 & 0x3F) + 4
            off = ((b1 & 0x3F) << 8) + b2 + 1
        elif b0 < 0xE0:
            b1, b2, b3 = data[pos + 1:pos + 4]; pos += 4
            plain = b0 & 3
            copy = ((b0 & 0x0C) << 6) + b3 + 5
            off = ((b0 & 0x10) << 12) + (b1 << 8) + b2 + 1
        elif b0 < 0xFC:
            pos += 1
            plain = ((b0 & 0x1F) << 2) + 4
            copy = 0; off = 0
        else:
            pos += 1
            plain = b0 & 3
            copy = 0; off = 0
            out += data[pos:pos + plain]
            break
        out += data[pos:pos + plain]; pos += plain
        if copy:
            if off > len(out):
                raise ValueError("back-reference beyond output (off=%d, have=%d)" % (off, len(out)))
            start = len(out) - off
            for i in range(copy):
                out.append(out[start + i])
    if len(out) != out_size:
        raise ValueError("refpack size mismatch: header %d, got %d" % (out_size, len(out)))
    return bytes(out)


def check_protobuf(buf, depth=0, max_depth=3):
    """Walk raw protobuf wire format. Returns (ok, error_offset, message)."""
    pos, n = 0, len(buf)

    def varint(p):
        result = shift = 0
        while True:
            if p >= n:
                raise ValueError("truncated varint")
            b = buf[p]; p += 1
            result |= (b & 0x7F) << shift
            if not b & 0x80:
                return result, p
            shift += 7
            if shift > 70:
                raise ValueError("varint too long")

    fields = 0
    try:
        while pos < n:
            start = pos
            key, pos = varint(pos)
            wt, fn = key & 7, key >> 3
            if fn == 0:
                raise ValueError("field number 0")
            if wt == 0:
                _, pos = varint(pos)
            elif wt == 1:
                pos += 8
            elif wt == 5:
                pos += 4
            elif wt == 2:
                ln, pos = varint(pos)
                if pos + ln > n:
                    raise ValueError("length-delimited field %d (len %d) runs past end" % (fn, ln))
                pos += ln
            else:
                raise ValueError("invalid wire type %d" % wt)
            if pos > n:
                raise ValueError("field %d runs past end" % fn)
            fields += 1
    except ValueError as e:
        return False, start, str(e), fields
    return True, None, None, fields


def main():
    path = sys.argv[1]
    extract = sys.argv[sys.argv.index("--extract") + 1] if "--extract" in sys.argv else None
    data = open(path, "rb").read()
    fsize = len(data)
    problems = []
    print("File: %s (%d bytes)" % (path, fsize))

    if data[:4] != b"DBPF":
        print("FATAL: missing DBPF magic, got %r" % data[:4]); return
    major, minor = struct.unpack_from("<II", data, 4)
    count = struct.unpack_from("<I", data, 0x24)[0]
    idx_size = struct.unpack_from("<I", data, 0x2C)[0]
    idx_pos_low = struct.unpack_from("<I", data, 0x28)[0]
    idx_pos = struct.unpack_from("<Q", data, 0x40)[0] or idx_pos_low
    print("DBPF v%d.%d, %d entries, index @0x%X size %d" % (major, minor, count, idx_pos, idx_size))
    if idx_pos + idx_size > fsize:
        problems.append("Index extends past end of file -> file is TRUNCATED")
        print("FATAL:", problems[-1]); return
    if idx_pos + idx_size != fsize:
        print("note: %d bytes after index" % (fsize - idx_pos - idx_size))

    p = idx_pos
    flags = struct.unpack_from("<I", data, p)[0]; p += 4
    const = {}
    for bit, name in enumerate(("type", "group", "insthi")):
        if flags & (1 << bit):
            const[name] = struct.unpack_from("<I", data, p)[0]; p += 4

    entries = []
    for i in range(count):
        e = {}
        for name in ("type", "group", "insthi"):
            if name in const:
                e[name] = const[name]
            else:
                e[name] = struct.unpack_from("<I", data, p)[0]; p += 4
        e["instlo"], e["offset"], sz, e["memsize"] = struct.unpack_from("<IIII", data, p); p += 16
        e["size"] = sz & 0x7FFFFFFF
        if sz & 0x80000000:
            e["comp"], e["committed"] = struct.unpack_from("<HH", data, p); p += 4
        else:
            e["comp"] = 0
        e["idx"] = i
        entries.append(e)
    if p != idx_pos + idx_size:
        problems.append("Index size mismatch: parsed %d bytes, header says %d" % (p - idx_pos, idx_size))

    # Overlap / bounds checks
    spans = sorted((e["offset"], e["offset"] + e["size"], e["idx"]) for e in entries if e["comp"] != 0xFFE0)
    for a, b in zip(spans, spans[1:]):
        if b[0] < a[1]:
            problems.append("Entries %d and %d overlap (0x%X-0x%X vs 0x%X)" % (a[2], b[2], a[0], a[1], b[0]))
    keys = Counter((e["type"], e["group"], e["insthi"], e["instlo"]) for e in entries)
    dups = [k for k, c in keys.items() if c > 1]
    if dups:
        problems.append("%d duplicate resource keys (TGI)" % len(dups))

    type_counts = Counter(e["type"] for e in entries)
    print("\nResource types:")
    for t, c in type_counts.most_common():
        print("  0x%08X %-20s x%d" % (t, TYPE_NAMES.get(t, "?"), c))

    bad = 0
    savegame = []
    for e in entries:
        tag = "#%d T:%08X G:%08X I:%08X%08X" % (e["idx"], e["type"], e["group"], e["insthi"], e["instlo"])
        if e["comp"] == 0xFFE0:
            continue  # deleted-entry marker, no data
        if e["offset"] + e["size"] > fsize or e["offset"] < 0x60:
            problems.append("%s: data out of bounds (off 0x%X size %d)" % (tag, e["offset"], e["size"])); bad += 1; continue
        raw = data[e["offset"]:e["offset"] + e["size"]]
        try:
            if e["comp"] == 0x5A42:
                out = zlib.decompress(raw)
            elif e["comp"] == 0xFFFF:
                out = refpack_decompress(raw, e["memsize"])
            elif e["comp"] == 0:
                out = raw
            elif e["comp"] == 0xFFE0:
                continue
            else:
                raise ValueError("unknown compression 0x%04X" % e["comp"])
        except Exception as ex:
            problems.append("%s: decompress failed (%s): %s" % (tag, COMP_NAMES.get(e["comp"], hex(e["comp"])), ex)); bad += 1; continue
        if len(out) != e["memsize"]:
            problems.append("%s: size mismatch, index says %d, got %d" % (tag, e["memsize"], len(out))); bad += 1
        if all(b == 0 for b in out[:4096]) and len(out) > 0:
            problems.append("%s: data starts with 4KB+ of zeros (possible zeroed/corrupt block)" % tag)
        if e["type"] == 0x0000000D:
            savegame.append((e, out))
        if extract:
            os.makedirs(extract, exist_ok=True)
            open(os.path.join(extract, "%04d_%08X_%08X_%08X%08X.bin" % (e["idx"], e["type"], e["group"], e["insthi"], e["instlo"])), "wb").write(out)

    ndel = sum(e["comp"] == 0xFFE0 for e in entries)
    print("\nDecompressed %d/%d resources OK (%d deleted markers skipped)" % (len(entries) - bad - ndel, len(entries) - ndel, ndel))

    for e, out in savegame:
        ok, off, msg, nf = check_protobuf(out)
        print("\nSaveGameData #%d: %d bytes, %d top-level protobuf fields -> %s" %
              (e["idx"], len(out), nf, "OK" if ok else "BROKEN at offset %d: %s" % (off, msg)))
        if not ok:
            problems.append("SaveGameData protobuf malformed at %d: %s" % (off, msg))
    if not savegame:
        problems.append("No SaveGameData (type 0x0000000D) resource found!")

    print("\n=== %d problem(s) ===" % len(problems))
    for pr in problems[:200]:
        print(" -", pr)


if __name__ == "__main__":
    main()
