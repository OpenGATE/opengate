import opengate as gate
from opengate.tests import utility

import stl
import numpy as np
import itk


def create_test_mesh(file_name="myTesselatedBoxVolume.stl"):
    mode = stl.Mode(1)  # ASCII
    # file_name = "myTesselatedBoxVolume.stl"
    my_mesh = create_box_mesh()
    translate_mesh_to_center(my_mesh)
    show_mesh_info(my_mesh)
    store_mesh_to_file(my_mesh, file_name, mode=mode)


def create_box_mesh():
    """Create a simple cube mesh of 300x300x300 mm"""
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
        dtype=np.float64,
    )
    # shift to center
    # vertices -= 0.5
    # scale vertices from a 1x1x1 mm cube to a 300x300x300 mm cube
    scale = 300
    vertices[:, 0] *= scale
    vertices[:, 1] *= scale
    vertices[:, 2] *= scale
    # vertices *= scale

    # Define the faces of the box using vertex indices
    faces = np.array(
        [
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
    )
    # Create the mesh
    box_mesh = stl.mesh.Mesh(np.zeros(faces.shape[0], dtype=stl.mesh.Mesh.dtype))
    for i, f in enumerate(faces):
        for j in range(3):
            box_mesh.vectors[i][j] = vertices[f[j]]

    # create a mesh from the data#
    # box_mesh = mesh.Mesh(data.copy())
    return box_mesh


def read_mesh_from_file(file_name):
    # Using an existing stl file:
    box_mesh = stl.mesh.Mesh.from_file(file_name)
    return box_mesh


def translate_mesh_to_center(mesh_to_translate):
    # translate the mesh to the center of gravity
    cog = mesh_to_translate.get_mass_properties()[1]
    mesh_to_translate.translate(-cog)
    return mesh_to_translate


def show_mesh_info(mesh_to_use):
    volume, cog, inertia = mesh_to_use.get_mass_properties()
    print("volume ", volume)
    print("center of gravity ", cog)
    # print("inertia ", inertia)
    # print("get_unit_normals ", mesh_to_use.get_unit_normals())
    print("is_closed ", mesh_to_use.is_closed())


def store_mesh_to_file(mesh_to_store, file_name, mode=0):
    dir(mesh_to_store)
    mesh_to_store.save(file_name, mode=mode)


def simulation():
    output_path = paths.output

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    eV = gate.g4_units.eV
    MeV = gate.g4_units.MeV
    um = gate.g4_units.um
    nm = gate.g4_units.nm
    km = gate.g4_units.km
    gcm3 = gate.g4_units.g / gate.g4_units.cm3
    deg = gate.g4_units.deg
    mrad = gate.g4_units.mrad

    energy = 60 * MeV
    print(f"The energy is {energy/eV} eV")

    # simulation object
    sim = gate.Simulation()
    ui = sim.user_info

    #
    # Visualization
    ui.visu = False
    ui.visu_verbose = False

    ui.random_engine = "MersenneTwister"
    ui.random_seed = "auto"
    ui.number_of_threads = 1

    # geometry
    # There is a default volume called world (lowercase)
    #  change world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = "G4_Galactic"

    tes = sim.add_volume("Tesselated", name="MyTesselatedVolume")
    tes.material = "G4_WATER"
    tes.mother = "world"  # by default
    tes.file_name = output_path / "myTesselatedBoxVolume.stl"

    # print the list of available volumes types:
    print("Volume types :", sim.volume_manager.dump_volume_types())

    # sources
    source = sim.add_source("GenericSource", "particle")
    source.mother = "world"
    source.particle = "proton"

    source.position.type = "point"
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.position.translation = [0 * cm, 0 * cm, -30 * cm]

    source.energy.type = "gauss"
    source.energy.mono = energy
    source.n = 10000

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
    stats.output = output_path / "Statistics.txt"
    stats.track_types_flag = True

    # Dose Actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.mother = "MyTesselatedVolume"
    # number of voxels per dimension
    dose.size = [1, 1, 300]
    # size of the voxels
    dose.spacing = [30 * cm, 30 * cm, 1 * mm]
    dose.uncertainty = False
    dose.hit_type = "random"
    dose.output = output_path / "Edep.mhd"

    # start simulation
    sim.run()
    return sim


def eval_results(simLink):
    # access to the results
    eval_Volume = simLink.volume_manager.get_volume(
        "MyTesselatedVolume"
    ).solid_info.cubic_volume
    print("volume: ", eval_Volume)
    volume_is_ok = utility.check_diff_abs(
        float(eval_Volume), float(27000000.0), tolerance=1e-1, txt="volume"
    )

    dose = simLink.output.get_actor("dose")
    image = dose.py_edep_image
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
    __file__, "test066_stl_volume", output_folder="test066"
)


def main():
    print("Generating STL data")
    create_test_mesh(file_name=paths.output / "myTesselatedBoxVolume.stl")
    print("Running Gate Simulation")
    simLink = simulation()
    print("Simulation finished")
    print("Evaluating results")
    is_ok = eval_results(simLink)
    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
