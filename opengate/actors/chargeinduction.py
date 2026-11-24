"""
Tables of the charge induced on the pixels of a semiconductor detector with
a pixelated anode (e.g. CZT), used by DigitizerChargeInductionActor.

A deposit of energy E at depth z (distance to the cathode) and at (dx, dy)
relative to the centre of a pixel gives to this pixel the signal
E x eta(z, dx, dy), with two tables:

- eta_own: for the pixel of the deposit;
- eta_neighbour: for the other pixels (can be negative).

Two tables because the weighting potential jumps at the edge of the pad on
the anode plane. Both cover 3 x 3 pixels around the pixel centre.

The tables are computed from:
- the weighting potential of one pad (Laplace equation between the cathode
  and the anode planes, solved by Fourier series on a period of several
  pixels; rectangular pads, optionally smaller than the pitch: gaps between
  the pads);
- the drift of the electrons to the anode and of the holes to the cathode,
  each with a mean path before trapping (Hecht-like, along the weighting
  potential: Shockley-Ramo);
- an optional Gaussian charge cloud shared between the pads (applied to the
  electrons that reach the anode). This term is separable: it is given as
  three 1D tables on a fine grid (cloud_x, cloud_y: share of the cloud on
  the pad along each axis; cloud_z: share of the electrons that reach the
  anode), and the actor adds (cloud_x(dx) cloud_y(dy) - own) cloud_z(z) to
  eta (own: 1 for eta_own, 0 for eta_neighbour). A 3D table could not
  resolve the edge of the pad for a cloud of ~0.1 mm.

With no trapping of the electrons, holes that do not move and no cloud:
eta_own = 1 - phi, eta_neighbour = -phi (phi: weighting potential of the
pixel at the deposit).

The electrons that reach the anode are assumed to be collected by the pad
of the pixel cell (pitch x pitch) they drift in, also when the pad is
smaller than the pitch (the field steers them to the pad): with gaps, only
the induction during the drift changes, there is no charge lost in the gaps.

All lengths are in Geant4 internal units (mm).
"""

from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.special import erf

from ..exception import fatal


def weighting_potential(pitch, thickness, n=512, n_period=16, n_z=121, pad_size=None):
    """
    Weighting potential of one rectangular anode pad (sides: pad_size, by
    default the pitch, i.e. no gap) of a crystal between two planes: 1 on the
    pad, 0 on the rest of the anode plane and on the cathode. Solved by
    Fourier series on a period of n_period x n_period pixels sampled on n x n
    cells.

    Return z (n_z nodes from 0 at the cathode to thickness at the anode),
    x, y (centres of the cells, three pixels wide, the pad in the middle)
    and phi (z, x, y).
    """
    px, py = pitch
    ax, ay = pitch if pad_size is None else pad_size
    d = thickness
    dx, dy = n_period * px / n, n_period * py / n
    x = (np.arange(n) - n // 2) * dx + dx / 2
    y = (np.arange(n) - n // 2) * dy + dy / 2
    pad = (np.abs(x)[:, None] < ax / 2) & (np.abs(y)[None, :] < ay / 2)
    s = np.fft.fft2(pad.astype(float))
    kx = 2 * np.pi * np.fft.fftfreq(n, dx)
    ky = 2 * np.pi * np.fft.fftfreq(n, dy)
    k = np.hypot(kx[:, None], ky[None, :])
    z = np.linspace(0, d, n_z)
    mx = int(round(1.5 * px / dx))
    my = int(round(1.5 * py / dy))
    cx = slice(n // 2 - mx, n // 2 + mx)
    cy = slice(n // 2 - my, n // 2 + my)
    phi = np.zeros((n_z, 2 * mx, 2 * my))
    for i, zz in enumerate(z):
        # sinh(k z) / sinh(k d), written to avoid the overflow
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            g = (
                np.exp(-k * (d - zz))
                * (1 - np.exp(-2 * k * zz))
                / (1 - np.exp(-2 * k * d))
            )
        g[0, 0] = zz / d
        phi[i] = np.fft.ifft2(s * g).real[cx, cy]
    return z, x[cx], y[cy], phi


def depth_factor(z, phi, electron_path=np.inf, hole_path=0.0):
    """
    Share of the charge of a deposit at z (distance to the cathode) induced
    on the pad, along one line of drift (phi: (z, ...)): the electrons go to
    the anode and the holes to the cathode, each with a mean path before
    trapping. electron_path infinite and hole_path 0: phi(anode) - phi(z).
    np.einsum (no BLAS): single thread, on purpose. The computation is small
    (~1 s) and a multithreaded BLAS only wastes CPU on a busy machine.
    """
    dphi = np.diff(phi, axis=0)
    zm = 0.5 * (z[1:] + z[:-1])
    eta = np.zeros_like(phi)
    for i, zz in enumerate(z):
        if np.isfinite(electron_path):
            e = np.exp(-(zm[i:] - zz) / electron_path)
        else:
            e = np.ones(len(zm) - i)
        eta[i] = np.einsum("i,ijk->jk", e, dphi[i:])
        if hole_path > 0:
            h = np.exp(-(zz - zm[:i]) / hole_path)
            eta[i] += np.einsum("i,ijk->jk", h, dphi[:i])
    return eta


def border_share(x, sigma, pitch):
    """Share of a Gaussian cloud (sigma) at x that falls on the pad centred at 0 (width: pitch), along one axis."""
    s = np.sqrt(2) * sigma
    return 0.5 * (erf((x + pitch / 2) / s) - erf((x - pitch / 2) / s))


@lru_cache(maxsize=16)
def _induction_tables_cached(
    pitch, thickness, electron_path, hole_path, cloud_sigma, n, n_period, n_z, pad
):
    z, x, y, phi = weighting_potential(pitch, thickness, n, n_period, n_z, pad)
    tables = {}
    for name, own in (("eta_own", 1.0), ("eta_neighbour", 0.0)):
        # on the anode plane, the hits of the pixel see 1, the others 0
        t = phi.copy()
        t[-1] = own
        tables[name] = depth_factor(z, t, electron_path, hole_path)
    if cloud_sigma > 0:
        # the cloud of the electrons that reach the anode is shared between
        # the pads (replaces the share of the pad of the deposit): 1D tables
        # on a fine grid (the 3D grid cannot resolve the edge of the pad)
        step = min(cloud_sigma / 50, pitch[0] / 500, pitch[1] / 500)
        for k, axis in ((0, "cloud_x"), (1, "cloud_y")):
            u = np.arange(-1.5 * pitch[k], 1.5 * pitch[k] + step / 2, step)
            tables[axis] = border_share(u, cloud_sigma, pitch[k])
            tables[axis + "_axis"] = u
        zc = np.linspace(0, thickness, 1201)
        if np.isfinite(electron_path):
            tables["cloud_z"] = np.exp(-(thickness - zc) / electron_path)
        else:
            tables["cloud_z"] = np.ones_like(zc)
        tables["cloud_z_axis"] = zc
    tables.update(z=z, x=x, y=y)
    for v in tables.values():
        v.setflags(write=False)
    return tables


def induction_tables(
    pitch,
    thickness,
    electron_path=np.inf,
    hole_path=0.0,
    cloud_sigma=0.0,
    n=512,
    n_period=16,
    n_z=121,
    pad_size=None,
):
    """
    Tables eta_own and eta_neighbour (z, x, y) and their axes z, x, y (dict
    of read-only arrays). See the module documentation. pad_size: size of
    the pads (None: the pitch, no gap). Cached: the actors of several heads
    with the same parameters share the computation.
    """
    if pad_size is not None:
        pad_size = (float(pad_size[0]), float(pad_size[1]))
        if not (0 < pad_size[0] <= pitch[0] and 0 < pad_size[1] <= pitch[1]):
            fatal(
                f"The pad size {pad_size} must be positive and not larger than the pitch {pitch}"
            )
    return _induction_tables_cached(
        (float(pitch[0]), float(pitch[1])),
        float(thickness),
        float(electron_path),
        float(hole_path),
        float(cloud_sigma),
        int(n),
        int(n_period),
        int(n_z),
        pad_size,
    )


def unit_tables(pitch, thickness):
    """Tables with no induction: eta_own = 1, eta_neighbour = 0 (plain readout by pixel)."""
    z = np.array([0.0, thickness])
    x = np.array([-1.5, 1.5]) * pitch[0]
    y = np.array([-1.5, 1.5]) * pitch[1]
    shape = (2, 2, 2)
    return dict(z=z, x=x, y=y, eta_own=np.ones(shape), eta_neighbour=np.zeros(shape))


def read_tables(tables):
    """
    Tables given by the user: a dict or a .npz file with the keys z, x, y
    (regular axes, mm) and eta_own, eta_neighbour (shape (len(z), len(x),
    len(y))).
    """
    if isinstance(tables, (str, Path)):
        with np.load(tables) as f:
            tables = {k: f[k] for k in f.files}
    keys = ("z", "x", "y", "eta_own", "eta_neighbour")
    for k in keys:
        if k not in tables:
            fatal(f"The induction tables must contain the key '{k}' (keys: {keys})")
    t = {k: np.asarray(tables[k], dtype=float) for k in keys}
    cloud_keys = [f"cloud_{a}{s}" for a in "xyz" for s in ("", "_axis")]
    present = [k for k in cloud_keys if k in tables]
    if present and len(present) != len(cloud_keys):
        fatal(f"The induction tables must contain all or none of the keys {cloud_keys}")
    for k in present:
        t[k] = np.asarray(tables[k], dtype=float)
    for a in "xyz" if present else "":
        v, ax = t[f"cloud_{a}"], t[f"cloud_{a}_axis"]
        if v.shape != ax.shape or len(ax) < 2 or not np.allclose(np.diff(ax), ax[1] - ax[0]) or ax[1] <= ax[0]:  # fmt: skip
            fatal(
                f"The table cloud_{a} must be 1D, on a regular increasing axis cloud_{a}_axis"
            )
    shape = (len(t["z"]), len(t["x"]), len(t["y"]))
    for k in ("eta_own", "eta_neighbour"):
        if t[k].shape != shape:
            fatal(
                f"The induction table '{k}' has the shape {t[k].shape}, "
                f"while the axes z, x, y give {shape}"
            )
    for k in ("z", "x", "y"):
        a = t[k]
        if len(a) < 2 or not np.allclose(np.diff(a), a[1] - a[0]) or a[1] <= a[0]:
            fatal(
                f"The axis '{k}' of the induction tables must be regular and increasing"
            )
    return t


def cloud_tables(tables):
    """The three 1D cloud tables, their origins and spacings (None if no cloud term)."""
    if "cloud_x" not in tables:
        return None
    out = []
    for a in "xyz":
        ax = tables[f"cloud_{a}_axis"]
        out += [tables[f"cloud_{a}"], float(ax[0]), float(ax[1] - ax[0])]
    return out


def table_origin_and_spacing(tables):
    """Position of the first node and spacing (z, x, y) of the tables."""
    origin = [float(tables[k][0]) for k in ("z", "x", "y")]
    spacing = [float(tables[k][1] - tables[k][0]) for k in ("z", "x", "y")]
    return origin, spacing


def grid_from_positions(centres, tolerance=1e-6):
    """
    Pixel grid from the centres of the pixels (array (n, 3) in the frame of
    the crystal, in the order of the copy numbers): the pixels must form a
    full regular grid in the XY plane. Return the pixel size (2), the number
    of pixels (2), the centre of the grid (2), and for each copy number the
    indices ix, iy.
    """
    centres = np.asarray(centres, dtype=float)
    if centres.ndim != 2 or centres.shape[1] != 3 or len(centres) < 1:
        fatal("The pixel centres must be an array (n, 3)")
    if np.ptp(centres[:, 2]) > tolerance:
        fatal("The pixels must all be at the same Z in the crystal (one layer).")
    size, number, center, indices = [], [], [], []
    for k in (0, 1):
        c = centres[:, k]
        # distinct positions along this axis
        u = np.sort(c)
        u = u[np.concatenate([[True], np.diff(u) > tolerance])]
        if len(u) == 1:
            fatal(
                f"The pixels have one position along axis {'XY'[k]}: the pixel size "
                f"cannot be computed (a grid of one row is not supported with a pixel volume)."
            )
        step = np.diff(u)
        if np.ptp(step) > tolerance * max(1.0, step.mean()):
            fatal(f"The pixels are not regularly spaced along the axis {'XY'[k]}.")
        p = step.mean()
        i = np.rint((c - u[0]) / p).astype(int)
        size.append(float(p))
        number.append(len(u))
        center.append(float((u[0] + u[-1]) / 2))
        indices.append(i)
    if len(centres) != number[0] * number[1]:
        fatal(
            f"The pixels do not form a full grid: {len(centres)} pixels for a grid "
            f"of {number[0]} x {number[1]}."
        )
    key = indices[0] * number[1] + indices[1]
    if len(np.unique(key)) != len(key):
        fatal("Two pixels are at the same position.")
    return size, number, center, indices[0].tolist(), indices[1].tolist()


def pixel_centres_of_volume(volume):
    """
    Centres of the copies of a repeated pixel volume in the frame of its
    mother (the crystal), in the order of the copy numbers. The volume is
    either a RepeatParametrisedVolume or a volume with several translations.
    """
    if getattr(volume, "translations", None) is not None:
        return volume.copy_translations()
    if hasattr(volume, "linear_repeat"):
        rep = np.array(volume.linear_repeat, dtype=int)
        t = np.array(volume.translation, dtype=float).reshape(3)
        if isinstance(volume.start, str) and volume.start == "auto":
            start = -(rep - 1) * t / 2.0
        else:
            start = np.array(volume.start, dtype=float)
        if volume.offset_nb != 1:
            fatal(
                f"The pixel volume '{volume.name}' has offset_nb = {volume.offset_nb}: not supported."
            )
        # same order as GateRepeatParameterisation
        centres = [
            start + np.array([i, j, k]) * t
            for i in range(rep[0])
            for j in range(rep[1])
            for k in range(rep[2])
        ]
        return np.array(centres)
    translations = np.array(volume.translation, dtype=float)
    if translations.ndim == 1:
        translations = translations[None, :]
    rotations = volume.rotation
    if rotations is not None:
        r = np.array(rotations, dtype=float)
        r = r.reshape(-1, 3, 3)
        if not np.allclose(r, np.eye(3)[None, :, :]):
            fatal(f"The pixel volume '{volume.name}' must not be rotated.")
    return translations
