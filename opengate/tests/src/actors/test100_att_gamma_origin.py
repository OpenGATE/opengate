#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import matplotlib.pyplot as plt
import numpy as np
import uproot
import opengate as gate
from opengate.contrib.root_helpers import *
from opengate.tests import utility


def main():

    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test100_att_gamma_origin"
    )

    """
    This test check the new attribute XXXX.

    This attribute store the position/energy of the first gamma that is parent of the current particle (including   itself).
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

    # world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [10 * cm, 10 * cm, 10 * cm]
    waterbox.translation = [0, 0, 0]
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]

    # sphere around
    sphere = sim.add_volume("Sphere", "sphere")
    sphere.rmin = 15 * cm
    sphere.rmax = 16 * cm
    sphere.material = "G4_AIR"

    # source
    source = sim.add_source("GenericSource", "source")
    source.particle = "ion 89 225"
    source.energy.mono = 0
    source.position.type = "sphere"
    source.position.radius = 5 * mm
    source.direction.type = "iso"
    source.activity = 5000 * Bq

    # new attribute
    att1 = sim.activate_auxiliary_attribute("GammaAncestorAttribute", "GammaPosition")
    att1.value_to_store = "VertexPosition"
    att2 = sim.activate_auxiliary_attribute(
        "GammaAncestorAttribute", "GammaVertexKineticEnergy"
    )
    att2.value_to_store = "VertexKineticEnergy"

    # phase space
    phsp = sim.add_actor("PhaseSpaceActor", "phase_space")
    phsp.attached_to = sphere
    phsp.output_filename = "phase_space.root"
    phsp.attributes = [
        "EventID",
        "TrackID",
        "ParentID",
        "ParticleName",
        "PreKineticEnergy",
        "PrePosition",
        att1.name,
        att2.name,
    ]

    # stats
    stat = sim.add_actor("SimulationStatisticsActor", "stat")
    stat.track_types_flag = True

    # physics with decay
    sim.physics_manager.enable_decay = True

    # run
    sim.run()

    # todo
    is_ok = True
    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
