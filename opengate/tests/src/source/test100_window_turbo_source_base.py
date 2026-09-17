import opengate as gate
import numpy as np
from opengate.tests import utility
import matplotlib.pyplot as plt


def build_collimator(sim, head, pin_radius_up=3.6, pin_radius_down=13.6):
    world = sim.world
    gcm3 = gate.g4_units.g_cm3
    mm = gate.g4_units.mm
    sim.volume_manager.material_database.add_material_weights(
        "Tungsten",
        ["W"],
        [1],
        19.3 * gcm3,
    )

    pinboard_inner = sim.add_volume("Box", "pinboard_inner")
    pinboard_inner.mother = head
    pinboard_inner.material = "Tungsten"
    pinboard_inner.translation = [0, -59.5 * mm, 0]
    pinboard_inner.size = [500 * mm, 2 * mm, 500 * mm]
    pinboard_inner.color = [0.5, 0.5, 0.5, 0.5]

    # kill_actor_inner = sim.add_actor("KillActor", "kill_inner")
    # kill_actor_inner.attached_to = "pinboard_inner"

    pinboard_cylinder = sim.add_volume("Tubs", "pin_cylinder")
    pinboard_cylinder.mother = pinboard_inner
    pinboard_cylinder.rmin = 0
    pinboard_cylinder.rmax = pin_radius_up * mm
    pinboard_cylinder.dz = 1 * mm
    pinboard_cylinder.material = "G4_AIR"
    pinboard_cylinder.rotation = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    pinboard_cylinder.color = [1, 1, 1, 1]

    pinboard_outer = sim.add_volume("Box", "pinboard_outer")
    pinboard_outer.mother = head
    pinboard_outer.material = "Tungsten"
    pinboard_outer.translation = [0, -67 * mm, 0]
    pinboard_outer.size = [500 * mm, 12.99999 * mm, 500 * mm]
    pinboard_outer.color = [0.5, 0.5, 0.5, 0.5]

    pin_cone = sim.add_volume("Cons", "pin_cone")
    pin_cone.mother = pinboard_outer
    pin_cone.rmax1 = pin_radius_up * mm
    pin_cone.rmax2 = pin_radius_down * mm
    pin_cone.rmin1 = 0
    pin_cone.rmin2 = 0
    pin_cone.dz = (12.99999 / 2) * mm
    pin_cone.material = "G4_AIR"
    pin_cone.rotation = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    pin_cone.color = [1, 1, 1, 1]
    pin_cone.dphi = 2 * np.pi

    # kill_actor_outer = sim.add_actor("KillActor", "kill_outer")
    # kill_actor_outer.attached_to = "pinboard_outer"


def build_crystal(sim, head, prj_name):
    world = sim.world
    gcm3 = gate.g4_units.g_cm3
    sim.volume_manager.material_database.add_material_weights(
        "CsI",
        ["Cs", "I"],
        [1, 1],
        4.51 * gcm3,
    )

    mm = gate.g4_units.mm

    head_crystal = sim.add_volume("Box", "head_crystal")
    head_crystal.mother = head
    head_crystal.size = [160 * mm, 8 * mm, 160 * mm]
    head_crystal.material = "CsI"
    head_crystal.translation = [0, 69.5 * mm, 0]
    head_crystal.color = [0, 0, 1, 1]
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.attributes = [
        "TotalEnergyDeposit",
        "KineticEnergy",
        "PostPosition",
        "TrackCreatorProcess",
        "GlobalTime",
        "TrackVolumeName",
        "RunID",
        "ThreadID",
        "TrackID",
        "PreStepUniqueVolumeID",
    ]
    hc.attached_to = ["head_crystal"]
    sc = sim.add_actor("DigitizerAdderActor", "Singles")
    sc.input_digi_collection = "Hits"
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.group_volume = "head_crystal"
    proj = sim.add_actor("DigitizerProjectionActor", "Projection")
    proj.attached_to = "head_crystal"
    proj.input_digi_collections = ["Singles"]
    proj.spacing = [1.5 * mm, 1.5 * mm]
    proj.size = [100, 100]
    proj.origin_as_image_center = False
    proj.output_filename = f"{prj_name}.mhd"
    proj.detector_orientation_matrix = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])


def build_geometry(
    sim, prj_name, pin_radius_up=3.6, pin_radius_down=13.6, head_y_pos=100
):
    # head_y_pos is the distance between center of the collimator and the system center in y direction
    mm = gate.g4_units.mm
    world = sim.world
    world.size = [500 * mm, 1000 * mm, 500 * mm]
    world.color = [1, 1, 1, 0.05]

    head = sim.add_volume("Box", "head")
    head.mother = world
    head.size = [500 * mm, 147 * mm, 500 * mm]
    head.material = "G4_AIR"
    head.translation = [0, (73.5 + head_y_pos - 14) * mm, 0]
    head.color = [0, 1, 0, 0.05]

    build_collimator(sim, head, pin_radius_up, pin_radius_down)
    build_crystal(sim, head, prj_name)


def calculate_profile(image_path):
    import SimpleITK as sitk

    image = sitk.ReadImage(image_path)
    array = sitk.GetArrayFromImage(image)
    profile = np.sum(array, axis=(0, 1))
    return profile


def compare_profiles(ref, test, tolerance=8.0, fig_name=None):
    ref = np.asarray(ref, dtype=float)
    test = np.asarray(test, dtype=float)

    if ref.shape != test.shape:
        utility.print_test(False, f"Profile shapes differ: {ref.shape} vs {test.shape}")
        return False

    sad = np.abs(ref - test).sum() / (ref.sum() + test.sum()) * 100
    is_ok = sad < tolerance
    utility.print_test(
        is_ok, f"Profile relative SAD = {sad:.2f}% (tol {tolerance:.2f}%)"
    )

    if fig_name is not None:
        plt.figure(figsize=(10, 5))
        plt.plot(ref / ref.sum(), label="reference")
        plt.plot(test / test.sum(), label="test")
        plt.legend()
        plt.xlabel("Pixel")
        plt.ylabel("Normalized counts")
        plt.savefig(fig_name)

    return is_ok
