#!/usr/bin/env python3
"""Convert lowpoly_blahaj.3mf into a compile-time C header for the DOS demo.

The 3mf is a zip; the mesh lives in 3D/Objects/Object_1_1.model as plain XML
(<vertices>/<triangles>). The outer 3D/3dmodel.model has a <build><item
transform=...> that is print-BED PLACEMENT, not a meaningful orientation, so
it is ignored entirely -- we take the component's own coordinate space and
choose our own resting pose via BAKE_ROT below.

Output is a header of static arrays rather than an .obj parsed at runtime:
the mesh never changes, and this keeps the DOS side free of any file I/O and
float-parsing (fscanf %f) risk. Run once by hand; commit the generated header.
"""

import math
import os
import zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_3MF = os.path.join(os.path.dirname(HERE), "..", "owc_djgpp_allegro",
                       "lowpoly_blahaj.3mf")
OUT_H = os.path.join(os.path.dirname(HERE), "src", "SHARK.H")

# A textured version of the same sculpt (same 154-vertex mesh -- confirmed by
# nearest-point matching in normalized space, residual ~1e-5 -- just exported
# with a different vertex order and no shared index scheme with the 3mf).
# Used to sample the real paint job per vertex instead of guessing it.
REF_DIR = os.path.join(os.path.dirname(HERE), "reference")
REF_OBJ = os.path.join(REF_DIR, "blahaj.obj")
REF_TEX = os.path.join(REF_DIR, "texture.001.png")

# Longest bbox axis is scaled to this, to sit in the same visual range as the
# sibling cube demo's unit cube (cam_d=4.5, fov=260).
TARGET_EXTENT = 2.8

# Corrective rotation (radians, applied X then Y then Z) baked into the
# vertex data so the runtime only ever applies the demo's own spin. Tuned by
# eye against real screenshots -- see the plan's verification loop.
BAKE_ROT = (-math.pi / 2.0, 0.0, 0.0)


def load_mesh(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("3D/Objects/Object_1_1.model")
    root = ET.fromstring(xml)

    verts = [(float(v.get("x")), float(v.get("y")), float(v.get("z")))
             for v in root.iter(NS + "vertex")]
    tris = [(int(t.get("v1")), int(t.get("v2")), int(t.get("v3")))
            for t in root.iter(NS + "triangle")]
    return verts, tris


def rotate(p, rot):
    x, y, z = p
    rx, ry, rz = rot
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return (x, y, z)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def normalize(v):
    n = math.sqrt(dot(v, v))
    if n < 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def face_normal(verts, tri):
    a, b, c = (verts[i] for i in tri)
    return normalize(cross(sub(b, a), sub(c, a)))



TOP_COLOR    = (75.0, 133.0, 149.0)
BELLY_COLOR  = (255.0, 255.0, 255.0)
BLEND_LO, BLEND_HI = -0.18, 0.10   # baked Y range the fallback blend uses

def smoothstep(lo, hi, x):
    t = 0.0 if x <= lo else 1.0 if x >= hi else (x - lo) / (hi - lo)
    return t * t * (3.0 - 2.0 * t)

def body_albedo_fallback(y):
    t = smoothstep(BLEND_LO, BLEND_HI, y)
    return tuple(BELLY_COLOR[i] + (TOP_COLOR[i] - BELLY_COLOR[i]) * t for i in range(3))


def load_reference_obj(path):
    """Parse just enough of a Blender-exported OBJ: vertex positions, and
    for each vertex position the (u, v) it was unwrapped to, averaged across
    every face that touches it (a vertex can carry more than one UV across a
    seam; averaging is a fine approximation for a mesh this low-poly)."""
    positions = []
    uvs = []
    uv_sum = {}
    uv_n = {}
    with open(path) as f:
        for line in f:
            if line.startswith("v "):
                p = line.split()
                positions.append(tuple(float(x) for x in p[1:4]))
            elif line.startswith("vt "):
                p = line.split()
                uvs.append((float(p[1]), float(p[2])))
            elif line.startswith("f "):
                for tok in line.split()[1:]:
                    parts = tok.split("/")
                    vi = int(parts[0]) - 1
                    if len(parts) > 1 and parts[1]:
                        ti = int(parts[1]) - 1
                        u, v = uvs[ti]
                        s = uv_sum.get(vi, (0.0, 0.0))
                        uv_sum[vi] = (s[0] + u, s[1] + v)
                        uv_n[vi] = uv_n.get(vi, 0) + 1
    vert_uv = [(uv_sum[i][0] / uv_n[i], uv_sum[i][1] / uv_n[i]) if i in uv_n
              else (0.0, 0.0) for i in range(len(positions))]
    return positions, vert_uv


def load_reference_colors(verts_raw):
    """Per-vertex albedo for `verts_raw` (this session's raw, un-baked 3mf
    vertices) sampled from the reference texture, matched by nearest point
    in a shared centered/unit-scaled space. Returns None (caller should fall
    back to body_albedo_fallback) if the reference assets aren't available.
    """
    try:
        from PIL import Image
    except ImportError:
        print("PIL not available -- falling back to the Y-based body colour")
        return None
    if not (os.path.isfile(REF_OBJ) and os.path.isfile(REF_TEX)):
        print("reference OBJ/texture not found -- falling back to the "
             "Y-based body colour")
        return None

    ref_pos, ref_uv = load_reference_obj(REF_OBJ)

    def normalize_cloud(vs):
        lo = [min(v[i] for v in vs) for i in range(3)]
        hi = [max(v[i] for v in vs) for i in range(3)]
        c = [(lo[i] + hi[i]) / 2.0 for i in range(3)]
        diag = math.sqrt(sum((hi[i] - lo[i]) ** 2 for i in range(3)))
        return [tuple((v[i] - c[i]) / diag for i in range(3)) for v in vs]

    a = normalize_cloud(verts_raw)
    b = normalize_cloud(ref_pos)

    img = Image.open(REF_TEX).convert("RGB")
    w, h = img.size

    albedo = []
    max_d2 = 0.0
    for p in a:
        best_i, best_d2 = 0, None
        for j, q in enumerate(b):
            d2 = sum((p[k] - q[k]) ** 2 for k in range(3))
            if best_d2 is None or d2 < best_d2:
                best_d2, best_i = d2, j
        max_d2 = max(max_d2, best_d2)
        u, v = ref_uv[best_i]
        px = min(w - 1, max(0, int(u * w)))
        py = min(h - 1, max(0, int((1.0 - v) * h)))
        r, g, bl = img.getpixel((px, py))
        albedo.append((float(r), float(g), float(bl)))

    print(f"reference colour match: worst nearest-point distance "
          f"{math.sqrt(max_d2):.5f} (normalized space)")
    return albedo


def main():
    verts, tris = load_mesh(SRC_3MF)
    print(f"parsed {len(verts)} vertices, {len(tris)} triangles")

    # Recenter on the bbox center, then scale the longest axis to TARGET_EXTENT.
    lo = [min(v[i] for v in verts) for i in range(3)]
    hi = [max(v[i] for v in verts) for i in range(3)]
    print(f"raw bbox: x[{lo[0]:.2f},{hi[0]:.2f}] "
          f"y[{lo[1]:.2f},{hi[1]:.2f}] z[{lo[2]:.2f},{hi[2]:.2f}]")

    verts_raw = verts   # kept for reference-texture matching below, which
                        # does its own centering/scaling and would be thrown
                        # off by BAKE_ROT's rotation if given the baked verts

    center = [(lo[i] + hi[i]) / 2.0 for i in range(3)]
    scale = TARGET_EXTENT / max(hi[i] - lo[i] for i in range(3))
    verts = [rotate(tuple((v[i] - center[i]) * scale for i in range(3)), BAKE_ROT)
             for v in verts]

    lo = [min(v[i] for v in verts) for i in range(3)]
    hi = [max(v[i] for v in verts) for i in range(3)]
    print(f"baked bbox: x[{lo[0]:.2f},{hi[0]:.2f}] "
          f"y[{lo[1]:.2f},{hi[1]:.2f}] z[{lo[2]:.2f},{hi[2]:.2f}]")


    directed = set()
    consistent = True
    for a, b, c in tris:
        for e in ((a, b), (b, c), (c, a)):
            if e in directed:
                consistent = False
            directed.add(e)
    if not consistent or any((b, a) not in directed for (a, b) in directed):
        raise SystemExit("mesh is not a consistently wound closed manifold; "
                         "per-triangle repair would be needed")

    volume = sum(dot(verts[a], cross(verts[b], verts[c])) / 6.0
                 for a, b, c in tris)
    if volume < 0:
        tris = [(a, c, b) for a, b, c in tris]
        print(f"winding: consistent but inward (vol {volume:.3f}) -- flipped all")
    else:
        print(f"winding: consistent and already outward (vol {volume:.3f})")

    # Smooth vertex normals (area-weighted by using unnormalized face normals)
    # baked here so the runtime only has to rotate them, never rebuild them.
    accum = [[0.0, 0.0, 0.0] for _ in verts]
    for tri in tris:
        a, b, c = (verts[i] for i in tri)
        fn = cross(sub(b, a), sub(c, a))
        for i in tri:
            for k in range(3):
                accum[i][k] += fn[k]
    normals = [normalize(tuple(n)) for n in accum]

    degenerate = sum(1 for n in normals if n == (0.0, 0.0, 0.0))
    if degenerate:
        print(f"WARNING: {degenerate} vertices had a degenerate normal")

    albedo = load_reference_colors(verts_raw)
    if albedo is None:
        albedo = [body_albedo_fallback(v[1]) for v in verts]

    with open(OUT_H, "w") as f:
        f.write(f"""\
/* SHARK.H -- generated by tools/convert_blahaj.py, do not edit by hand.
 *
 * Low-poly Blahaj mesh baked out of lowpoly_blahaj.3mf:
 * Shark's License:  CC AttributionCreative Commons Attribution
 * Sharks author : IsabelleDotJpeg https://sketchfab.com/3d-models/low-poly-blahaj-5ac23e0cd44d49dcaaa14967f7d7a778
 */

#ifndef SHARK_H
#define SHARK_H

#define SHARK_NVERTS {len(verts)}
#define SHARK_NTRIS  {len(tris)}

static const float g_shark_verts[SHARK_NVERTS][3] = {{
""")
        for v in verts:
            f.write("    {%9.5ff, %9.5ff, %9.5ff},\n" % v)
        f.write("};\n\nstatic const float g_shark_normals[SHARK_NVERTS][3] = {\n")
        for n in normals:
            f.write("    {%9.5ff, %9.5ff, %9.5ff},\n" % n)
        f.write("};\n\nstatic const float g_shark_albedo[SHARK_NVERTS][3] = {\n")
        for c in albedo:
            f.write("    {%6.1ff, %6.1ff, %6.1ff},\n" % c)
        f.write("};\n\nstatic const int g_shark_tris[SHARK_NTRIS][3] = {\n")
        for t in tris:
            f.write("    {%3d, %3d, %3d},\n" % t)
        f.write("};\n\n#endif  /* SHARK_H */\n")

    print(f"wrote {OUT_H}")


if __name__ == "__main__":
    main()
