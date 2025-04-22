import opengate as gate
import opengate_core as g4
import opengate.geometry.solids as solids
import opengate.geometry.volumes as volumes
import opengate.managers as managers

import opengate.tests.utility as tu

import pathlib

from scipy.spatial.transform import Rotation


# units
m = gate.g4_units.m
cm = gate.g4_units.cm
mm = gate.g4_units.mm
nm = gate.g4_units.nm
Bq = gate.g4_units.Bq
MeV = gate.g4_units.MeV

if __name__ == "__main__":

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = True
    sim.visu_verbose = True
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 1
    sim.random_seed = "auto"
    sim.progress_bar = True

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    world = sim.add_volume("Box", "World")
    world.size = [1.0 * gate.g4_units.m, 1.0 * gate.g4_units.m, 1.0 * gate.g4_units.m]
    world.material = "G4_AIR"
    world.color = [1, 1, 1, 0.1]
    print(world)

    EllipVolume1 = sim.add_volume("EllipsoidVolume", "Brain")
    EllipVolume1.xSemiAxis = 6.0 * cm
    EllipVolume1.ySemiAxis = 9.0 * cm
    EllipVolume1.zSemiAxis = 5.0 * cm
    EllipVolume1.zBottomCut = 0 * cm
    EllipVolume1.zTopCut = 0 * cm

    EllipVolume1.translation = [0, 0, 1.0 * cm]
    EllipVolume1.material = "G4_WATER"
    EllipVolume1.color = [1, 0, 0, 0.1]
    print(EllipVolume1)

    # default source for tests
    source = sim.add_source("GenericSource", "Default")
    source.particle = "proton"
    source.energy.mono = 240 * MeV
    source.position.radius = 1 * cm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 50 * Bq

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    sim.run()

    # print results at the end
    print(stats)
