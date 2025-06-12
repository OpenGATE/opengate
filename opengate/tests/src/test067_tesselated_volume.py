#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import numpy as np
import meshio
import itk


def create_test_mesh(file_name="myTesselatedBoxVolume.stl"):
    mesh = create_box_mesh()
    mesh.write(file_name)


def create_box_mesh():
    """Create a simple cube mesh of 300×300×300 mm³"""

    # Define the vertices and faces of the box using vectors
    vertices = np.array(
        [
            [0, 0, 0],  # Vertex 0
            [1, 0, 0],  # Vertex 1
            [1, 1, 0],  # Vertex 2
            [0, 1, 0],  # Vertex 3
            [0, 0, 1],  # Vertex 4
            [1, 0, 1],  # Vertex 5
            [1, 1, 1],  # Vertex 6
            [0, 1, 1],  # Vertex 7
        ],
        dtype=np.float32,
    )

    # scale vertices from a 1×1×1 mm³ cube to a 0-centered 300×300×300 mm³ cube
    vertices = (vertices - 0.5) * 300

    # Define the faces of the box using vertex indices
    triangles = [
        [0, 3, 1],
        [1, 3, 2],
        [0, 4, 7],
        [0, 7, 3],
        [4, 5, 6],
        [4, 6, 7],
        [5, 1, 2],
        [5, 2, 6],
        [2, 3, 6],
        [3, 7, 6],
        [0, 1, 5],
        [0, 5, 4],
    ]

    cells = [("triangle", triangles)]

    # Create the mesh
    return meshio.Mesh(vertices, cells)


def create_simulation():
    output_path = paths.output

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    eV = gate.g4_units.eV
    MeV = gate.g4_units.MeV
    um = gate.g4_units.um

    # simulation object
    sim = gate.Simulation()

    #
    # Visualization
    sim.visu = False
    sim.visu_verbose = False
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 123456
    sim.number_of_threads = 1
    sim.output_dir = output_path

    # geometry
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = "G4_Galactic"

    tes = sim.add_volume("Tesselated", name="MyTesselatedVolume")
    tes.material = "G4_WATER"
    tes.file_name = output_path / "myTesselatedBoxVolume.stl"
    tes.origin_at_cog = True

    # print the list of available volumes types:
    sim.volume_manager.print_volume_types()

    # sources
    source = sim.add_source("GenericSource", "particle")
    source.particle = "proton"
    source.position.type = "point"
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.position.translation = [0 * cm, 0 * cm, -30 * cm]
    source.energy.type = "gauss"
    source.energy.mono = 60 * MeV
    source.n = 100

    print(f"The energy is {source.energy.mono / eV} eV")

    # Physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"
    global_cut = 500 * um
    sim.physics_manager.global_production_cuts.gamma = global_cut
    sim.physics_manager.global_production_cuts.electron = global_cut
    sim.physics_manager.global_production_cuts.positron = global_cut
    sim.physics_manager.global_production_cuts.proton = global_cut

    # Actors
    # Statistics Actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "Statistics.txt"
    stats.track_types_flag = True

    # Dose Actor
    dose_actor = sim.add_actor("DoseActor", "dose")
    dose_actor.attached_to = tes
    # number of voxels per dimension
    dose_actor.size = [1, 1, 300]
    # size of the voxels
    dose_actor.spacing = [30 * cm, 30 * cm, 1 * mm]
    dose_actor.dose.active = True
    dose_actor.edep_squared.active = True
    dose_actor.hit_type = "random"
    dose_actor.output_filename = "test067_dose.mhd"

    return sim


def eval_results(sim):
    # access to the results
    eval_Volume = sim.volume_manager.get_volume(
        "MyTesselatedVolume"
    ).solid_info.cubic_volume
    print("volume: ", eval_Volume)
    volume_is_ok = utility.check_diff_abs(
        float(eval_Volume), float(27000000.0), tolerance=1e-1, txt="volume"
    )

    dose = sim.get_actor("dose")
    image = dose.edep.get_data()
    np_image = itk.GetArrayFromImage(image)
    # For 1D images, the array is squeezed
    np_image = np.squeeze(np_image)
    # create index array
    array_1d = np.arange(300)
    # Check if the lengths of the arrays match
    if len(array_1d) != len(np_image):
        raise ValueError("Lengths of the arrays do not match")
    (
        r80,
        tmp,
    ) = utility.getRange(array_1d, np_image, percentLevel=0.8)

    print("r80: ", r80)
    r80_is_ok = utility.check_diff_abs(
        float(r80), float(30.43), tolerance=1e-1, txt="R80"
    )

    if volume_is_ok and r80_is_ok:
        is_ok = True
    else:
        is_ok = False
    return is_ok


paths = utility.get_default_test_paths(
    __file__, "test067_tesselated_volume", output_folder="test067"
)


if __name__ == "__main__":
    print("Generating STL data")
    create_test_mesh(file_name=str(paths.output / "myTesselatedBoxVolume.stl"))

    sim = create_simulation()

    print("Running GATE simulation")
    sim.run()

    stats_actor = sim.actor_manager.get_actor("Stats")
    print(stats_actor)

    print("Simulation finished")
    print("Evaluating results")
    is_ok = eval_results(sim)
    utility.test_ok(is_ok)
