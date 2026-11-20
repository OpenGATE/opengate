#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DigitizerSpatialBlurringActor: the edge policies (none, clamp, truncated,
truncated_std) and the limits volume (#792).

A 60 keV pencil beam hits a NaI crystal (photoelectric effect: the position of
the single is close to the beam axis); the singles are blurred (FWHM 30 mm)
by four actors, one per edge policy.
- beam in the middle of the crystal: all policies give the requested sigma;
- beam 5 mm from the edge: compared to the analytical truncated Gaussian;
- crystal made of pixels: the limits are the volume the actor is attached to
  (the block), or the pixel if limits_volume is the pixel.
"""

import numpy as np
import uproot
import opengate as gate
import opengate_core as g4
from opengate.tests import utility

mm = gate.g4_units.mm
keV = gate.g4_units.keV
fwhm = 30 * mm
sigma = fwhm * gate.definitions.fwhm_to_sigma
policies = ["none", "clamp", "truncated", "truncated_std"]


def run(name, x0, pixels=False, limits_volume=None, former_options=None):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.verbose_level = gate.logger.NONE
    sim.random_seed = 87654321
    sim.world.size = [1000 * mm, 1000 * mm, 1000 * mm]
    sim.world.material = "G4_Galactic"

    # crystal 200 x 200 x 10 mm, monolithic or 20 x 20 pixels of 10 mm
    crystal = sim.add_volume("Box", "crystal")
    crystal.size = [200 * mm, 200 * mm, 10 * mm]
    crystal.material = "G4_SODIUM_IODIDE"
    if pixels:
        crystal.material = "G4_Galactic"
        pixel = sim.add_volume("Box", "pixel")
        pixel.mother = crystal
        pixel.size = [10 * mm, 10 * mm, 10 * mm]
        pixel.material = "G4_SODIUM_IODIDE"
        pixel.translation = gate.geometry.utility.get_grid_repetition(
            [20, 20, 1], [10 * mm, 10 * mm, 0]
        )

    source = sim.add_source("GenericSource", "beam")
    source.particle = "gamma"
    source.energy.mono = 60 * keV
    source.position.type = "point"
    source.position.translation = [x0, 0, -50 * mm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = 20000

    hc = sim.add_actor("DigitizerHitsCollectionActor", "hits")
    hc.attached_to = crystal
    hc.authorize_repeated_volumes = True
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]
    hc.root_output.write_to_disk = False
    sc = sim.add_actor("DigitizerAdderActor", "singles")
    sc.attached_to = crystal
    sc.authorize_repeated_volumes = True
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWinnerPosition"
    sc.group_volume = crystal.name
    sc.root_output.write_to_disk = False

    names = policies if former_options is None else ["former"]
    for p in names:
        sb = sim.add_actor("DigitizerSpatialBlurringActor", f"blur_{p}")
        sb.attached_to = crystal
        sb.authorize_repeated_volumes = True
        sb.input_digi_collection = sc.name
        sb.blur_attribute = "PostPosition"
        sb.blur_fwhm = fwhm
        if former_options is None:
            sb.edge_policy = p
        else:
            sb.keep_in_solid_limits = former_options[0]
            sb.use_truncated_Gaussian = former_options[1]
        sb.limits_volume = limits_volume
        sb.output_filename = f"test145_{name}.root"
    sim.run(start_new_process=True)

    f = uproot.open(paths.output / f"test145_{name}.root")
    return {p: f[f"blur_{p}"]["PostPosition_X"].array(library="np") - x0 for p in names}


def check(b, msg):
    utility.print_test(b, msg)
    return b


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test145")
    is_ok = True
    Blur = g4.GateDigitizerSpatialBlurringActor

    # 0) analytical functions
    s = Blur.ComputeTruncatedStd(-1.0, 1.0, -100.0, 0.0)
    is_ok = (
        check(abs(s - 0.7935) < 1e-3, f"Truncated std at 1 sigma: {s:.4f}") and is_ok
    )
    s = Blur.ComputeTruncatedRms(-1.0, 1.0, -100.0, 0.0)
    is_ok = (
        check(abs(s - 0.8440) < 1e-3, f"Truncated rms at 1 sigma: {s:.4f}") and is_ok
    )
    s = Blur.ComputeParentSigmaForRms(-1.0, 1.0, -100.0, 0.0)
    s2 = Blur.ComputeTruncatedRms(-1.0, s, -100.0, 0.0)
    b = abs(s2 - 1.0) < 1e-5
    is_ok = check(b, f"Parent sigma {s:.4f} gives a rms distance of {s2:.6f}") and is_ok

    # 1) beam in the middle: no effect of the edges
    print()
    d = run("middle", 0)
    for p in policies:
        std = d[p].std()
        b = abs(std - sigma) / sigma < 0.03
        is_ok = (
            check(b, f"Middle, {p:13}: std {std:.2f} mm (sigma {sigma:.2f})") and is_ok
        )

    # 2) beam 5 mm from the edge (x = 95 mm, the crystal ends at 100 mm)
    print()
    x0 = 95 * mm
    d = run("edge", x0)
    std_t = Blur.ComputeTruncatedStd(x0, sigma, -100 * mm, 100 * mm)
    n = len(d["none"])
    out = np.sum(d["none"] > 5 * mm) / n
    b = 0.30 < out < 0.40  # 1 - cdf(5/12.74) = 0.347
    is_ok = (
        check(b, f"Edge, none         : {out*100:.1f} % outside the crystal") and is_ok
    )
    on_edge = np.sum(d["clamp"] > 5 * mm - 1e-3) / n
    b = 0.30 < on_edge < 0.40 and d["clamp"].max() < 5 * mm
    is_ok = (
        check(b, f"Edge, clamp        : {on_edge*100:.1f} % on the boundary") and is_ok
    )
    std = d["truncated"].std()
    b = d["truncated"].max() <= 5 * mm and abs(std - std_t) / std_t < 0.03
    is_ok = (
        check(b, f"Edge, truncated    : std {std:.2f} mm (expected {std_t:.2f})")
        and is_ok
    )
    # truncated_std: the rms distance to the true position is sigma
    rms = np.sqrt(np.mean(d["truncated_std"] ** 2))
    b = d["truncated_std"].max() <= 5 * mm and abs(rms - sigma) / sigma < 0.03
    is_ok = (
        check(b, f"Edge, truncated_std: rms {rms:.2f} mm (expected {sigma:.2f})")
        and is_ok
    )

    # 3) former options: keep_in_solid_limits True, use_truncated_Gaussian False = clamp
    d = run("former", x0, former_options=(True, False))
    on_edge2 = np.sum(d["former"] > 5 * mm - 1e-3) / n
    b = abs(on_edge2 - on_edge) < 0.02
    is_ok = (
        check(b, f"Former options (clamp): {on_edge2*100:.1f} % on the boundary")
        and is_ok
    )

    # 4) pixels: the limits are the block (the attached volume), not the pixel
    print()
    x0 = 5 * mm  # centre of a pixel
    d = run("pixels", x0, pixels=True)
    for p in ["truncated", "truncated_std"]:
        rms = np.sqrt(np.mean(d[p] ** 2))
        b = abs(rms - sigma) / sigma < 0.03
        is_ok = (
            check(b, f"Pixels, {p:13}: rms {rms:.2f} mm (sigma {sigma:.2f})") and is_ok
        )

    # ... unless limits_volume is the pixel: the position stays in the pixel
    d = run("pixel_limits", x0, pixels=True, limits_volume="pixel")
    x = d["truncated"]
    b = np.abs(x).max() <= 5 * mm
    is_ok = (
        check(
            b, f"Pixel limits: |x| max {np.abs(x).max():.2f} mm (pixel half size 5 mm)"
        )
        and is_ok
    )

    utility.test_ok(is_ok)
