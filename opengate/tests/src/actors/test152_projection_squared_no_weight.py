#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DigitizerProjectionActor: squared counts when the digi have no Weight
attribute (they were not scored: the squared counts were all zero).

A 140 keV beam hits a CdTe crystal of 8 x 8 pixels of 2.46 mm. Three chains,
with the squared counts:
- A: hits with Weight -> adder -> projection;
- B: hits without Weight -> adder -> projection: same images as A, and the
  squared counts equal the counts (one single per event);
- C: hits without Weight -> charge induction (one digi per pixel) ->
  projection with bins of 2 x 2 pixels: one event can give several digi in
  one bin, the squared counts are the sum over the events of n^2 (n: number
  of digi of the event in the bin).
"""

import numpy as np
import uproot
import itk
import opengate as gate
from opengate.tests import utility

mm = gate.g4_units.mm
keV = gate.g4_units.keV
pitch = 2.46 * mm
n_pixels = 8


def run():
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.verbose_level = gate.logger.NONE
    sim.random_seed = 3456789
    sim.world.size = [200 * mm, 200 * mm, 200 * mm]
    sim.world.material = "G4_Galactic"

    crystal = sim.add_volume("Box", "crystal")
    crystal.size = [n_pixels * pitch, n_pixels * pitch, 6 * mm]
    crystal.material = "G4_CADMIUM_TELLURIDE"

    source = sim.add_source("GenericSource", "beam")
    source.particle = "gamma"
    source.energy.mono = 140 * keV
    source.position.type = "box"
    source.position.size = [crystal.size[0], crystal.size[1], 0]
    source.position.translation = [0, 0, 20 * mm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, -1]
    source.number_of_primaries = 20000
    sim.physics_manager.set_production_cut(crystal.name, "all", 0.01 * mm)

    attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
        "EventID",
    ]
    last = {}
    for name, weight in (("A", True), ("B", False)):
        hc = sim.add_actor("DigitizerHitsCollectionActor", f"hits_{name}")
        hc.attached_to = crystal
        hc.attributes = attributes + (["Weight"] if weight else [])
        hc.output_filename = None
        sc = sim.add_actor("DigitizerAdderActor", f"singles_{name}")
        sc.attached_to = crystal
        sc.input_digi_collection = hc.name
        sc.output_filename = "test152.root"
        last[name] = sc.name

    px = sim.add_actor("DigitizerChargeInductionActor", "pixels_C")
    px.attached_to = crystal
    px.input_digi_collection = "hits_B"
    px.pixel_size = [pitch, pitch]
    px.number_of_pixels = [n_pixels, n_pixels]
    px.signal_threshold = 20 * keV
    px.output_filename = "test152.root"
    last["C"] = px.name

    for name, (size, spacing) in {
        "A": (n_pixels, pitch),
        "B": (n_pixels, pitch),
        "C": (n_pixels // 2, 2 * pitch),
    }.items():
        proj = sim.add_actor("DigitizerProjectionActor", f"projection_{name}")
        proj.attached_to = crystal
        proj.input_digi_collections = [last[name]]
        proj.spacing = [spacing, spacing]
        proj.size = [size, size]
        proj.output_filename = f"test152_projection_{name}.mhd"
        proj.squared_counts.active = True
    sim.run()
    return sim


def images(sim, name):
    proj = sim.get_actor(f"projection_{name}")
    c = itk.GetArrayFromImage(proj.counts.image)
    s = itk.GetArrayFromImage(proj.squared_counts.image)
    return c, s


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test152")
    sim = run()
    is_ok = True

    ca, sa = images(sim, "A")
    cb, sb = images(sim, "B")
    cc, sc = images(sim, "C")

    b = np.array_equal(ca, cb) and np.array_equal(sa, sb)
    utility.print_test(
        b, f"With and without Weight: same counts ({ca.sum():.0f}) and squared counts"
    )
    is_ok = is_ok and b

    b = sb.sum() > 0 and np.array_equal(sb, cb)
    utility.print_test(
        b,
        f"No Weight, adder: squared counts {sb.sum():.0f} = counts {cb.sum():.0f}",
    )
    is_ok = is_ok and b

    # C: one event can give several digi in one bin of 2 x 2 pixels
    d = uproot.open(paths.output / "test152.root")["pixels_C"].arrays(library="np")
    key = d["EventID"] * 100 + (d["PixelIndexX"] // 2) * 10 + d["PixelIndexY"] // 2
    _, n = np.unique(key, return_counts=True)
    expected = (n**2).sum()
    b = cc.sum() == len(key) and sc.sum() == expected and sc.sum() > cc.sum()
    utility.print_test(
        b,
        f"No Weight, charge induction: counts {cc.sum():.0f} ({len(key)} digi), "
        f"squared counts {sc.sum():.0f} (expected {expected}, "
        f"{(n > 1).sum()} bins with several digi of one event)",
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)
