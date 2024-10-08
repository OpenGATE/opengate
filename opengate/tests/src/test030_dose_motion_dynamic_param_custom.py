#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
from opengate.tests import utility

# ABOUT THIS TEST:
# This test shows how a user can implement a customized version of a geometry changer
# and add it manually to the simulation
# This test should perform exactly the same simulation as test030_dose_motion_dynamic_param.py,
# but print out extra info in-between the runs

# See also test071_custom_geometry_changer
# Warning: This is intended for advanced GATE users


def print_face():
    print("*******************")
    print("**** ^^^   ^^^ ****")
    print("****  O     O  ****")
    print("****     L     ****")
    print("****  \_____/  ****")
    print("****     V     ****")
    print("*******************")


class MyCustomTranslationChanger(gate.actors.dynamicactors.VolumeTranslationChanger):
    # The VolumeTranslationChanger has a user_info called 'translations' which holds the list of translation vectors
    # you can access it via self.translations

    # implement an 'apply_change() method
    def apply_change(self, run_id):
        # call the apply_change() method from the superclass
        # which will actually apply the translation
        super().apply_change(run_id)
        # now do your own stuff
        print_face()
        print(
            f"This is MyCustomTranslationChanger working on volume {self.attached_to_volume.name} in run {run_id}."
        )
        print(f"Current translation: {self.translations[run_id]}")
        run_interval = self.volume_manager.simulation.run_timing_intervals[run_id]
        print(
            f"This run interval is from {run_interval[0] / gate.g4_units.s} s "
            f"to {run_interval[1] / gate.g4_units.s} s"
        )
        print()


class MyCustomRotationChanger(gate.actors.dynamicactors.VolumeRotationChanger):
    # The VolumeRotationChanger has a user_info called 'rotations' which holds the list of rotation matrices
    # you can access it via self.rotations

    # implement an 'apply_change() method
    def apply_change(self, run_id):
        # call the apply_change() method from the superclass
        # which will actually apply the translation
        super().apply_change(run_id)
        # now do your own stuff
        print_face()
        print(
            f"This is MyCustomRotationChanger working on volume {self.attached_to_volume.name} in run {run_id}."
        )
        print(f"Current rotations: {self.rotations[run_id]}")
        run_interval = self.volume_manager.simulation.run_timing_intervals[run_id]
        print(
            f"This run interval is from {run_interval[0] / gate.g4_units.s} s "
            f"to {run_interval[1] / gate.g4_units.s} s"
        )
        print()


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test029_volume_time_rotation", "test030"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 983456
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    um = gate.g4_units.um
    nm = gate.g4_units.nm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.second

    #  change world size
    sim.world.size = [1 * m, 1 * m, 1 * m]

    # add a simple fake volume to test hierarchy
    # translation and rotation like in the Gate macro
    fake = sim.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.translation = [1 * cm, 2 * cm, 3 * cm]
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.mother = "fake"
    waterbox.size = [20 * cm, 20 * cm, 20 * cm]
    waterbox.translation = [-3 * cm, -2 * cm, -1 * cm]
    waterbox.rotation = Rotation.from_euler("y", -20, degrees=True).as_matrix()
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.set_production_cut("world", "all", 700 * um)

    # default source for tests
    # the source is fixed at the center, only the volume will move
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 150 * MeV
    source.particle = "proton"
    source.position.type = "disc"
    source.position.radius = 5 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 30000 * Bq

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test030-edep.mhd"
    dose.attached_to = "waterbox"
    dose.size = [99, 99, 99]
    mm = gate.g4_units.mm
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.translation = [2 * mm, 3 * mm, -2 * mm]
    dose.edep_uncertainty.active = True

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    # created the translations and rotations which describe the motion of the volume 'fake'
    n = 3
    interval_length = 1 * sec / n
    sim.run_timing_intervals = [
        (i * interval_length, (i + 1) * interval_length) for i in range(n)
    ]
    gantry_angles_deg = [i * 20 for i in range(n)]
    # use a helper function
    (
        dynamic_translations,
        dynamic_rotations,
    ) = gate.geometry.utility.get_transform_orbiting(
        initial_position=fake.translation, axis="Y", angle_deg=gantry_angles_deg
    )

    # create the changers manually
    translation_changer = MyCustomTranslationChanger(name="translation_changer")
    rotation_changer = MyCustomRotationChanger(name="rotation_changer")
    # set the translations and rotations
    translation_changer.translations = dynamic_translations
    translation_changer.attached_to = fake
    rotation_changer.rotations = dynamic_rotations
    rotation_changer.attached_to = fake

    # add a DynamicGeometryActor to the simulation
    dyn_geo_actor = sim.add_actor("DynamicGeometryActor", name="dyn_geo_actor")
    # ... and add the changers to the actor
    dyn_geo_actor.geometry_changers.append(translation_changer)
    dyn_geo_actor.geometry_changers.append(rotation_changer)

    # start simulation
    sim.run()

    # print results at the end
    print(stats)

    # tests
    stats_ref = utility.read_stat_file(paths.output_ref / "stats030.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.11)

    print()
    gate.exception.warning("Difference for EDEP")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "test030-edep.mhd",
            dose.edep.get_output_path(),
            stats,
            tolerance=30,
            ignore_value=0,
        )
        and is_ok
    )

    print("\nDifference for uncertainty")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "test030-edep_uncertainty.mhd",
            dose.edep_uncertainty.get_output_path(),
            stats,
            tolerance=15,
            ignore_value=1,
        )
        and is_ok
    )

    utility.test_ok(is_ok)
