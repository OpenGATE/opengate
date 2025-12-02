#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate

# This test demonstrates how a user can implement a custom GeometryChanger
# by inheriting from the GeometryChanger class.
# This is interesting for expert users who want to customize their dynamic simulation

# Note that this test creates a new changer. See test XXX for an example on how to extend an existing changer.


# Write a custom changer which inherits from GeometryChanger
# The GeometryChanger class has a user_info item called 'attached_to'
# which stores the name of the volume to which it is attached.
# You can use this out-of-the-box
# all you need to do is implement an 'apply_change' method which should take the run_id as input
# you have access to the hierarchy of managers via self.volume_manager
class MyCustomChanger(gate.actors.dynamicactors.GeometryChanger):
    # implement an 'apply_change() method
    def apply_change(self, run_id):
        print("*******************")
        print("**** ^^^   ^^^ ****")
        print("****  O     O  ****")
        print("****     L     ****")
        print("****  \\_____/  ****")
        print("****     V     ****")
        print("*******************")
        print(f"This is volume {self.attached_to_volume.name} in run {run_id}.")
        run_interval = self.volume_manager.simulation.run_timing_intervals[run_id]
        print(
            f"This run interval is from {run_interval[0] / gate.g4_units.s} s "
            f"to {run_interval[1] / gate.g4_units.s} s"
        )
        print()


if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False

    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    sec = gate.g4_units.second

    box = sim.add_volume("BoxVolume", name="box")
    sphere = sim.add_volume("SphereVolume", name="sphere")
    sphere.translation = [10 * cm, 0, 0]

    # create the changer objects and attach them to the objects
    my_changer_for_box = MyCustomChanger(name="my_changer_for_box")
    my_changer_for_box.attached_to = box
    my_changer_for_sphere = MyCustomChanger(name="my_changer_for_sphere")
    my_changer_for_sphere.attached_to = sphere

    # create a DynamicGeometryActor and add the changers to it
    # you only need one of them and
    dyngeoactor = sim.add_actor("DynamicGeometryActor", name="dyngeoactor")
    dyngeoactor.geometry_changers.append(my_changer_for_sphere)
    dyngeoactor.geometry_changers.append(my_changer_for_box)

    source = sim.add_source("GenericSource", "proton_source")
    source.energy.mono = 100 * MeV
    source.particle = "proton"
    source.position.type = "sphere"
    source.position.radius = 1 * cm
    source.position.translation = [40 * cm, 0, 0 * cm]
    source.activity = 10 * Bq
    source.direction.type = "momentum"
    source.direction.momentum = [1, 0, 0]

    sim.run_timing_intervals = [(0, 1 * sec), (1 * sec, 2 * sec), (20 * sec, 21 * sec)]

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")

    # start simulation
    sim.run()
