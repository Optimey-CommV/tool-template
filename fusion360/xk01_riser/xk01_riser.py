# SPDX-FileCopyrightText: 2026 Joost Meyfroodt
# SPDX-License-Identifier: GPL-3.0-or-later
"""Driedelige, nestbare verhoging voor het ProtoArc XK01 toetsenbord.

Fusion-script: maakt drie componenten (B links, A midden, C rechts) die in
gebruik op een lijn liggen en voor transport als Russische popjes in elkaar
schuiven. De maten hieronder zijn de enige bron van waarheid: pas ze aan en
draai het script opnieuw. Het script opent telkens een nieuw document.

Assen: X = lengte (links naar rechts), Y = diepte (positief = naar voren,
naar de gebruiker), Z = hoogte boven de tafel. Y = 0 is het aanslagvlak
waar de achterrand van het toetsenbord tegen rust.

De profielberekening gebruikt geen Fusion-API, zodat check_geometry.py
dezelfde code buiten Fusion kan controleren.
"""

import math
import traceback

# --- Toetsenbord (meet je eigen exemplaar na met een schuifmaat) ---------
KB_WIDTH = 386.4      # uitgevouwen breedte XK01
END_MARGIN = 1.0      # balk blijft per zijde zoveel binnen de toetsenbordrand
KB_SPAN = 112.0       # afstand voorste rubberpad (tafelcontact) tot achterrand
TILT_DEG = 6.0        # gewenste helling van het toetsenbord

# --- Profiel ----------------------------------------------------------------
SEAT_DEPTH = 20.0     # diepte van de zitting voor het aanslagvlak
LIP_HEIGHT = 4.0      # hoogte van de achterlip boven de zitting
LIP_CHAMFER = 0.8     # afschuining voorkant lip, max 0.58 x WALL
WALL = 1.6            # wanddikte van de holle delen A en B
CLEARANCE = 0.3       # speling tussen geneste delen (PETG: 0.3 tot 0.35)
LIP_T_C = 3.6         # dikte achterlip van het kleinste (massieve) deel C
END_CAP = 4.0         # dikte van de kopse eindplaten

# --- Magneten (Ø6 x 3 mm neodymium) ----------------------------------------
MAG_HOLE_D = 6.2      # gatdiameter, magneet wordt erin gelijmd
MAG_DEPTH = 3.2       # diepte van het gat
MAG_POS = [(4.0, 4.5), (14.0, 4.5)]  # (y, z) middelpunten op het kopvlak

# --- Optionele uitsparingen voor scharnierbumpers ----------------------------
# Lijst van (x_midden, breedte, diepte) in mm, x gemeten vanaf de linkerrand
# van het toetsenbord. Leeg laten tenzij de scharnieren achteraan uitsteken.
HINGE_NOTCHES = []

# --- Weergave ---------------------------------------------------------------
LAYOUT = "gebruik"    # "gebruik" (op een lijn) of "genest" (opbergstand)


def derived():
    """Alle afgeleide maten op een plek."""
    a = math.radians(TILT_DEG)
    step = WALL + CLEARANCE
    seat_z = KB_SPAN * math.tan(a)
    total = KB_WIDTH - 2 * END_MARGIN
    x_step = 2 * (END_CAP + CLEARANCE)
    len_a = (total + 3 * x_step) / 3
    return {
        "a": a,
        "step": step,
        "seat_z": seat_z,
        "lip_z": seat_z + LIP_HEIGHT,
        "total": total,
        "x_step": x_step,
        "lip_t": {"A": LIP_T_C + 4 * step, "B": LIP_T_C + 2 * step, "C": LIP_T_C},
        "length": {"A": len_a, "B": len_a - x_step, "C": len_a - 2 * x_step},
    }


def parts():
    """Volgorde in gebruik: B links, A midden, C rechts.

    A is het grootste deel en heeft magneten aan beide kanten. B nest in A,
    C nest in B. C is massief.
    """
    d = derived()
    return [
        {"key": "B", "name": "B_links", "hollow": True, "mag_left": False, "mag_right": True},
        {"key": "A", "name": "A_midden", "hollow": True, "mag_left": True, "mag_right": True},
        {"key": "C", "name": "C_rechts", "hollow": False, "mag_left": True, "mag_right": False},
    ], d


def outer_profile(lip_t):
    """Buitencontour (y, z) in mm, tegen de klok in vanaf achteraan onderaan."""
    d = derived()
    ta = math.tan(d["a"])
    zs, zl, df, ch = d["seat_z"], d["lip_z"], SEAT_DEPTH, LIP_CHAMFER
    return [
        (-lip_t, 0.0),
        (df, 0.0),
        (df, zs - df * ta),
        (0.0, zs),
        (0.0, zl - ch),
        (-ch, zl),
        (-lip_t, zl),
    ]


def cavity_profile(lip_t):
    """Binnenruimte van een hol deel, onderaan open (loopt door tot z = -1)."""
    d = derived()
    ta, ca = math.tan(d["a"]), math.cos(d["a"])
    zs, zl, df, t = d["seat_z"], d["lip_z"], SEAT_DEPTH, WALL
    return [
        (-lip_t + t, -1.0),
        (df - t, -1.0),
        (df - t, zs - (df - t) * ta - t / ca),
        (-t, zs + t * ta - t / ca),
        (-t, zl - t),
        (-lip_t + t, zl - t),
    ]


def placements():
    """Positie (x, y, z) van elk deel voor de gekozen LAYOUT."""
    d = derived()
    s, xs = d["step"], END_CAP + CLEARANCE
    if LAYOUT == "genest":
        return {"A": (0.0, 0.0, 0.0), "B": (xs, -s, -s), "C": (2 * xs, -2 * s, -2 * s)}
    x_b = END_MARGIN
    x_a = x_b + d["length"]["B"]
    x_c = x_a + d["length"]["A"]
    return {"B": (x_b, 0.0, 0.0), "A": (x_a, 0.0, 0.0), "C": (x_c, 0.0, 0.0)}


def check_design():
    """Snelle controles zonder externe bibliotheken. Geeft een lijst fouten."""
    d = derived()
    errors = []
    zs, ta = d["seat_z"], math.tan(d["a"])
    front_z = zs - SEAT_DEPTH * ta
    if LIP_CHAMFER > 0.58 * WALL:
        errors.append("LIP_CHAMFER te groot: de wand van A en B wordt dunner dan WALL.")
    if LIP_T_C < 3.0:
        errors.append("LIP_T_C kleiner dan 3 mm: de lip van C wordt te zwak.")
    if END_CAP < MAG_DEPTH + 0.6:
        errors.append("END_CAP te dun voor MAG_DEPTH (minder dan 0.6 mm bodem).")
    if front_z - WALL < 3.0:
        errors.append("Zitting vooraan te laag voor een holle doorsnede.")
    r = MAG_HOLE_D / 2
    for y, z in MAG_POS:
        if y - r < -LIP_T_C + 1.0 or y + r > SEAT_DEPTH - 1.0:
            errors.append(f"Magneet op y={y} valt (bijna) buiten de diepte van deel C.")
        seat_here = zs - (y + r) * ta
        if z - r < 1.0 or z + r > seat_here - 1.0:
            errors.append(f"Magneet op z={z} valt (bijna) buiten de hoogte van deel C.")
    if LAYOUT not in ("gebruik", "genest"):
        errors.append('LAYOUT moet "gebruik" of "genest" zijn.')
    return errors


# ---------------------------------------------------------------------------
# Fusion-gedeelte. Interne eenheid van de API is centimeter.
# ---------------------------------------------------------------------------

def _cm(v):
    return v / 10.0


def _sketch_at(comp, base_plane, axis, offset):
    """Schets op een vlak evenwijdig aan base_plane, op 'offset' mm langs 'axis'."""
    import adsk.core
    normal = base_plane.geometry.normal
    sign = 1.0 if normal.dotProduct(axis) > 0 else -1.0
    if abs(offset) < 1e-9:
        plane = base_plane
    else:
        inp = comp.constructionPlanes.createInput()
        inp.setByOffset(base_plane, adsk.core.ValueInput.createByReal(_cm(offset * sign)))
        plane = comp.constructionPlanes.add(inp)
        plane.isLightBulbOn = False
    return comp.sketches.add(plane)


def _pt(sk, x, y, z):
    import adsk.core
    return sk.modelToSketchSpace(adsk.core.Point3D.create(_cm(x), _cm(y), _cm(z)))


def _polygon_yz(sk, x, pts):
    lines = sk.sketchCurves.sketchLines
    p = [_pt(sk, x, y, z) for y, z in pts]
    for i in range(len(p)):
        lines.addByTwoPoints(p[i], p[(i + 1) % len(p)])


def _extrude(comp, sk, axis, length, operation, body=None):
    """Extrudeer alle profielen van sk over 'length' mm langs 'axis' (teken = richting)."""
    import adsk.core
    import adsk.fusion
    profiles = adsk.core.ObjectCollection.create()
    for i in range(sk.profiles.count):
        profiles.add(sk.profiles.item(i))
    normal = sk.xDirection.crossProduct(sk.yDirection)
    forward = normal.dotProduct(axis) * length > 0
    direction = (adsk.fusion.ExtentDirections.PositiveExtentDirection if forward
                 else adsk.fusion.ExtentDirections.NegativeExtentDirection)
    extrudes = comp.features.extrudeFeatures
    inp = extrudes.createInput(profiles, operation)
    dist = adsk.fusion.DistanceExtentDefinition.create(
        adsk.core.ValueInput.createByReal(_cm(abs(length))))
    inp.setOneSideExtent(dist, direction)
    if body is not None:
        inp.participantBodies = [body]
    return extrudes.add(inp)


def _build_part(root, spec, d, pos):
    import adsk.core
    import adsk.fusion
    key = spec["key"]
    lip_t, length = d["lip_t"][key], d["length"][key]
    x_axis = adsk.core.Vector3D.create(1, 0, 0)
    z_axis = adsk.core.Vector3D.create(0, 0, 1)
    new_body = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    cut = adsk.fusion.FeatureOperations.CutFeatureOperation

    m = adsk.core.Matrix3D.create()
    m.translation = adsk.core.Vector3D.create(_cm(pos[0]), _cm(pos[1]), _cm(pos[2]))
    occ = root.occurrences.addNewComponent(m)
    comp = occ.component
    comp.name = spec["name"]
    yz = comp.yZConstructionPlane

    sk = _sketch_at(comp, yz, x_axis, 0.0)
    sk.name = "buitenprofiel"
    _polygon_yz(sk, 0.0, outer_profile(lip_t))
    body = _extrude(comp, sk, x_axis, length, new_body).bodies.item(0)
    body.name = spec["name"]

    if spec["hollow"]:
        sk = _sketch_at(comp, yz, x_axis, END_CAP)
        sk.name = "holte"
        _polygon_yz(sk, END_CAP, cavity_profile(lip_t))
        _extrude(comp, sk, x_axis, length - 2 * END_CAP, cut, body)

    for side, x, sign in (("mag_left", 0.0, 1), ("mag_right", length, -1)):
        if not spec[side]:
            continue
        sk = _sketch_at(comp, yz, x_axis, x)
        sk.name = "magneten links" if sign > 0 else "magneten rechts"
        for y, z in MAG_POS:
            sk.sketchCurves.sketchCircles.addByCenterRadius(_pt(sk, x, y, z), _cm(MAG_HOLE_D / 2))
        _extrude(comp, sk, x_axis, sign * MAG_DEPTH, cut, body)

    x0 = pos[0] if LAYOUT == "gebruik" else None
    if x0 is not None:
        for xc, width, depth in HINGE_NOTCHES:
            lo = max(xc - width / 2 - x0, 0.0)
            hi = min(xc + width / 2 - x0, length)
            if hi <= lo:
                continue
            sk = _sketch_at(comp, comp.xYConstructionPlane, z_axis, d["seat_z"])
            sk.name = "scharnieruitsparing"
            sk.sketchCurves.sketchLines.addTwoPointRectangle(
                _pt(sk, lo, -depth, d["seat_z"]), _pt(sk, hi, 0.5, d["seat_z"]))
            _extrude(comp, sk, z_axis, LIP_HEIGHT + 1.0, cut, body)
    return comp


def run(context):
    import adsk.core
    import adsk.fusion
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        errors = check_design()
        if errors:
            ui.messageBox("Ontwerp klopt niet:\n\n" + "\n".join(errors))
            return
        if LAYOUT == "genest" and HINGE_NOTCHES:
            ui.messageBox("Let op: scharnieruitsparingen worden alleen in LAYOUT "
                          "\"gebruik\" gemaakt.")

        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent

        specs, d = parts()
        pos = placements()
        for spec in specs:
            _build_part(root, spec, d, pos[spec["key"]])

        L = d["length"]
        ui.messageBox(
            "Klaar ({}).\n\n"
            "Hoogte zitting aan aanslag: {:.2f} mm\n"
            "Lengtes: B {:.2f} / A {:.2f} / C {:.2f} mm (samen {:.2f})\n"
            "Opbergpakket: {:.1f} x {:.1f} x {:.1f} mm\n\n"
            "Controleer de opbergstand met LAYOUT = \"genest\" en Inspect > Interference."
            .format(LAYOUT, d["seat_z"], L["B"], L["A"], L["C"], sum(L.values()),
                    L["A"], d["lip_t"]["A"] + SEAT_DEPTH, d["lip_z"] + 2 * d["step"]))
    except Exception:
        ui.messageBox("Fout:\n" + traceback.format_exc())


def stop(context):
    pass
