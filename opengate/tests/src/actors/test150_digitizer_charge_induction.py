#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DigitizerChargeInductionActor: charge induction and readout by pixel in a
CdTe crystal of 8 x 4 pixels of 2.46 mm, 6 mm thick, translated and rotated
in the world, hit by a 140 keV photon beam (square, covering the pixels)
from the cathode side.

Run 1, monolithic crystal (the pixels from the local position):
- "pixel": no induction (tables "unit"), no neighbour: plain readout by pixel;
- "law": tables from the weighting potential (no trapping, holes that do
  not move, no cloud), 3 x 3 pixels;
- "trap": with trapping of electrons and holes, a charge cloud, gain and
  threshold;
- "gap": the law with pads of 2 mm (gaps of 0.46 mm);
- "minusz": the law with the cathode on the -z side and the middle of the
  step as position;
- "policies": the law with attribute policies (TrackID: max, KineticEnergy:
  energy_winner).

Run 2, pixelated crystal: the pixels are 32 placed copies of a box, the grid
is not centred in the crystal (one empty column of vacuum on each side, the
grid shifted by one pitch). The grid is read from the pixel volume, the
pixel of a hit is its copy number:
- "pv_unit": readout by pixel, PostPosition;
- "pv_law": the law, middle of the step.

Each output is compared, digi by digi, with a numpy implementation on the
same hits (pixel from the local position, trilinear interpolation of the
tables with scipy). Also checked: the global position of each digi is the
centre of its pixel, the readout by pixel keeps the energy of the hits, the
grid read from a RepeatParametrisedVolume, the effect of the gaps on the
weighting potential.
"""

import numpy as np
import uproot
from scipy.ndimage import map_coordinates
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
from opengate.geometry.volumes import RepeatParametrisedVolume
from opengate.actors.chargeinduction import (
    induction_tables,
    unit_tables,
    weighting_potential,
    grid_from_positions,
    pixel_centres_of_volume,
)

mm = gate.g4_units.mm
keV = gate.g4_units.keV

pitch = [2.46 * mm, 2.46 * mm]
n_pixels = [8, 4]
thickness = 6 * mm
translation = np.array([10 * mm, -5 * mm, 20 * mm])
rotation = Rotation.from_euler("zx", [30, 10], degrees=True).as_matrix()
policies = {"TrackID": "max", "KineticEnergy": "energy_winner"}

variants_monolithic = {
    "pixel": dict(neighbours=0, tables="unit", signal_threshold=0),
    "law": dict(neighbours=1, tables=None, signal_threshold=0),
    "trap": dict(
        neighbours=1,
        tables=None,
        electron_mean_path=20 * mm,
        hole_mean_path=0.5 * mm,
        charge_cloud_sigma=0.1 * mm,
        gain=1.02,
        signal_threshold=20 * keV,
    ),
    "gap": dict(neighbours=1, tables=None, pad_size=[2 * mm, 2 * mm]),
    "minusz": dict(
        neighbours=1,
        tables=None,
        cathode_side="-z",
        hit_position="middle",
        signal_threshold=0,
    ),
    "policies": dict(
        neighbours=1, tables=None, signal_threshold=0, attribute_policies=policies
    ),
}
variants_pixelated = {
    "pv_unit": dict(
        neighbours=0, tables="unit", signal_threshold=0, pixel_volume="pixel"
    ),
    "pv_law": dict(
        neighbours=1,
        tables=None,
        signal_threshold=0,
        hit_position="middle",
        pixel_volume="pixel",
    ),
}
# grid centre in the crystal for the pixelated run
grid_shift = np.array([pitch[0], 0, 0])


def run(name, variants, pixelated):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.verbose_level = gate.logger.NONE
    sim.random_seed = 12345678
    sim.world.size = [200 * mm, 200 * mm, 200 * mm]
    sim.world.material = "G4_Galactic"

    crystal = sim.add_volume("Box", "crystal")
    crystal.size = [n_pixels[0] * pitch[0], n_pixels[1] * pitch[1], thickness]
    crystal.material = "G4_CADMIUM_TELLURIDE"
    crystal.translation = list(translation)
    crystal.rotation = rotation
    centre = np.zeros(3)
    if pixelated:
        # crystal larger than the grid (vacuum), the grid shifted by one pitch
        crystal.size = [(n_pixels[0] + 4) * pitch[0], n_pixels[1] * pitch[1], thickness]
        crystal.material = "G4_Galactic"
        pixel = sim.add_volume("Box", "pixel")
        pixel.mother = crystal
        pixel.size = [pitch[0], pitch[1], thickness]
        pixel.material = "G4_CADMIUM_TELLURIDE"
        t = gate.geometry.utility.get_grid_repetition(
            [n_pixels[0], n_pixels[1], 1], [pitch[0], pitch[1], 0]
        )
        pixel.translation = [list(np.array(x) + grid_shift) for x in t]
        centre = grid_shift

    # beam along -z (local), from the cathode side, covering the pixels
    source = sim.add_source("GenericSource", "beam")
    source.particle = "gamma"
    source.energy.mono = 140 * keV
    source.position.type = "box"
    source.position.size = [n_pixels[0] * pitch[0], n_pixels[1] * pitch[1], 0]
    source.position.translation = list(
        translation + rotation @ (centre + [0, 0, 20 * mm])
    )
    source.position.rotation = rotation
    source.direction.type = "momentum"
    source.direction.momentum = list(rotation @ [0, 0, -1])
    source.number_of_primaries = 20000

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut(crystal.name, "all", 0.01 * mm)
    if pixelated:
        sim.physics_manager.set_production_cut(pixel.name, "all", 0.01 * mm)

    hc = sim.add_actor("DigitizerHitsCollectionActor", "hits")
    hc.attached_to = crystal
    hc.authorize_repeated_volumes = True
    hc.attributes = [
        "PostPosition",
        "PrePosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
        "EventID",
        "TrackID",
        "KineticEnergy",
    ]
    hc.output_filename = f"test150_{name}.root"

    for vname, options in variants.items():
        a = sim.add_actor("DigitizerChargeInductionActor", vname)
        a.attached_to = crystal
        a.authorize_repeated_volumes = True
        a.input_digi_collection = hc.name
        a.pixel_size = pitch
        a.number_of_pixels = n_pixels
        for k, v in options.items():
            setattr(a, k, v)
        a.output_filename = f"test150_{name}.root"

    sim.run(start_new_process=True)
    return uproot.open(paths.output / f"test150_{name}.root")


def to_local(p):
    return (p - translation) @ rotation


def reference(hits, options, centre):
    """
    The actor in numpy. Return {(event, pixel x, pixel y): [signal, max
    TrackID, KineticEnergy of the hit of largest |contribution|]}. The pixel
    of a hit is computed from the middle of the step (exact for the copy
    number of a pixel volume).
    """
    neighbours = options["neighbours"]
    if options["tables"] == "unit":
        t = unit_tables(pitch, thickness)
    else:
        t = induction_tables(
            pitch,
            thickness,
            electron_path=options.get("electron_mean_path", np.inf),
            hole_path=options.get("hole_mean_path", 0),
            cloud_sigma=options.get("charge_cloud_sigma", 0),
            pad_size=options.get("pad_size", None),
        )
    gain = options.get("gain", 1.0)
    threshold = options.get("signal_threshold", 1 * keV)
    p = hits["post"]
    if options.get("hit_position", "post") == "middle":
        p = 0.5 * (p + hits["pre"])
    loc = to_local(p) - centre
    if "pixel_volume" in options:
        # the hits that are not in a pixel volume are ignored
        pix = to_local(0.5 * (hits["post"] + hits["pre"])) - centre
        inside = (np.abs(pix[:, 0]) < n_pixels[0] * pitch[0] / 2) & (
            np.abs(pix[:, 1]) < n_pixels[1] * pitch[1] / 2
        )
        hits = {k: v[inside] for k, v in hits.items()}
        p, loc, pix = p[inside], loc[inside], pix[inside]
    else:
        pix = loc
    u = [(pix[:, i] + n_pixels[i] * pitch[i] / 2) / pitch[i] for i in (0, 1)]
    ix = [np.clip(np.floor(u[i]), 0, n_pixels[i] - 1).astype(int) for i in (0, 1)]
    r = [loc[:, i] - ((ix[i] + 0.5) * pitch[i] - n_pixels[i] * pitch[i] / 2) for i in (0, 1)]  # fmt: skip
    if options.get("cathode_side", "+z") == "+z":
        z = np.clip(thickness / 2 - loc[:, 2], 0, thickness)
    else:
        z = np.clip(thickness / 2 + loc[:, 2], 0, thickness)
    out = {}
    best = {}
    for a in range(-neighbours, neighbours + 1):
        for b in range(-neighbours, neighbours + 1):
            jx, jy = ix[0] + a, ix[1] + b
            m = (jx >= 0) & (jx < n_pixels[0]) & (jy >= 0) & (jy < n_pixels[1])
            table = t["eta_own"] if (a, b) == (0, 0) else t["eta_neighbour"]
            c = [
                (z[m] - t["z"][0]) / (t["z"][1] - t["z"][0]),
                (r[0][m] - a * pitch[0] - t["x"][0]) / (t["x"][1] - t["x"][0]),
                (r[1][m] - b * pitch[1] - t["y"][0]) / (t["y"][1] - t["y"][0]),
            ]
            w = map_coordinates(table, c, order=1, mode="nearest")
            if "cloud_x" in t:
                own = float((a, b) == (0, 0))
                bx = np.interp(r[0][m] - a * pitch[0], t["cloud_x_axis"], t["cloud_x"])
                by = np.interp(r[1][m] - b * pitch[1], t["cloud_y_axis"], t["cloud_y"])
                w = w + (bx * by - own) * np.interp(
                    z[m], t["cloud_z_axis"], t["cloud_z"]
                )
            for i, k, v in zip(
                np.flatnonzero(m),
                zip(hits["event"][m], jx[m], jy[m]),
                hits["edep"][m] * w,
                strict=True,
            ):
                o = out.setdefault(k, [0.0, -np.inf, 0.0])
                o[0] += v
                o[1] = max(o[1], hits["track"][i])
                # the first hit (in the order of the hits) in case of equality
                bi = best.get(k)
                if bi is None or abs(v) > bi[0] or (abs(v) == bi[0] and i < bi[1]):
                    best[k] = (abs(v), i)
    for k, (_, i) in best.items():
        out[k][2] = hits["ke"][i]
    for k in out:
        out[k][0] *= gain
    return {k: v for k, v in out.items() if v[0] >= threshold and v[0] > 0}


def read_hits(f):
    h = f["hits"].arrays(library="np")
    hits = {
        "edep": h["TotalEnergyDeposit"],
        "event": h["EventID"],
        "track": h["TrackID"],
        "ke": h["KineticEnergy"],
        "post": np.stack([h[f"PostPosition_{c}"] for c in "XYZ"], axis=1),
        "pre": np.stack([h[f"PrePosition_{c}"] for c in "XYZ"], axis=1),
    }
    m = hits["edep"] > 0
    return {k: v[m] for k, v in hits.items()}


def check_variants(f, hits, variants, centre):
    is_ok = True
    for name, options in variants.items():
        d = f[name].arrays(library="np")
        keys = list(zip(d["EventID"], d["PixelIndexX"], d["PixelIndexY"]))
        ref = reference(hits, options, centre)
        e = d["TotalEnergyDeposit"]
        same_keys = set(keys) == set(ref.keys()) and len(keys) == len(set(keys))
        diff = max(abs(v - ref[k][0]) for k, v in zip(keys, e)) if same_keys else np.inf
        b = same_keys and diff < 1e-6 * keV
        utility.print_test(
            b,
            f"{name:8}: {len(e)} digi (numpy {len(ref)}), "
            f"max |diff| {diff / keV:.2e} keV, mean energy {np.mean(e) / keV:.2f} keV",
        )
        is_ok = is_ok and b

        # position: global = centre of the pixel; local z = 0
        local = np.stack([d[f"PostPositionLocal_{c}"] for c in "XYZ"], axis=1)
        glob = np.stack([d[f"PostPosition_{c}"] for c in "XYZ"], axis=1)
        pc = np.stack(
            [
                (d["PixelIndexX"] + 0.5) * pitch[0] - n_pixels[0] * pitch[0] / 2,
                (d["PixelIndexY"] + 0.5) * pitch[1] - n_pixels[1] * pitch[1] / 2,
                np.zeros(len(e)),
            ],
            axis=1,
        ) + [centre[0], centre[1], 0]
        dl = np.abs(local - pc).max()
        dg = np.abs(to_local(glob) - pc).max()
        b = dl < 1e-9 * mm and dg < 1e-6 * mm
        utility.print_test(
            b, f"{name:8}: pixel centres, local {dl:.1e} mm, global {dg:.1e} mm"
        )
        is_ok = is_ok and b

        if "attribute_policies" in options and same_keys:
            t_ok = all(ref[k][1] == v for k, v in zip(keys, d["TrackID"]))
            k_ok = all(ref[k][2] == v for k, v in zip(keys, d["KineticEnergy"]))
            n_diff = sum(t != 1 for t in d["TrackID"])
            b = t_ok and k_ok
            utility.print_test(
                b,
                f"{name:8}: TrackID (max) {t_ok}, KineticEnergy (energy winner) {k_ok} "
                f"({n_diff} digi with a max TrackID != 1)",
            )
            is_ok = is_ok and b
    return is_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test150")
    is_ok = True

    # tables: smaller pads give a smaller weighting potential above the pad
    _, _, _, phi = weighting_potential(pitch, thickness, n_z=13)
    _, _, _, phi_gap = weighting_potential(pitch, thickness, n_z=13, pad_size=[2, 2])
    c = phi.shape[1] // 2
    b = (phi_gap[1:-1, c, c] < phi[1:-1, c, c]).all() and phi_gap[0].max() < 1e-12
    utility.print_test(
        b,
        f"Weighting potential at mid depth, centre of the pixel: pad = pitch "
        f"{phi[6, c, c]:.3f}, pad 2 mm {phi_gap[6, c, c]:.3f}",
    )
    is_ok = is_ok and b

    # grid read from a RepeatParametrisedVolume (same order as the copy numbers)
    sim = gate.Simulation()
    cr = sim.add_volume("Box", "c")
    px = sim.add_volume("Box", "p")
    px.mother = cr
    rp = RepeatParametrisedVolume(repeated_volume=px)
    rp.linear_repeat = [5, 3, 1]
    rp.translation = [2 * mm, 3 * mm, 0]
    size, number, centre, ix, iy = grid_from_positions(pixel_centres_of_volume(rp))
    b = (
        np.allclose(size, [2, 3])
        and number == [5, 3]
        and np.allclose(centre, 0)
        and ix[:4] == [0, 0, 0, 1]
        and iy[:4] == [0, 1, 2, 0]
    )
    utility.print_test(
        b, f"Grid of a RepeatParametrisedVolume: {size} {number} {centre}"
    )
    is_ok = is_ok and b

    # run 1: monolithic crystal
    f = run("monolithic", variants_monolithic, False)
    hits = read_hits(f)
    print(f"Monolithic: {len(hits['edep'])} hits, {len(np.unique(hits['event']))} events")  # fmt: skip
    is_ok = check_variants(f, hits, variants_monolithic, np.zeros(3)) and is_ok

    # the readout by pixel keeps the energy of the hits
    r = f["pixel"]["TotalEnergyDeposit"].array(library="np").sum() / hits["edep"].sum()
    b = abs(r - 1) < 1e-9
    utility.print_test(b, f"Readout by pixel: energy of the digi / of the hits {r:.9f}")
    is_ok = is_ok and b

    # run 2: pixelated crystal
    f = run("pixelated", variants_pixelated, True)
    hits = read_hits(f)
    print(f"Pixelated: {len(hits['edep'])} hits, {len(np.unique(hits['event']))} events")  # fmt: skip
    is_ok = check_variants(f, hits, variants_pixelated, grid_shift) and is_ok
    r = (
        f["pv_unit"]["TotalEnergyDeposit"].array(library="np").sum()
        / hits["edep"].sum()
    )
    b = abs(r - 1) < 1e-9
    utility.print_test(b, f"Pixel volume: energy of the digi / of the hits {r:.9f}")
    is_ok = is_ok and b
    # the hits whose post position is on the edge of their pixel (the copy
    # number gives their pixel, not the position)
    post = to_local(hits["post"]) - grid_shift
    mid = to_local(0.5 * (hits["post"] + hits["pre"])) - grid_shift
    u = lambda q: np.floor((q[:, 0] + n_pixels[0] * pitch[0] / 2) / pitch[0])
    print(f"Hits whose post position is in another pixel than the step: {(u(post) != u(mid)).sum()}")  # fmt: skip

    utility.test_ok(is_ok)
