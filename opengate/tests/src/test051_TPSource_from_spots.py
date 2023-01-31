import opengate as gate
import itk
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation

## ------ INITIALIZE SIMULATION ENVIRONMENT ---------- ##
paths = gate.get_default_test_paths(__file__, "gate_test044_pbs")
output_path = paths.output / "output_test051"
# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_seed = 123654789
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

# waterbox
phantom = sim.add_volume("Box", "phantom")
phantom.size = [20 * cm, 20 * cm, 100.2 * cm]
phantom.translation = [0.0, 0.0, 50.1 * cm]  # at isocenter
phantom.material = "G4_AIR"
phantom.color = [0, 0, 1, 1]

# Planes
m = Rotation.identity().as_matrix()

plane = sim.add_volume("Box", "plane")
plane.mother = "phantom"
plane.size = [200 * mm, 200 * mm, 2 * mm]
plane.translation = [0 * mm, 0 * mm, -50 * mm]
plane.rotation = m
plane.material = "G4_AIR"
plane.color = [1, 0, 1, 1]

# physics
p = sim.get_physics_user_info()
p.physics_list_name = "FTFP_INCLXX_EMZ"
sim.set_cut("world", "all", 1000 * km)

# add dose actor
dose = sim.add_actor("DoseActor", "doseInXZ")
dose.output = output_path / "plane.mhd"
dose.mother = plane.name
dose.size = [400, 400, 1]
dose.spacing = [0.5, 0.5, 2.0]
dose.hit_type = "random"

## ---------- DEFINE BEAMLINE MODEL -------------##
IR2HBL = gate.BeamlineModel()
IR2HBL.Name = None
IR2HBL.RadiationTypes = "ion 6 12"
# Nozzle entrance to Isocenter distance
IR2HBL.NozzleToIsoDist = 1300 * mm
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

nSim = 20000  # particles to simulate per beam
tps = gate.TreatmentPlanSource(nSim, sim, IR2HBL)
# create some spots
spot1 = gate.spot_info(0, 0, 3000, 300)
spot1.beamFraction = 1 / 8
spot1.ion = "ion 6 12"
spot2 = gate.spot_info(50, -50, 12000, 360)
spot2.beamFraction = 3 / 8
spot2.ion = "ion 6 12"
spot3 = gate.spot_info(-25, 50, 6000, 300)
spot3.beamFraction = 2 / 8
spot3.ion = "ion 6 12"
spot4 = gate.spot_info(50, -25, 1000, 300)
spot4.beamFraction = 1 / 8
spot4.ion = "ion 6 12"
tps.spots = [spot1, spot2, spot3, spot4]
# tps.rotation = Rotation.from_euler('y', 90, degrees = True)
tps.translation = [0, 0, 0]
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

# some plots
img_mhd = itk.imread(dose.output)
data = itk.GetArrayViewFromImage(img_mhd)
shape = data.shape
# # 2D
# for i in range(1, shape[0], shape[0] // 3):
#     print(f"Slab Nr. {i}")
#     gate.plot2D(data[i, :, :], "2D Edep", show=True)

# 1D
fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
# gate.plot_img_axis(ax, img_mhd, "z profile", axis="z")
gate.plot_img_axis(ax, img_mhd, "x profile", axis="x")
gate.plot_img_axis(ax, img_mhd, "y profile", axis="y")
plt.show()

EdepColorMap = gate.create_2D_Edep_colorMap(output_path / "plane.mhd")
img_name = "Edep.png"
EdepColorMap.savefig(output_path / img_name)
plt.close(EdepColorMap)
