#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import matplotlib.pyplot as plt
import numpy as np
import uproot
import opengate as gate
from opengate.tests import utility


def test108_test(df, output_dir=None):
    overall_valid = True

    allowedE = {0.510999, 1.274497}  # MeV,
    # validation rules  for position of gamma ancestors : annihilation or isomeric transition
    validation_rules = {
        0.510999: {"mean_max": 1.0, "max_max": 8.0},
        1.274497: {"mean_max": 0.0, "max_max": 0.0},
    }
    tolE = 0.001
    energies = df["GammaVertexKineticEnergy"]
    origin_x = df["GammaPosition_X"]
    origin_y = df["GammaPosition_Y"]
    origin_z = df["GammaPosition_Z"]
    n_entries = len(energies)

    # Masks for each energy
    masks = {E: energies.apply(lambda x: abs(x - E) < tolE) for E in allowedE}

    # Compute Euclidean distances for each energy group
    distances = {
        E: np.sqrt(
            origin_x[masks[E]] ** 2 + origin_y[masks[E]] ** 2 + origin_z[masks[E]] ** 2
        )
        for E in allowedE
    }

    # ----------------------------------------------------
    # Test for Ratio  of intensities nb(E0)/nb(E1)
    # ----------------------------------------------------
    tolf = 0.06
    fraction = 1.81  # expected intensity ratio for the annhilations photons wrp to 1.274 keV  photon
    E0, E1 = allowedE
    n_E0 = masks[E0].sum()
    n_E1 = masks[E1].sum()
    if n_E0 == 0 or n_E1 == 0:
        overall_valid = False
    else:
        ratio_E0_E1 = n_E0 / n_E1
        print(f"Ratio nb(E0)/nb(E1) = {ratio_E0_E1:.6f}")
        if ratio_E0_E1 < fraction - tolf or ratio_E0_E1 > fraction:
            print(
                f"[FAIL] Ratio nb(E0)/nb(E1) = {ratio_E0_E1:.6f} (allowed between 1.76 and 1.81)"
            )
            overall_valid = False

    # ----------------------------------------------------
    # Test for ancestor position
    # ---------------------------------------------------
    for E in allowedE:
        d = distances[E]
        mean_d = d.mean()
        max_d = d.max()

        # -----------------------------
        # Plotting
        # -----------------------------
        plt.figure(figsize=(8, 5))
        plt.hist(d, bins=60, alpha=0.7, color="steelblue")
        plt.title(f"Euclidean distance distribution for E = {E} MeV")
        plt.xlabel("Distance (mm)")
        plt.ylabel("Counts")

        plt.axvline(
            mean_d,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Mean = {mean_d:.2f}",
        )
        plt.axvline(
            max_d,
            color="green",
            linestyle="--",
            linewidth=2,
            label=f"Max = {max_d:.2f}",
        )

        plt.legend()
        plt.tight_layout()

        if output_dir is not None:
            fname = os.path.join(output_dir, f"dist_E_{E:.6f}.png")
            print(f"Figure saved in {fname}")
            plt.savefig(fname, dpi=200)

        plt.close()

        # -----------------------------
        # Validation rules depending on the  photon, annihilation or isomeric trqnsition
        # -----------------------------
        rules = validation_rules[E]
        if mean_d > rules["mean_max"] or max_d > rules["max_max"]:
            print(
                f"[FAIL] E={E}: mean={mean_d:.3f} (allowed ≤ {rules['mean_max']}), "
                f"max={max_d:.3f} (allowed ≤ {rules['max_max']})"
            )
            overall_valid = False

    # ----------------------------------------------------
    #  test for fraction of 'invalid' events (not allowed energies), aroudn 0.3%  due to positron annihilation in the fly ?
    # -----------------------------------------------------------------------------------------
    valid = energies.apply(lambda x: any(abs(x - e) < tolE for e in allowedE))
    mask_invalid = ~energies.isna() & ~valid
    inv_energies = energies[mask_invalid]
    inv_particle = df.loc[mask_invalid, "ParticleName"]
    inv_proces = df.loc[mask_invalid, "TrackCreatorProcess"]
    n_invalid = len(inv_energies)
    print("percentage of invalid entries (%): ", n_invalid / n_entries * 100)
    if n_invalid / n_entries > 0.01:
        print("Invalid energies found:")
        for e, p, proc in zip(inv_energies, inv_particle, inv_proces):
            print(f"Energy: {e}, Particle: {p}, Process: {proc}")
        overall_valid = False

    return overall_valid


def main():

    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test108_att_gamma_origin"
    )

    """
    This test check the new attribute ParticleAncestorAttribute
    This attribute store the position/energy of the first gamma that is parent of the current particle (including  itself).
    """
    print(paths)

    # create the simulation
    sim = gate.Simulation()
    sim.visu = False
    sim.visu_type = "qt"
    sim.random_seed = "auto"
    sim.output_dir = paths.output
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s

    # world size
    world = sim.world
    world.size = [0.5 * m, 0.5 * m, 0.5 * m]

    # water encapsulation for the annihilation of the positron
    encapsulation = sim.add_volume("Sphere", "encapsulation")
    encapsulation.rmin = 0 * cm
    encapsulation.rmax = 1 * cm
    encapsulation.translation = [0, 0, 0]
    encapsulation.material = "G4_WATER"
    encapsulation.color = [0, 0, 1, 1]

    # sphere around
    sphere = sim.add_volume("Sphere", "sphere")
    sphere.rmin = 10 * cm
    sphere.rmax = 11 * cm
    sphere.material = "G4_AIR"

    # source
    source = sim.add_source("GenericSource", "Nas22_source")
    source.attached_to = encapsulation  # for the annihilation of the positrorn
    source.particle = "ion 11 22"  # Na22
    source.energy.type = "mono"
    source.energy.mono = 0
    source.position.type = "point"
    source.direction.type = "iso"
    source.activity = 5000 * Bq
    source.half_life = 8.205 * 1e07 * sec  # I need to give this to have results

    # new attribute
    att1 = sim.activate_auxiliary_attribute(
        "ParticleAncestorAttribute", "GammaPosition"
    )
    att1.value_to_store = "VertexPosition"
    att1.particle_name = "gamma"  # this is the default
    att2 = sim.activate_auxiliary_attribute(
        "ParticleAncestorAttribute", "GammaVertexKineticEnergy"
    )
    att2.value_to_store = "VertexKineticEnergy"

    # phase space
    phsp = sim.add_actor("PhaseSpaceActor", "phase_space")
    phsp.attached_to = sphere
    phsp.output_filename = "test108_phase_space.root"
    phsp.attributes = [
        "EventID",
        "TrackID",
        "ParentID",
        "ParticleName",
        "PreKineticEnergy",
        "PrePosition",
        "TrackCreatorProcess",
        att1.name,
        att2.name,
    ]
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)

    sim.run_timing_intervals = [[0, 2.5 * sec]]

    # stats
    stat = sim.add_actor("SimulationStatisticsActor", "stat")
    stat.track_types_flag = True

    # physics with decay
    sim.physics_manager.enable_decay = True

    # run
    sim.run()
    print(stat)

    # test
    print(phsp.get_output_path())
    phsp_out = uproot.open(
        str(paths.output) + "/" + str(phsp.output_filename) + ":phase_space"
    )

    df = phsp_out.arrays(library="pd")
    is_ok = test108_test(df, output_dir=paths.output)

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
