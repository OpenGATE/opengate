#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ScatterSplittingFreeFlightActor with the detector in a parallel world.

A point source of 140.5 keV in a water cylinder; below it a head (air
box) with a CdTe crystal. The head is excluded from the biasing and is a
kill volume: the detector must stay fully analog. The same FF scatter
simulation is run twice, the head in the mass world and the head in a
parallel world; both must give the same spectrum of the singles in the
crystal (weighted counts per energy range).

The secondaries of the free-flight photons (Cd / Te K X-rays of 23-31 keV,
photoelectrons) are not free-flight tracks: they must not be killed in the
head (by the kill volume rule, nor by the energy cutoff), otherwise the
deposited energy is too low (more counts between 55 and 95 keV, fewer in
the peak).
"""

import numpy as np
import uproot
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility

mm = gate.g4_units.mm
cm = gate.g4_units.cm
keV = gate.g4_units.keV
deg = gate.g4_units.deg
Bq = gate.g4_units.Bq
sec = gate.g4_units.s

energy_ranges = {
    "55-95 keV": (55, 95),
    "95-125 keV": (95, 125),
    "125-145 keV": (125, 145),
}


def run(paths, parallel, n, seed):
    name = "pw" if parallel else "mw"
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.random_seed = seed
    sim.number_of_threads = 1
    sim.progress_bar = False
    sim.world.size = [1 * 1000 * mm] * 3
    sim.world.material = "G4_Galactic"

    water = sim.add_volume("Tubs", "water")
    water.rmin = 0
    water.rmax = 10 * cm
    water.dz = 10 * cm
    water.rotation = Rotation.from_euler("x", 90, degrees=True).as_matrix()
    water.material = "G4_WATER"

    mother = "world"
    if parallel:
        sim.add_parallel_world("world2")
        mother = "world2"
    head = sim.add_volume("Box", "head")
    head.mother = mother
    head.size = [6 * cm, 6 * cm, 3 * cm]
    head.translation = [0, 0, -12 * cm - head.size[2] / 2]
    head.material = "G4_AIR"
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = head.name
    crystal.size = [4 * cm, 4 * cm, 6 * mm]
    crystal.translation = [0, 0, 0]
    crystal.material = "G4_CADMIUM_TELLURIDE"

    source = sim.add_source("GenericSource", "src")
    source.particle = "gamma"
    source.energy.mono = 140.5 * keV
    source.position.type = "point"
    source.direction.type = "iso"
    source.activity = n * Bq
    sim.run_timing_intervals = [[0, 1 * sec]]

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 50 * mm)
    sim.physics_manager.set_production_cut(crystal.name, "all", 0.1 * mm)
    sim.physics_manager.em_parameters.fluo = True
    sim.g4_commands_before_init.append("/process/em/UseGeneralProcess false")

    ff = sim.add_actor("ScatterSplittingFreeFlightActor", "ff")
    ff.attached_to = "world"
    ff.weight_cutoff = 1e-20
    ff.energy_cutoff = 0.85 * 108.9 * keV
    ff.exclude_volumes = [head.name]
    ff.kill_interacting_in_volumes = [head.name]
    ff.compton_splitting_factor = 20
    ff.rayleigh_splitting_factor = 20
    ff.max_compton_level = 3
    aa = ff.angular_acceptance
    aa.policy = "Rejection"
    aa.skip_policy = "SkipEvents"
    aa.enable_intersection_check = True
    aa.target_volumes = [crystal.name]
    aa.enable_angle_check = True
    aa.angle_check_reference_vector = [0, 0, -1]
    aa.angle_tolerance_max = 60 * deg

    hc = sim.add_actor("DigitizerHitsCollectionActor", "hits")
    hc.attached_to = crystal.name
    hc.attributes = [
        "TotalEnergyDeposit",
        "PostPosition",
        "GlobalTime",
        "PreStepUniqueVolumeID",
        "Weight",
        "EventID",
    ]
    hc.write_to_disk = False
    sc = sim.add_actor("DigitizerAdderActor", "singles")
    sc.attached_to = crystal.name
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWinnerPosition"
    sc.output_filename = f"test085_scatter_{name}.root"

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    sim.run(start_new_process=True)
    print(stats)
    print(sim.get_actor("ff"))

    t = uproot.open(sc.get_output_path())["singles"]
    e = t["TotalEnergyDeposit"].array(library="np") / keV
    w = t["Weight"].array(library="np")
    r = {}
    for k, (lo, hi) in energy_ranges.items():
        m = (e >= lo) & (e < hi)
        r[k] = (np.sum(w[m]), np.sum(w[m] ** 2))
    return r


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test085")
    n = 1e5
    mass = run(paths, False, n, 123)
    para = run(paths, True, n, 456)

    is_ok = True
    for k in energy_ranges:
        (sm, vm), (sp, vp) = mass[k], para[k]
        ratio = sp / sm
        z = (sp - sm) / np.sqrt(vm + vp)
        b = abs(z) < 4
        utility.print_test(
            b,
            f"{k}: parallel / mass world {ratio:.3f} "
            f"(rel. sigma {np.sqrt(vm) / sm:.3f}, {np.sqrt(vp) / sp:.3f}), z {z:+.2f}",
        )
        is_ok = is_ok and b
    utility.test_ok(is_ok)
