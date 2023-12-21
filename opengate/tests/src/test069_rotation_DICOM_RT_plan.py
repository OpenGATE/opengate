import opengate as gate
import numpy as np
import itk
import test069_rotation_DICOM_RT_plan_helpers as t
from opengate.tests import utility


def validation_test(theoretical_calculation, MC_calculation, tol=0.08):
    print(
        "Area from theoretical calculation for all CP (mm2): ", theoretical_calculation
    )
    print("Area from MC simulations for all CP: (mm2)", MC_calculation)
    percentage_diff = (
        100 * (theoretical_calculation - MC_calculation) / theoretical_calculation
    )
    bool_percentage_diff = np.abs(percentage_diff) > tol * 100
    if np.sum(bool_percentage_diff) == 0:
        return True
    else:
        return False


def calc_MLC_aperture(
    x_leaf_position, y_jaws, pos_MLC=349.3, pos_jaws=470.5, SAD=1000, leaf_width=1.85
):
    mm = gate.g4_units.mm
    leaf_width = leaf_width * mm
    left = x_leaf_position[:80] * pos_MLC / SAD
    right = x_leaf_position[80:] * pos_MLC / SAD
    left[left != 0] = left[left != 0] - left[left != 0] % 0.5
    right[right != 0] = right[right != 0] + 0.5 - right[right != 0] % 0.5

    pos_Y_leaf = np.arange(
        -leaf_width * 40 + leaf_width / 2,
        leaf_width * 40 - leaf_width / 2 + 0.01,
        leaf_width,
    )
    left[pos_Y_leaf < y_jaws[0] * pos_jaws / SAD] = 0
    left[pos_Y_leaf > y_jaws[1] * pos_jaws / SAD] = 0
    right[pos_Y_leaf < y_jaws[0] * pos_jaws / SAD] = 0
    right[pos_Y_leaf > y_jaws[1] * pos_jaws / SAD] = 0
    diff = np.array(right - left)

    return np.sum(diff) * leaf_width


def add_VolumeToIrradiate(sim, name, rot_volume):
    mm = gate.g4_units.mm
    Box = sim.add_volume("Box", "cylinder")
    Box.material = "G4_WATER"
    Box.mother = name
    Box.size = [400 * mm, 400 * mm, 400 * mm]

    voxel_size_x = 0.5 * mm
    voxel_size_y = 0.5 * mm
    voxel_size_z = 400 * mm

    dim_box = [
        400 * mm / voxel_size_x,
        400 * mm / voxel_size_y,
        400 * mm / voxel_size_z,
    ]
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = "output/testilol.mhd"
    dose.mother = Box.name
    dose.size = [int(dim_box[0]), int(dim_box[1]), int(dim_box[2])]
    dose.spacing = [voxel_size_x, voxel_size_y, voxel_size_z]
    dose.uncertainty = False
    dose.square = False
    dose.hit_type = "random"

    motion_tubs = sim.add_actor("MotionVolumeActor", "Move_Tubs")
    motion_tubs.mother = Box.name
    motion_tubs.rotations = []
    motion_tubs.translations = []
    for i in range(len(rot_volume)):
        motion_tubs.rotations.append(rot_volume[i])
        motion_tubs.translations.append([0, 0, 0])


def add_alpha_source(sim, name, pos_Z, nb_part):
    ui = sim.user_info
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    plan_source = sim.add_volume("Box", "plan_alpha_source")
    plan_source.material = "G4_Galactic"
    plan_source.mother = name
    plan_size = np.array([250 * mm, 148 * mm, 1 * nm])
    plan_source.size = np.copy(plan_size)
    plan_source.translation = [0 * mm, 0 * mm, -pos_Z / 2 + 300 * mm]

    source = sim.add_source("GenericSource", "alpha_source")
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    source.particle = "alpha"
    source.mother = plan_source.name
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV
    source.position.type = "box"
    source.position.size = np.copy(plan_size)
    source.direction.type = "momentum"
    source.force_rotation = True
    source.direction.momentum = [0, 0, -1]
    source.activity = nb_part * Bq / ui.number_of_threads


def launch_simulation(
    nt, path_img, img, file, output_path, output, nb_part, src_f, vis, seg_cp, patient
):
    visu = vis
    km = gate.g4_units.km
    nb_cp = t.liste_CP(file)
    nb_aleatoire = np.random.randint(0, nb_cp - 1, 4)
    print("Control Points ID: ", nb_aleatoire)
    seg_cp += 1
    l_aperture_voxel = np.zeros(len(nb_aleatoire))
    l_aperture_calc = np.zeros(len(nb_aleatoire))
    for i in range(len(nb_aleatoire)):
        cp_param = t.Dataset_DICOM_MLC_jaws(
            file, [nb_aleatoire[i], nb_aleatoire[i] + 1], 0
        )
        mean_leaves = (cp_param["Leaves"][0] + cp_param["Leaves"][1]) / 2
        mean_jaws_1 = (cp_param["Y_jaws_1"][0] + cp_param["Y_jaws_1"][1]) / 2
        mean_jaws_2 = (cp_param["Y_jaws_2"][0] + cp_param["Y_jaws_2"][1]) / 2
        y_jaws = [mean_jaws_1, mean_jaws_2]
        area = calc_MLC_aperture(mean_leaves, y_jaws)
        l_aperture_calc[i] = area
        sim = t.init_simulation(
            nt,
            cp_param,
            path_img,
            img,
            visu,
            src_f,
            bool_phsp=False,
            seg_cp=seg_cp,
            patient=patient,
        )

        ui = sim.user_info
        ui.running_verbose_level = gate.logger.RUN

        linac = sim.volume_manager.volumes["Linac_box"]
        world = sim.volume_manager.volumes["world"]
        linac.material = "G4_Galactic"
        world.material = "G4_Galactic"
        motion_actor = sim.get_actor_user_info("Move_LINAC")
        rotation_volume = motion_actor.rotations
        add_alpha_source(sim, linac.name, linac.size[2], nb_part)
        add_VolumeToIrradiate(sim, world.name, rotation_volume)

        dose_actor = sim.get_actor_user_info("dose")
        dose_actor.output = output_path / output

        ui.visu = visu
        if visu:
            ui.visu_type = "vrml"
        sim.physics_manager.global_production_cuts.gamma = 1 * km
        sim.physics_manager.global_production_cuts.electron = 1 * km
        sim.physics_manager.global_production_cuts.positron = 1 * km
        sec = gate.g4_units.s
        sim.run_timing_intervals = []
        for j in range(len(rotation_volume)):
            sim.run_timing_intervals.append([j * sec, (j + 1) * sec])

        sim.run(start_new_process=True)
        img_MC = itk.imread(output_path / output)
        array_MC = itk.GetArrayFromImage(img_MC)
        bool_MC = array_MC[array_MC != 0]
        l_aperture_voxel[i] = len(bool_MC) / 4
    is_ok = validation_test(l_aperture_calc, l_aperture_voxel)
    utility.test_ok(is_ok)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__)
    output_path = paths.output
    patient = False
    nt = 1
    ###### The three following variables are here to not modify the main program (the helpers) which need it ######
    path_img = "useless"
    img = "useless"
    src_f = "alpha"
    ###############################################################################################################
    output = "img_test_069.mhd"
    nb_part = 750000
    seg_cp = 1
    vis = False
    file = str(paths.data / "DICOM_RT_plan.dcm")
    launch_simulation(
        nt,
        path_img,
        img,
        file,
        output_path,
        output,
        nb_part,
        src_f,
        vis,
        seg_cp,
        patient,
    )
