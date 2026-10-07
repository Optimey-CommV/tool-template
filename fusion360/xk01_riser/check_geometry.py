# SPDX-FileCopyrightText: 2026 Joost Meyfroodt
# SPDX-License-Identifier: GPL-3.0-or-later
"""Controleert de doorsneden van xk01_riser.py buiten Fusion.

Gebruik:  python3 check_geometry.py [doorsnede.png]
Vereist:  shapely, en matplotlib voor de tekening.
"""

import math
import sys

from shapely.geometry import Point, Polygon, box

import xk01_riser as r

EPS = 1e-6


def shape(key):
    d = r.derived()
    lip_t = d["lip_t"][key]
    outer = Polygon(r.outer_profile(lip_t))
    if key == "C":
        return outer
    return outer.difference(Polygon(r.cavity_profile(lip_t)))


def shifted(poly, dy, dz):
    return Polygon([(y + dy, z + dz) for y, z in poly.exterior.coords])


def main():
    d = r.derived()
    s = d["step"]
    fails = []

    def check(ok, msg):
        print(("OK    " if ok else "FOUT  ") + msg)
        if not ok:
            fails.append(msg)

    errors = r.check_design()
    check(not errors, "check_design(): " + ("; ".join(errors) or "geen fouten"))

    # 1. Nesting: B in A, C in B, C in A, met minstens CLEARANCE speling.
    outer = {k: Polygon(r.outer_profile(d["lip_t"][k])) for k in "ABC"}
    nest = {"B": (-s, -s), "C": (-2 * s, -2 * s)}
    pairs = [("B", "A"), ("C", "B"), ("C", "A")]
    for inner, host in pairs:
        dy, dz = nest[inner]
        hy, hz = nest.get(host, (0.0, 0.0))
        moved = shifted(outer[inner], dy - hy, dz - hz)
        gap = moved.distance(shape(host))
        check(gap >= r.CLEARANCE - 1e-3,
              f"{inner} in {host}: kleinste speling {gap:.3f} mm (eis {r.CLEARANCE})")

    # 2. Wanddikte van de holle delen.
    for key in "AB":
        lip_t = d["lip_t"][key]
        cav = Polygon(r.cavity_profile(lip_t))
        allowed = Polygon(r.outer_profile(lip_t)).union(box(-100, -100, 100, 0))
        thin = cav.buffer(r.WALL - 0.05).difference(allowed)
        check(thin.area < 1e-6, f"{key}: wanddikte overal >= {r.WALL - 0.05:.2f} mm")

    # 3. In gebruik: identieke zitting en aanslag voor alle drie.
    ta = math.tan(d["a"])
    for key in "ABC":
        pts = r.outer_profile(d["lip_t"][key])
        seat_ok = abs(pts[3][1] - d["seat_z"]) < EPS and abs(pts[3][0]) < EPS
        front_ok = abs(pts[2][1] - (d["seat_z"] - r.SEAT_DEPTH * ta)) < EPS
        check(seat_ok and front_ok, f"{key}: zitting en aanslag op dezelfde plaats")

    # 4. Magneetgaten volledig in elk profiel en in de massieve eindplaat.
    for key in "ABC":
        poly = outer[key]
        for y, z in r.MAG_POS:
            hole = Point(y, z).buffer(r.MAG_HOLE_D / 2)
            margin = poly.exterior.distance(hole) if poly.contains(hole) else -1
            check(margin >= 1.0, f"{key}: magneet ({y}, {z}) rand {margin:.2f} mm")

    # 5. Lengtes.
    L = d["length"]
    check(abs(sum(L.values()) - d["total"]) < EPS,
          f"Totale lengte {sum(L.values()):.2f} mm binnen toetsenbord {r.KB_WIDTH} mm")
    for inner, host in (("B", "A"), ("C", "B")):
        free = L[host] - 2 * r.END_CAP - L[inner]
        check(free >= 2 * r.CLEARANCE - EPS, f"{inner} past in lengte in {host}: {free:.2f} mm vrij")

    print()
    print(f"Zittinghoogte aan aanslag: {d['seat_z']:.2f} mm, voorkant zitting "
          f"{d['seat_z'] - r.SEAT_DEPTH * ta:.2f} mm, lip tot {d['lip_z']:.2f} mm")
    print(f"Lipdiktes A/B/C: {d['lip_t']['A']:.2f} / {d['lip_t']['B']:.2f} / {d['lip_t']['C']:.2f} mm")
    print(f"Lengtes B/A/C: {L['B']:.2f} / {L['A']:.2f} / {L['C']:.2f} mm")
    print(f"Opbergpakket: {L['A']:.1f} x {d['lip_t']['A'] + r.SEAT_DEPTH:.1f} x "
          f"{d['lip_z'] + 2 * s:.1f} mm")

    if len(sys.argv) > 1:
        draw(sys.argv[1], d, nest)
    return 1 if fails else 0


def draw(path, d, nest):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"A": "#3b6ea5", "B": "#d08a2e", "C": "#4f9a6a"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    def fill(ax, poly, color, alpha):
        geoms = getattr(poly, "geoms", [poly])
        for g in geoms:
            y, z = g.exterior.xy
            ax.fill(y, z, color=color, alpha=alpha, lw=0)
            ax.plot(y, z, color=color, lw=1.2)

    ax = axes[0]
    for key in "ABC":
        fill(ax, shape(key), colors[key], 0.25)
    ta = math.tan(d["a"])
    ky = [0, 30]
    ax.plot(ky, [d["seat_z"] - y * ta for y in ky], "k--", lw=0.8)
    ax.text(21, d["seat_z"] - 21 * ta + 0.6, "onderkant toetsenbord", fontsize=8)
    ax.set_title("In gebruik: A, B, C over elkaar gelegd")

    ax = axes[1]
    for key in "ABC":
        dy, dz = nest.get(key, (0.0, 0.0))
        poly = shape(key)
        geoms = getattr(poly, "geoms", [poly])
        moved = [shifted(g, dy, dz) for g in geoms]
        for g in moved:
            fill(ax, g, colors[key], 0.35)
    ax.set_title("Opbergstand: C in B in A")

    for ax in axes:
        ax.axhline(0, color="#888", lw=0.6)
        ax.set_aspect("equal")
        ax.set_xlabel("y (mm), positief = naar voren")
        ax.set_ylabel("z (mm)")
        ax.grid(True, lw=0.3, alpha=0.5)
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k], alpha=0.5) for k in "ABC"]
    fig.legend(handles, ["A midden (hol)", "B links (hol)", "C rechts (massief)"],
               loc="lower center", ncol=3, frameon=False)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, dpi=150)
    print(f"Tekening: {path}")


if __name__ == "__main__":
    sys.exit(main())
