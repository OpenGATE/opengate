#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate.contrib.pet.philipsvereos as vereos
import opengate.contrib.pet.castor_helpers as castor
from scipy.spatial.transform import Rotation
from test096_pet_castor_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test096_pet_blur3"
    )

    # folders
    output_path = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq

    # options
    sim = gate.Simulation()
    sim.random_seed = 654321
    sim.number_of_threads = 5
    sim.output_dir = output_path
    sim.verbose_level = gate.logger.NONE

    # world
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]
    world.material = "G4_AIR"

    # create the pet and move it
    pet = vereos.add_pet(sim, "pet", nb_module=8)
    pet.translation = [-3 * cm, 14 * cm, 2 * cm]
    pet.rotation = Rotation.from_euler("yx", (-10, 30), degrees=True).as_matrix()

    # get the crystal volume
    crystal = sim.volume_manager.get_volume("pet_crystal")

    # set a (fake) digitizer
    hits_actor, blur_actor = add_test_digitizer(
        sim, crystal, "output_blur3_truncated_gaussian.root"
    )
    blur_actor.keep_in_solid_limits = True
    blur_actor.use_truncated_Gaussian = True

    # source and physics
    stats = test_add_physics_and_stats(sim, "pet")
    activity = 1000 * Bq / sim.number_of_threads
    test_add_b2b_source(sim, activity)

    # Save volumes
    filename = paths.output / "castor_config_blur3.json"
    param = castor.set_hook_castor_config(sim, crystal.name, filename)

    # go (with test several runs, because the VolumeUIDAsInt is reset each run)
    print(f"Run a simulation of 1 sec, 3 runs, with {activity/Bq:.0f} Bq")
    sec = gate.g4_units.s
    sim.run_timing_intervals = [
        [0, 0.5 * sec],
        [0.5 * sec, 0.75 * sec],
        [0.75 * sec, 1 * sec],
    ]
    sim.run()

    # get the castor_config
    castor_config = param["castor_config"]

    # 1) read all hits/singles in the root file
    fn = hits_actor.get_output_path()
    branch_name = "singles_blur"
    vol_ids, positions, local_positions = read_root_positions(fn, branch_name)

    # 3) get tr, rot, size (compute index)
    translations, rotations, sizes = get_positions_of_volumes(vol_ids, castor_config)
    s = sizes[0]
    print(f"Volume bounding : {s[0]/2.0} {s[1]/2.0} {s[2]/2.0}")

    # 4) are points in volume (this can be vectorized, but we wrote it as a loop
    # to make the transformation explicit)
    is_inside_mask = np.ones(len(vol_ids), dtype=bool)
    for i in range(len(vol_ids)):
        p = positions[i]
        size = sizes[i]
        half_size = size / 2.0 + 1e-5  # (tolerance)
        tpos = np.dot(rotations[i].T, (p - translations[i]))
        # check if the point is inside the volume
        is_inside = (np.abs(tpos) <= half_size).all()
        # distance be local_position and tpos
        if not is_inside:
            d = np.linalg.norm(local_positions[i] - tpos)
            if d > 1e-8:
                is_ok = False
                print(
                    f"{i} {is_inside} {vol_ids[i]} pos = {positions[i]} lpos = {local_positions[i]} tpos = {tpos} => {d}"
                )
        is_inside_mask[i] = is_inside
    outside = np.sum(~is_inside_mask)
    print(f"Number of hits outside the volumes : {outside} / {len(vol_ids)}")

    # check
    is_ok = True
    if outside > 0:
        is_ok = False
    utility.print_test(
        is_ok, f"All hits MUST be inside the volume {outside} / {len(vol_ids)}"
    )

    # write a vrml file for debug
    vrml_filename = output_path / "castor_config_blur3.vrml"
    create_vrml_from_config(filename, vrml_filename)
    add_hits_to_vrml(vrml_filename, positions, is_inside_mask)

    utility.test_ok(is_ok)
