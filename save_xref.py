#!/usr/bin/env python3
"""Cross-reference check of Sims 4 SaveGameData (schema inferred from wire format).

Inferred field numbers:
  SaveGameData: 4=neighborhoods 5=households 6=sims 7=zones 8=streets
  Household:    1=account 2=household_id 3=name 4=home_zone 5=funds 6=inventory 11.1=packed sim ids
  Sim:          1=sim_id 2=zone_id 4=household_id 5=first 6=last 22=household_name
  Zone:         1=zone_id 2=name 10=neighborhood_id
"""
import struct
import sys
from collections import Counter, defaultdict
from pb_explore import parse, load_savegame


def u64(b):
    return struct.unpack('<Q', b)[0]


def fields(msg):
    d = defaultdict(list)
    for fn, wt, v in msg:
        d[fn].append(v)
    return d


def first(d, k, conv=None, default=None):
    if k not in d:
        return default
    return conv(d[k][0]) if conv else d[k][0]


def txt(b):
    return b.decode('utf-8', 'replace') if isinstance(b, bytes) else b


def main(path):
    blob = load_savegame(path)
    top = fields(parse(blob))
    issues = []

    households, sims, zones, hoods = {}, {}, {}, {}
    hh_members = {}
    for raw in top[5]:
        f = fields(parse(raw))
        hid = first(f, 2, u64)
        if hid in households:
            issues.append("Duplicate household id %016x" % hid)
        members = []
        if 11 in f:
            inner = fields(parse(f[11][0]))
            if 1 in inner:
                pk = inner[1][0]
                members = [u64(pk[i:i + 8]) for i in range(0, len(pk), 8)]
        households[hid] = dict(name=txt(first(f, 3, default=b'')), zone=first(f, 4, u64, 0),
                               funds=first(f, 5, default=0), n_inv=len(f.get(6, [])))
        hh_members[hid] = members

    for raw in top[6]:
        f = fields(parse(raw))
        sid = first(f, 1, u64)
        if sid in sims:
            issues.append("Duplicate sim id %016x (%s)" % (sid, sims[sid]['name']))
        sims[sid] = dict(name="%s %s" % (txt(first(f, 5, default=b'')), txt(first(f, 6, default=b''))),
                         hh=first(f, 4, u64, 0), zone=first(f, 2, u64, 0),
                         hhname=txt(first(f, 22, default=b'')))

    for raw in top[7]:
        f = fields(parse(raw))
        zid = first(f, 1, u64)
        if zid in zones:
            issues.append("Duplicate zone id %016x" % zid)
        zones[zid] = dict(name=txt(first(f, 2, default=b'')), hood=first(f, 10, u64, 0),
                          f6=first(f, 6, u64, 0), f13=first(f, 13, u64, 0))

    for raw in top[4]:
        f = fields(parse(raw))
        hoods[first(f, 1, u64)] = txt(first(f, 3, default=b''))

    print("Neighborhoods: %d  Households: %d  Sims: %d  Zones: %d" %
          (len(hoods), len(households), len(sims), len(zones)))
    print("Worlds:", ", ".join(sorted(hoods.values())))

    # Sims -> household
    for sid, s in sims.items():
        if s['hh'] and s['hh'] not in households:
            issues.append("Sim '%s' (%016x) points to MISSING household %016x ('%s')" % (s['name'], sid, s['hh'], s['hhname']))
        elif s['hh'] and sid not in hh_members[s['hh']]:
            issues.append("Sim '%s' (%016x) says household '%s' but is not in its member list" %
                          (s['name'], sid, households[s['hh']]['name']))
        if not s['name'].strip():
            issues.append("Sim %016x has an empty name" % sid)
        if s['zone'] and s['zone'] not in zones:
            issues.append("Sim '%s' is on MISSING zone %016x" % (s['name'], s['zone']))

    # Household -> sims
    claimed = Counter()
    for hid, members in hh_members.items():
        h = households[hid]
        if not members:
            issues.append("Household '%s' (%016x) has NO members" % (h['name'], hid))
        for m in members:
            claimed[m] += 1
            if m not in sims:
                issues.append("Household '%s' lists MISSING sim %016x" % (h['name'], m))
            elif sims[m]['hh'] != hid:
                issues.append("Household '%s' lists sim '%s' who belongs to household %016x" %
                              (h['name'], sims[m]['name'], sims[m]['hh']))
        if h['zone'] and h['zone'] not in zones:
            issues.append("Household '%s' home zone %016x MISSING" % (h['name'], h['zone']))
        if isinstance(h['funds'], int) and h['funds'] > 9_999_999:
            issues.append("Household '%s' funds suspicious: %d" % (h['name'], h['funds']))
    for m, c in claimed.items():
        if c > 1:
            issues.append("Sim %016x (%s) is in %d households" % (m, sims.get(m, {}).get('name', '?'), c))

    # Multiple households on one lot
    home = defaultdict(list)
    for hid, h in households.items():
        if h['zone']:
            home[h['zone']].append(h['name'])
    for z, names in home.items():
        if len(names) > 1:
            issues.append("Zone '%s' is home to %d households: %s" % (zones.get(z, {}).get('name', '%016x' % z), len(names), names))

    # Zones -> neighborhood
    for zid, z in zones.items():
        if z['hood'] and z['hood'] not in hoods:
            issues.append("Zone '%s' references MISSING neighborhood %016x" % (z['name'], z['hood']))

    # Deep structural scan: every nested message that parses as protobuf in one place
    # should parse everywhere; find records whose bytes don't parse.
    for key, label in ((5, 'household'), (6, 'sim'), (7, 'zone'), (8, 'street')):
        for i, raw in enumerate(top[key]):
            if parse(raw) is None:
                issues.append("%s record #%d fails to parse" % (label, i))

    print("\n=== %d issue(s) ===" % len(issues))
    for s in issues:
        print(" -", s)
    return sims, households, zones, hoods


if __name__ == '__main__':
    main(sys.argv[1])
