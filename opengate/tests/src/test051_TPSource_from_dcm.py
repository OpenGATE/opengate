import opengate as gate
import itk
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation

## ------ INITIALIZE SIMULATION ENVIRONMENT ---------- ##
paths = gate.get_default_test_paths(__file__, "gate_test044_pbs")
output_path = paths.output / "output_test051_rtp"
ref_path = paths.output_ref / "test051_ref"


# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_seed = 12365478910
ui.random_engine = "MersenneTwister"

# units
km = gate.g4_units("km")
cm = gate.g4_units("cm")
mm = gate.g4_units("mm")
um = gate.g4_units("um")
MeV = gate.g4_units("MeV")
Bq = gate.g4_units("Bq")
nm = gate.g4_units("nm")
deg = gate.g4_units("deg")
rad = gate.g4_units("rad")

# add a material database
sim.add_material_database(paths.gate_data / "HFMaterials2014.db")

#  change world size
world = sim.world
world.size = [600 * cm, 500 * cm, 500 * cm]

# nozzle box
box = sim.add_volume("Box", "box")
box.size = [500 * mm, 500 * mm, 1000 * mm]
box.translation = [1148 * mm, 0.0, 0.0]
box.rotation = Rotation.from_euler("y", -90, degrees=True).as_matrix()
box.material = "G4_AIR"  # "Vacuum"
box.color = [0, 0, 1, 1]

# nozzle WET
nozzle = sim.add_volume("Box", "nozzle")
nozzle.mother = box.name
nozzle.size = [500 * mm, 500 * mm, 2 * mm]
nozzle.material = "G4_WATER"

# target
phantom = sim.add_volume("Box", "phantom")
phantom.size = [600 * mm, 310 * mm, 310 * mm]
phantom.translation = [300 * mm, 0.0, 0.0]
phantom.material = "G4_AIR"
phantom.color = [0, 0, 1, 1]

# physics
p = sim.get_physics_user_info()
p.physics_list_name = "FTFP_INCLXX_EMZ"
sim.set_cut("world", "all", 1000 * km)

# add dose actor
dose = sim.add_actor("DoseActor", "doseInXYZ")
dose.output = paths.output / "testTPSxyz.mhd"
dose.mother = phantom.name
dose.size = [300, 620, 620]
dose.spacing = [2.0, 0.5, 0.5]
dose.hit_type = "random"
dose.gray = True

dose1 = sim.add_actor("DoseActor", "doseInYZ")
dose1.output = paths.output / "testTPSnozzle.mhd"
dose1.mother = nozzle.name
dose1.size = [250, 250, 1]
dose1.spacing = [2.0, 2.0, 2.0]
dose1.hit_type = "random"

## ---------- DEFINE BEAMLINE MODEL -------------##
IR2HBL = gate.BeamlineModel()
IR2HBL.Name = None
IR2HBL.RadiationTypes = "ion 6 12"
# Nozzle entrance to Isocenter distance
IR2HBL.NozzleToIsoDist = 1300 * mm  # 1648 * mm#1300 * mm
# SMX to Isocenter distance
IR2HBL.SMXToIso = 6700 * mm
# SMY to Isocenter distance
IR2HBL.SMYToIso = 7420 * mm
# polinomial coefficients
IR2HBL.energyMeanCoeffs = [-6.71618e-9, 1.02304e-5, -4.9270e-3, 1.28461e1, -66.136]
IR2HBL.energySpreadCoeffs = [-1.66295e-9, 1.31502e-6, -2.59769e-4, -2.60088e-3, 7.436]
IR2HBL.sigmaXCoeffs = [
    -1.07268e-13,
    1.61558e-10,
    -9.92211e-8,
    3.19029e-5,
    -5.67757e-3,
    5.29884e-1,
    -17.749,
]
IR2HBL.thetaXCoeffs = [
    -1.13854e-17,
    1.52020e-14,
    -7.49359e-12,
    1.57991e-9,
    -8.98373e-8,
    -1.30862e-5,
    1.638e-3,
]
IR2HBL.epsilonXCoeffs = [
    -2.54669e-16,
    3.71028e-13,
    -2.14188e-10,
    6.21900e-8,
    -9.46711e-6,
    7.09187e-4,
    -19.511e-3,
]
IR2HBL.sigmaYCoeffs = [
    -5.80689e-14,
    9.10249e-11,
    -5.75230e-8,
    1.85977e-5,
    -3.20430e-3,
    2.74490e-1,
    -7.133,
]
IR2HBL.thetaYCoeffs = [
    8.10201e-18,
    -1.75709e-14,
    1.44445e-11,
    -5.82592e-9,
    1.22471e-6,
    -1.28547e-4,
    6.066e-3,
]
IR2HBL.epsilonYCoeffs = [
    -5.74235e-16,
    9.12245e-13,
    -5.88501e-10,
    1.96763e-7,
    -3.58265e-5,
    3.35307e-3,
    -122.935e-3,
]

## --------START PENCIL BEAM SCANNING---------- ##
# NOTE: HBL means that the beam is coming from -x (90 degree rot around y)
rt_plan = ref_path / "RP1.2.752.243.1.1.20230119115736709.2000.75541.dcm"
# rt_plan = ref_path / "RP1.2.752.243.1.1.20220712093231484.2300.41658.dcm"
beamset = gate.beamset_info(rt_plan)
G = float(beamset.beam_angles[0])
nSim = 328935  # particles to simulate per beam
tps = gate.TreatmentPlanSource(nSim, sim, IR2HBL)
tps.beamset = beamset
# tps.mother = 'box'
tps.rotation = Rotation.from_euler("y", G, degrees=True)
tps.G = G
tps.initialize_tpsource()

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "Stats")
s.track_types_flag = True
# start simulation
output = sim.start()

## -------------END SCANNING------------- ##
# print results at the end
stat = output.get_actor("Stats")
print(stat)

# create output dir, if it doesn't exist
if not os.path.isdir(output_path):
    os.mkdir(output_path)

## ------ TESTS -------##
# EDEP
ok = gate.assert_images(
    ref_path / "idc-PHANTOM-air_box-gate_test51_TP_1-PLAN-Physical.mhd",
    dose.output,
    axis="x",
)
# ------------------------------------
# SPOT POSITIONS COMPARISON
# read output and ref
img_mhd_out = itk.imread(str(dose.output).replace(".mhd", "_dose.mhd"))
# img_mhd_out = itk.imread(dose1.output)
img_mhd_ref = itk.imread(
    ref_path / "idc-PHANTOM-air_box-gate_test51_TP_1-PLAN-Physical.mhd"
)
data = itk.GetArrayViewFromImage(img_mhd_out) * beamset.mswtot / nSim
data_ref = itk.GetArrayViewFromImage(img_mhd_ref)
shape = data.shape
spacing = img_mhd_out.GetSpacing()

# spot comparison (N.B x and z are inverted in np array!)
# spots in the plan file
yz = [
    50.0,
    -50.0,
    -50.0,
    -50.0,
    -100.0,
    0.0,
    100,
    0,
    50,
    50,
    0,
    100,
    -100,
    -100,
    0,
    -100,
    100,
    -100,
    0,
    0,
    -50,
    50,
    -100,
    100,
    100,
    100,
]

yzM = np.array(yz).reshape(int(len(yz) / 2), 2)
# convert from mm (wrt image center) to voxel
spot_y = [int(y / dose.spacing[1]) + int(dose.size[1] / 2) for y in yzM[:, 0]]
spot_z = [-int(z / dose.spacing[1]) + int(dose.size[1] / 2) for z in yzM[:, 1]]

thresh = 0.1

# gate.plot2D(data[0, :, :], "2D Edep opengate", show=True)

for i in range(1, shape[2], shape[2] // 3):
    # check i-th slab
    print(f"Air slab nr. {i}")
    gate.plot2D(data[:, :, i], "2D Edep opengate", show=True)
    # gate.plot2D(data_ref[:, :, i], "2D Edep gate", show=True)
    # for y,z in zip(spot_y,spot_z):
    #     print(f'  planned coordinates ({y},{z})')
    #     # 'cut' the slab around the spot expected in y,z
    #     w = 30 # cut window's half size
    #     d_out = data[z-w:z+w, y-w:y+w, i:i+1]
    #     d_ref = data_ref[z-w:z+w, y-w:y+w, i:i+1]
    #     ok = gate.test_tps_spot_positions(d_out, d_ref, spacing) and ok


# 1D
fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
gate.plot_img_axis(ax, img_mhd_out, "z profile", axis="z")
gate.plot_img_axis(ax, img_mhd_out, "x profile", axis="x")
gate.plot_img_axis(ax, img_mhd_out, "y profile", axis="y")
# fig.savefig(output_path / 'dose_profiles.png')
plt.show()

fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
gate.plot_img_axis(ax, img_mhd_ref, "z profile", axis="z")
gate.plot_img_axis(ax, img_mhd_ref, "x profile", axis="x")
gate.plot_img_axis(ax, img_mhd_ref, "y profile", axis="y")
# fig.savefig(output_path / 'dose_profiles.png')
plt.show()
