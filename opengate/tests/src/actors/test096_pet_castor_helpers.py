import opengate as gate
from opengate.contrib.root_helpers import *
from opengate.contrib.pet.castor_helpers import *
from opengate.tests import utility


def add_test_digitizer(sim, crystal, filename="output.root"):
    # Hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", f"hits")
    hc.attached_to = crystal.name
    hc.authorize_repeated_volumes = True
    hc.output_filename = filename
    hc.attributes = [
        "EventID",
        "PostPosition",
        "PostPositionLocal",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "PreStepUniqueVolumeIDAsInt",
        "GlobalTime",
        "ParticleName",
    ]

    # Singles
    # sc = sim.add_actor("DigitizerReadoutActor", f"singles")
    # sc.discretize_volume = crystal.name
    sc = sim.add_actor("DigitizerAdderActor", f"singles")
    sc.attached_to = hc.attached_to
    sc.authorize_repeated_volumes = True
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.group_volume = crystal.name
    sc.output_filename = hc.output_filename

    # spatial blurring
    mm = gate.g4_units.mm
    bc = sim.add_actor("DigitizerSpatialBlurringActor", f"singles_blur")
    bc.attached_to = hc.attached_to
    bc.output_filename = hc.output_filename
    bc.input_digi_collection = sc.name
    bc.keep_in_solid_limits = True
    bc.use_truncated_Gaussian = True
    bc.blur_attribute = "PostPosition"
    bc.authorize_repeated_volumes = True
    bc.blur_fwhm = [5 * mm, 5 * mm, 5 * mm]

    return hc, bc


def test_add_physics_and_stats(sim, pet_name="pet"):
    mm = gate.g4_units.mm
    m = gate.g4_units.m
    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    # sim.physics_manager.enable_decay = True
    sim.physics_manager.set_production_cut("world", "all", 1 * m)
    sim.physics_manager.set_production_cut(pet_name, "all", 1 * mm)

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "stats.txt"
    return stats


def test_add_b2b_source(sim, activity, name="b2b"):
    # units
    mm = gate.g4_units.mm
    keV = gate.g4_units.keV
    deg = gate.g4_units.deg
    red = [1, 0, 0, 1]

    cyl = sim.add_volume("Tubs", name)
    cyl.rmin = 0 * mm
    cyl.rmax = 5 * mm
    cyl.dz = 35 * mm
    cyl.sphi = 0 * deg
    cyl.dphi = 360 * deg
    cyl.color = red
    cyl.material = "G4_WATER"

    source = sim.add_source("GenericSource", name)
    source.attached_to = cyl.name
    source.particle = "back_to_back"
    source.activity = activity
    source.position.type = "cylinder"
    source.position.radius = cyl.rmax
    source.position.dz = cyl.dz
    source.energy.mono = 511 * keV
    source.direction.type = "iso"


def read_root_positions(root_file_path, tree_name="hits"):
    # open the root file
    tree = root_read_tree(root_file_path, tree_name)

    # Get the branches as np arrays (FIXME -> np ? ak ?)
    vol_ids = root_tree_get_branch(tree, "PreStepUniqueVolumeIDAsInt")
    positions = root_tree_get_branch(tree, "PostPosition")
    local_positions = root_tree_get_branch(tree, "PostPositionLocal")

    return vol_ids, positions, local_positions


def get_positions_of_volumes(vol_ids, castor_config):
    # get the indices of the volumes in the castor config
    vol_index = build_castor_config_volume_index(castor_config)
    get_indices = np.vectorize(vol_index.get, otypes=[int])

    # Create a mask for hits in known volumes
    known_mask = np.isin(vol_ids, castor_config["unique_volume_id"])
    valid_vol_ids = vol_ids[known_mask]
    indices = get_indices(valid_vol_ids)

    # Gather the geometry data for all valid hits
    translations = castor_config["translation"][indices]
    rotations = castor_config["rotation"][indices]
    sizes = castor_config["size"][indices]

    return translations, rotations, sizes


def assert_positions(fn, branch_name, castor_config, check_pos=False):
    print(f"Testing positions in {fn} on branch {branch_name}")
    vol_ids, positions, local_positions = read_root_positions(fn, branch_name)
    is_ok = True

    # 2) Look at the vols_ids of the hits, 100% must be inside the castor file
    unknown_masks = ~np.isin(vol_ids, castor_config["unique_volume_id"])
    missing = vol_ids[unknown_masks]
    if len(missing) > 0:
        print(f"Some hits are not in the castor file: {missing}")
        is_ok = False
    utility.print_test(is_ok, f"All unique volume ids are in the castor file")

    # 3) get tr, rot, size (compute index)
    translations, rotations, sizes = get_positions_of_volumes(vol_ids, castor_config)

    # 4) are points in the volume? This can be vectorized, by we wrote it as a loop
    # to make the transformation explicit
    for i in range(len(vol_ids)):
        p = positions[i]
        size = sizes[i]
        half_size = size / 2.0 + 1e-9  # (tolerance)
        tpos = np.dot(rotations[i].T, (p - translations[i]))
        is_inside = (np.abs(tpos) <= half_size).all()
        # distance be local_position and tpos
        d = np.linalg.norm(local_positions[i] - tpos)
        if not is_inside or (check_pos and d > 1e-5):
            is_ok = False
            print(
                f"{i} {vol_ids[i]} pos = {positions[i]} lpos = {local_positions[i]} tpos = {tpos} => {d} ERROR"
            )
    utility.print_test(is_ok, f"All {len(vol_ids)} hits are inside the volumes")

    return is_ok


def add_hits_to_vrml(output_vrml_path, positions, is_inside_mask, sphere_radius=3.0):
    """
    Appends VRML spheres to an existing file to visualize hit locations.
    Green spheres are for hits inside their volume, red for those outside.
    """
    print(f"Appending {len(positions)} hit visualizations to {output_vrml_path} ...")

    # Open the file in append mode ('a') to add to the existing content
    with open(output_vrml_path, "a") as f:
        f.write("\n# --- Hit Visualizations --- \n\n")

        for i in range(len(positions)):
            pos = positions[i]
            is_inside = is_inside_mask[i]

            color = (
                "0 1 0" if is_inside else "1 0 0"
            )  # Green for inside, Red for outside

            f.write(f"# Hit instance #{i} - {'Inside' if is_inside else 'OUTSIDE'}\n")
            f.write("Transform {\n")
            f.write(f"  translation {pos[0]:.4f} {pos[1]:.4f} {pos[2]:.4f}\n")
            f.write("  children [\n")
            f.write("    Shape {\n")
            f.write("      appearance Appearance {\n")
            f.write("        material Material {\n")
            f.write(f"          diffuseColor {color}\n")
            f.write("        }\n")
            f.write("      }\n")
            f.write("      geometry Sphere {\n")
            f.write(f"        radius {sphere_radius}\n")
            f.write("      }\n")
            f.write("    }\n")
            f.write("  ]\n")
            f.write("}\n\n")

    print()
    print("Finished appending hits. You can visualize the hits with:")
    print(f"opengate_visu -i {output_vrml_path}")
