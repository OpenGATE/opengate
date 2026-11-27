#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GateImageMaskSolid: the solid of an image volume with an outside (the
union of the inside voxels of a grid, a staircase). No simulation: the
geometry methods of the solid are compared to a brute force reference
(each inside voxel as a box), on several masks (one voxel, two voxels
by an edge, an L, a ring, a sphere with a cavity, random voxels with an
anisotropic spacing, all inside, all outside):
- Inside of random points
- DistanceToIn(p, v) from the outside and from the surface, DistanceToOut(p,
  v) from the inside and from the surface: random rays, and rays from the
  nodes, edges and faces of the grid along the axes and the diagonals
  (along the faces, through the edges and the corners)
- the consistency: p + DistanceToIn v is on the surface
- the safeties (DistanceToIn(p), DistanceToOut(p)) are lower bounds
- GetPointOnSurface and SurfaceNormal, the volume and the area
Convention along a face between an inside and an outside voxel (ray
parallel to the face): from the outside the ray does not enter, from the
inside it does not exit.
"""

import time
import numpy as np
import opengate_core as g4
from opengate.image import compute_outside_distance_map
from opengate.tests import utility

K_OUTSIDE, K_SURFACE, K_INSIDE = 0, 1, 2
INF = 1e90
EPS = 1e-7  # mm, tolerance of the reference


def make_solid(name, inside, spacing):
    """inside: (z, y, x) bool; spacing: (x, y, z)"""
    s = g4.GateImageMaskSolid(name)
    nz, ny, nx = inside.shape
    d = compute_outside_distance_map(inside, spacing)
    s.SetMask([nx, ny, nz], list(spacing), inside.astype(np.uint8), d)
    return s


class Reference:
    """Brute force: each inside voxel is a box."""

    def __init__(self, inside, spacing):
        self.spacing = np.asarray(spacing, dtype=float)
        nz, ny, nx = inside.shape
        self.size = np.array([nx, ny, nz])
        self.half = 0.5 * self.size * self.spacing
        self.inside = inside
        k, j, i = np.nonzero(inside)
        idx = np.stack([i, j, k], axis=1)
        self.lo = -self.half + idx * self.spacing
        self.hi = self.lo + self.spacing
        k, j, i = np.nonzero(~inside)
        idx = np.stack([i, j, k], axis=1)
        self.out_lo = -self.half + idx * self.spacing
        self.out_hi = self.out_lo + self.spacing

    def intervals(self, p, v, strict):
        """the [te, tx] of the ray in each inside voxel (positive length).
        strict: for a ray parallel to a face, the ray must be strictly
        inside the slab (DistanceToIn); otherwise on the face counts
        (DistanceToOut)."""
        with np.errstate(divide="ignore", invalid="ignore"):
            ta = (self.lo - p) / v
            tb = (self.hi - p) / v
        t0 = np.minimum(ta, tb)
        t1 = np.maximum(ta, tb)
        par = v == 0
        if par.any():
            a = np.nonzero(par)[0]
            if strict:
                ok = self.strict_lanes(p, a)
            else:
                ok = (self.lo[:, a] - EPS <= p[a]) & (p[a] <= self.hi[:, a] + EPS)
                ok = ok.all(axis=1)
            t0[:, a] = -np.inf
            t1[:, a] = np.inf
        else:
            ok = np.ones(len(self.lo), dtype=bool)
        te = t0.max(axis=1)
        tx = t1.min(axis=1)
        ok &= tx - te > EPS
        return te[ok], tx[ok]

    def strict_lanes(self, p, axes):
        """for a ray parallel to the axes: the inside voxels whose lane
        contains the ray in the interior of the union. Strictly inside the
        slab, or on the lower plane of the voxel with all the voxels of the
        lane (below along these axes) inside."""
        ok = np.ones(len(self.lo), dtype=bool)
        below = []
        for a in axes:
            strictly = (self.lo[:, a] + EPS < p[a]) & (p[a] < self.hi[:, a] - EPS)
            on_lo = np.abs(self.lo[:, a] - p[a]) <= EPS
            ok &= strictly | on_lo
            below.append(on_lo)
        idx = np.round((self.lo + self.half) / self.spacing).astype(int)
        for n in range(len(self.lo)):
            if not ok[n]:
                continue
            on = [a for a, b in zip(axes, below) if b[n]]
            for m in range(1, 2 ** len(on)):
                w = idx[n].copy()
                for bit, a in enumerate(on):
                    if m >> bit & 1:
                        w[a] -= 1
                if not self.is_in(w):
                    ok[n] = False
                    break
        return ok

    def is_in(self, w):
        if (w < 0).any() or (w >= self.size).any():
            return False
        return bool(self.inside[w[2], w[1], w[0]])

    def distance_to_in(self, p, v):
        te, tx = self.intervals(p, v, True)
        m = tx > EPS
        if not m.any():
            return INF
        return max(0.0, te[m].min())

    def distance_to_out(self, p, v):
        te, tx = self.intervals(p, v, False)
        order = np.argsort(te)
        te, tx = te[order], tx[order]
        end = 0.0
        started = False
        for a, b in zip(te, tx):
            if a > end + EPS:
                break
            if b > end + EPS:
                end = b
                started = True
        return end if started else 0.0

    @staticmethod
    def box_distance(p, lo, hi):
        e = np.maximum(np.maximum(lo - p, 0), p - hi)
        return np.sqrt((e**2).sum(axis=1))

    def safety_in(self, p):
        if len(self.lo) == 0:
            return INF
        return self.box_distance(p, self.lo, self.hi).min()

    def safety_out(self, p):
        d = (self.half - np.abs(p)).min()  # the border of the box
        if len(self.out_lo):
            d = min(d, self.box_distance(p, self.out_lo, self.out_hi).min())
        return d


def random_directions(rng, n):
    v = rng.normal(size=(n, 3))
    return v / np.linalg.norm(v, axis=1)[:, None]


def lattice_directions():
    d = []
    for a in range(3):
        for s in (-1, 1):
            e = np.zeros(3)
            e[a] = s
            d.append(e)
    for a in range(3):
        for b in range(a + 1, 3):
            for sa in (-1, 1):
                for sb in (-1, 1):
                    e = np.zeros(3)
                    e[a], e[b] = sa, sb
                    d.append(e / np.sqrt(2))
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                d.append(np.array([sx, sy, sz]) / np.sqrt(3))
    return np.array(d)


def lattice_points(ref, rng, n):
    """grid nodes, edge middles and face centres (in and around the box)"""
    pts = []
    for _ in range(n):
        idx = rng.integers(-1, ref.size + 2)
        frac = rng.choice([0.0, 0.5], size=3)
        pts.append(-ref.half + (idx + frac) * ref.spacing)
    return np.array(pts)


def compare(name, values, refs, what):
    values = np.asarray(values)
    refs = np.asarray(refs)
    both_inf = (values > 1e90) & (refs > 1e80)
    err = np.where(both_inf, 0, np.abs(values - refs))
    bad = err > 1e-6
    b = not bad.any()
    msg = f"{name}: {what}, {len(values)} rays, max error {err.max():.1e} mm"
    if not b:
        i = np.nonzero(bad)[0][:3]
        msg += f" BAD: {bad.sum()}, e.g. {values[i]} vs {refs[i]}"
    utility.print_test(b, msg)
    return b


def check_mask(name, inside, spacing, rng, n_random=1500, n_lattice=400):
    is_ok = True
    s = make_solid(name, inside, spacing)
    ref = Reference(inside, spacing)
    vox = np.prod(spacing)

    # volume and area
    nin = int(inside.sum())
    padded = np.pad(inside, 1)
    area = 0.0
    sx, sy, sz = spacing
    for axis, a in zip((2, 1, 0), (sy * sz, sx * sz, sx * sy)):
        area += np.abs(np.diff(padded.astype(int), axis=axis)).sum() * a
    b = np.isclose(s.GetCubicVolume(), nin * vox) and np.isclose(
        s.GetSurfaceArea(), area
    )
    utility.print_test(
        b,
        f"{name}: {inside.shape[::-1]} voxels, {nin} inside, volume "
        f"{s.GetCubicVolume():.1f} area {s.GetSurfaceArea():.1f} mm2",
    )
    is_ok = is_ok and b

    # Inside of random points (in the box and around)
    p = rng.uniform(-ref.half - 2 * ref.spacing, ref.half + 2 * ref.spacing, (5000, 3))
    ins = s.inside(p)
    idx = np.floor((p + ref.half) / ref.spacing).astype(int)
    inb = ((idx >= 0) & (idx < ref.size)).all(axis=1)
    expected = np.zeros(len(p), dtype=int)
    ii = idx[inb]
    expected[inb] = np.where(inside[ii[:, 2], ii[:, 1], ii[:, 0]], K_INSIDE, K_OUTSIDE)
    b = (ins == expected).all()
    utility.print_test(b, f"{name}: Inside of {len(p)} random points")
    is_ok = is_ok and b

    # random rays and lattice rays
    dirs_lat = lattice_directions()
    p_lat = lattice_points(ref, rng, n_lattice)
    p_lat = np.repeat(p_lat, 3, axis=0)
    v_lat = dirs_lat[rng.integers(0, len(dirs_lat), len(p_lat))]
    p_rnd = rng.uniform(
        -ref.half - 2 * ref.spacing, ref.half + 2 * ref.spacing, (n_random, 3)
    )
    v_rnd = random_directions(rng, n_random)
    for label, pp, vv in (("random", p_rnd, v_rnd), ("lattice", p_lat, v_lat)):
        ins = s.inside(pp)
        # DistanceToIn from the outside and the surface
        m = ins != K_INSIDE
        if m.any():
            d = s.distance_to_in(pp[m], vv[m])
            r = [ref.distance_to_in(a, b) for a, b in zip(pp[m], vv[m])]
            is_ok = compare(name, d, r, f"DistanceToIn(p, v) {label}") and is_ok
            # consistency: p + d v is on the surface
            f = d < 1e90
            if f.any():
                q = pp[m][f] + d[f, None] * vv[m][f]
                b = (s.inside(q) == K_SURFACE).all()
                utility.print_test(
                    b, f"{name}: p + DistanceToIn v on the surface ({f.sum()})"
                )
                is_ok = is_ok and b
        # DistanceToOut from the inside and the surface
        m = ins != K_OUTSIDE
        if m.any():
            d, n = s.distance_to_out(pp[m], vv[m])
            r = [ref.distance_to_out(a, b) for a, b in zip(pp[m], vv[m])]
            is_ok = compare(name, d, r, f"DistanceToOut(p, v) {label}") and is_ok
            # the exit normal: unit, and the ray goes out through it
            nn = np.linalg.norm(n, axis=1)
            b = np.allclose(nn, 1) and ((n * vv[m]).sum(axis=1) > 0).all()
            utility.print_test(b, f"{name}: exit normals ({label})")
            is_ok = is_ok and b

    # safeties: lower bounds of the distance to the inside / outside
    ins = s.inside(p_rnd)
    m = ins == K_OUTSIDE
    if m.any():
        sf = s.safety_to_in(p_rnd[m])
        r = np.array([ref.safety_in(a) for a in p_rnd[m]])
        b = (sf <= r + 1e-9).all()
        utility.print_test(
            b,
            f"{name}: DistanceToIn(p) <= true distance ({m.sum()} points, "
            f"mean ratio {np.mean(sf / np.maximum(r, 1e-12)):.2f})",
        )
        is_ok = is_ok and b
    m = ins == K_INSIDE
    if m.any():
        sf = s.safety_to_out(p_rnd[m])
        r = np.array([ref.safety_out(a) for a in p_rnd[m]])
        b = (sf <= r + 1e-9).all()
        utility.print_test(
            b,
            f"{name}: DistanceToOut(p) <= true distance ({m.sum()} points, "
            f"mean ratio {np.mean(sf / np.maximum(r, 1e-12)):.2f})",
        )
        is_ok = is_ok and b

    # points on the surface and normals
    if nin > 0:
        q = s.points_on_surface(1000)
        n = s.surface_normal(q)
        b = (s.inside(q) == K_SURFACE).all()
        b = b and np.allclose(np.linalg.norm(n, axis=1), 1)
        b = b and (s.inside(q + 1e-3 * n) == K_OUTSIDE).mean() > 0.99
        b = b and (s.inside(q - 1e-3 * n) == K_INSIDE).mean() > 0.99
        utility.print_test(b, f"{name}: GetPointOnSurface and SurfaceNormal")
        is_ok = is_ok and b
        # from the surface: going out, the next entry (never 0); going in, 0
        v = random_directions(rng, len(q))
        out = (v * n).sum(axis=1) > 0
        d = s.distance_to_in(q, v)
        r = np.array([ref.distance_to_in(a, b) for a, b in zip(q, v)])
        is_ok = compare(name, d, r, "DistanceToIn(p, v) from the surface") and is_ok
        b = (d[out] > 0).all() and (d[~out] == 0).all()
        utility.print_test(b, f"{name}: from the surface, out: > 0, in: 0")
        is_ok = is_ok and b
    return is_ok


def masks(rng):
    m = {}
    a = np.zeros((5, 5, 5), dtype=bool)
    a[2, 2, 2] = True
    m["one voxel"] = (a, (2.0, 2.0, 2.0))
    a = np.zeros((4, 4, 4), dtype=bool)
    a[1, 1, 1] = a[1, 2, 2] = True
    m["two voxels by an edge"] = (a, (1.0, 1.0, 1.0))
    a = np.zeros((6, 6, 6), dtype=bool)
    a[1:5, 1:5, 1:3] = True
    a[1:5, 1:3, 1:5] = True
    m["L"] = (a, (1.5, 1.5, 1.5))
    a = np.zeros((4, 8, 8), dtype=bool)
    a[1:3, 1:7, 1:7] = True
    a[1:3, 3:5, 3:5] = False
    m["ring"] = (a, (1.0, 1.0, 2.0))
    z, y, x = np.mgrid[0:16, 0:16, 0:16] - 7.5
    r = np.sqrt(x**2 + y**2 + z**2)
    m["sphere with a cavity"] = ((r < 7) & (r > 3), (1.0, 1.0, 1.0))
    m["random, anisotropic"] = (rng.random((8, 9, 10)) < 0.5, (1.0, 2.0, 3.5))
    m["all inside"] = (np.ones((6, 5, 4), dtype=bool), (1.0, 1.0, 1.0))
    m["all outside"] = (np.zeros((6, 5, 4), dtype=bool), (1.0, 1.0, 1.0))
    return m


def timing(rng):
    """DistanceToIn(p, v) on a large mask, with and without the jumps of
    the distance map (information only)."""
    n = 128
    z, y, x = np.mgrid[0:n, 0:n, 0:n] - (n - 1) / 2
    inside = np.sqrt(x**2 + y**2 + z**2) < n / 6
    spacing = (2.0, 2.0, 2.0)
    s = make_solid("timing", inside, spacing)
    s0 = g4.GateImageMaskSolid("timing_no_map")
    s0.SetMask(
        [n, n, n],
        list(spacing),
        inside.astype(np.uint8),
        np.zeros(inside.shape, dtype=np.float32),
    )
    m = 200000
    p = rng.uniform(-n, n, (m, 3))
    p = p[s.inside(p) == K_OUTSIDE]
    v = random_directions(rng, len(p))
    t = time.time()
    d1 = s.distance_to_in(p, v)
    t1 = time.time() - t
    t = time.time()
    d0 = s0.distance_to_in(p, v)
    t0 = time.time() - t
    both_inf = (d0 > 1e90) & (d1 > 1e90)
    b = (np.where(both_inf, 0, np.abs(d0 - d1)) < 1e-9).all()
    utility.print_test(
        b,
        f"timing: {len(p)} rays, {n}^3 voxels, DistanceToIn(p, v) "
        f"{t1 / len(p) * 1e9:.0f} ns with the distance map, "
        f"{t0 / len(p) * 1e9:.0f} ns without (same results)",
    )
    return b


if __name__ == "__main__":
    rng = np.random.default_rng(12345)
    is_ok = True
    for name, (inside, spacing) in masks(rng).items():
        is_ok = check_mask(name, inside, spacing, rng) and is_ok
    is_ok = timing(rng) and is_ok
    utility.test_ok(is_ok)
