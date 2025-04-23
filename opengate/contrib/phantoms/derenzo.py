### Derenzo phantom with 6 sets of cylinders of different size for each set
### For tubs1 set of cylinders each cylinder is assigned with an activity value
### The same procedure as in tubs1 with the activity can be followed to all phantom sets

import opengate as gate
from scipy.spatial.transform import Rotation as R

# Define the units used in the simulation set-up
cm = gate.g4_units.cm
keV = gate.g4_units.keV
mm = gate.g4_units.mm


def add_derenzo_phantom(sim, name="derenzo"):
    """
    Add a Derenzo phantom with 6 sets of cylinders of different size for each set.
    The phantom is described in https://doi.org/10.3390/diagnostics15111387
    """
    phantom_body = sim.add_volume("Box", name)
    phantom_body.size = [30 * cm, 30 * cm, 5 * cm]
    phantom_body.mother = "world"
    phantom_body.material = "G4_AIR"
    rot = R.from_euler("x", [-90], degrees=True)
    phantom_body.rotation = rot.as_matrix()
    yellow = [1, 1, 0, 0.5]

    tubs_1 = sim.add_volume("Tubs", f"{phantom_body.name}_tubs_1")
    tubs_1.material = "G4_WATER"
    tubs_1.mother = phantom_body.name
    tubs_1.rmin = 0 * mm
    tubs_1.rmax = 14.5 * mm
    tubs_1.dz = 12 * mm
    tubs_1.color = yellow
    tubs_1.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    tubs_1.translation = [
        [29 * mm, 105 * mm, 0],
        [-29 * mm, 105 * mm, 0],
        [0 * mm, 54.77 * mm, 0],
    ]

    tubs_2 = sim.add_volume("Tubs", f"{phantom_body.name}_tubs_2")
    tubs_2.material = "G4_WATER"
    tubs_2.mother = phantom_body.name
    tubs_2.rmin = 0 * mm
    tubs_2.rmax = 9.3 * mm
    tubs_2.dz = 12 * mm
    tubs_2.color = yellow
    tubs_2.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    tubs_2.translation = [
        [66 * mm, 25 * mm, 0],
        [66 * mm, 89.44 * mm, 0],
        [28.8 * mm, 25 * mm, 0],
        [103.2 * mm, 25 * mm, 0],
        [84.5 * mm, 57.21 * mm, 0],
        [47.5 * mm, 57.21 * mm, 0],
    ]

    tubs_3 = sim.add_volume("Tubs", f"{phantom_body.name}_tubs_3")
    tubs_3.material = "G4_WATER"
    tubs_3.mother = phantom_body.name
    tubs_3.rmin = 0 * mm
    tubs_3.rmax = 7.85 * mm
    tubs_3.dz = 12 * mm
    tubs_3.color = yellow
    tubs_3.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    tubs_3.translation = [
        [66 * mm, -45.19 * mm, 0],
        [97.4 * mm, -45.19 * mm, 0],
        [34.6 * mm, -45.19 * mm, 0],
        [18.9 * mm, -18 * mm, 0],
        [50.3 * mm, -18 * mm, 0],
        [81.7 * mm, -18 * mm, 0],
        [113.1 * mm, -18 * mm, 0],
        [50.3 * mm, -72.38 * mm, 0],
        [81.7 * mm, -72.38 * mm, 0],
        [66 * mm, -99.57 * mm, 0],
    ]

    tubs_4 = sim.add_volume("Tubs", f"{phantom_body.name}_tubs_4")
    tubs_4.material = "G4_WATER"
    tubs_4.mother = phantom_body.name
    tubs_4.rmin = 0 * mm
    tubs_4.rmax = 6.5 * mm
    tubs_4.dz = 12 * mm
    tubs_4.color = yellow
    tubs_4.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    tubs_4.translation = [
        [0 * mm, -91.69 * mm, 0],
        [0 * mm, -46.67 * mm, 0],
        [26 * mm, -91.69 * mm, 0],
        [-26 * mm, -91.69 * mm, 0],
        [-13 * mm, -69.18 * mm, 0],
        [13 * mm, -69.18 * mm, 0],
        [13 * mm, -114.2 * mm, 0],
        [-13 * mm, -114.2 * mm, 0],
        [-39 * mm, -114.2 * mm, 0],
        [39 * mm, -114.2 * mm, 0],
    ]

    tubs_5 = sim.add_volume("Tubs", f"{phantom_body.name}_tubs_5")
    tubs_5.material = "G4_WATER"
    tubs_5.mother = phantom_body.name
    tubs_5.rmin = 0 * mm
    tubs_5.rmax = 5.75 * mm
    tubs_5.dz = 12 * mm
    tubs_5.color = yellow
    tubs_5.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    tubs_5.translation = [
        [-66 * mm, -42.92 * mm, 0],
        [-89 * mm, -42.92 * mm, 0],
        [-43 * mm, -42.92 * mm, 0],
        [-66 * mm, -82.76 * mm, 0],
        [-54.5 * mm, -62.84 * mm, 0],
        [-77.5 * mm, -62.84 * mm, 0],
        [-54.5 * mm, -23 * mm, 0],
        [-77.5 * mm, -23 * mm, 0],
        [-31.5 * mm, -23 * mm, 0],
        [-100.5 * mm, -23 * mm, 0],
    ]

    tubs_6 = sim.add_volume("Tubs", f"{phantom_body.name}_tubs_6")
    tubs_6.material = "G4_WATER"
    tubs_6.mother = phantom_body.name
    tubs_6.rmin = 0 * mm
    tubs_6.rmax = 5 * mm
    tubs_6.dz = 12 * mm
    tubs_6.color = yellow
    tubs_6.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    tubs_6.translation = [
        [-66 * mm, 17 * mm, 0],
        [-46 * mm, 17 * mm, 0],
        [-26 * mm, 17 * mm, 0],
        [-86 * mm, 17 * mm, 0],
        [-106 * mm, 17 * mm, 0],
        [-56 * mm, 34.32 * mm, 0],
        [-36 * mm, 34.32 * mm, 0],
        [-76 * mm, 34.32 * mm, 0],
        [-96 * mm, 34.32 * mm, 0],
        [-66 * mm, 51.64 * mm, 0],
        [-46 * mm, 51.64 * mm, 0],
        [-86 * mm, 51.64 * mm, 0],
        [-76 * mm, 68.96 * mm, 0],
        [-56 * mm, 68.96 * mm, 0],
        [-66 * mm, 86.28 * mm, 0],
    ]
    return phantom_body


def add_sources(sim, derenzo_phantom, activity_Bq_mL):
    """
    The source is attached to the tubs volumes of the derenzo,
    it means its coordinate system is the same
    activity_Bq_mL should contain the activity concentration for each set of tubs (6)
    """

    sources = []
    for nb_tub in range(1, 7):
        tubs = sim.volume_manager.volumes[f"{derenzo_phantom.name}_tubs_{nb_tub}"]
        for i in range(len(tubs.translation)):
            tub_name = tubs.get_repetition_name_from_index(i)
            s = tubs.solid_info
            source = sim.add_source(
                "GenericSource", f"{derenzo_phantom.name}_tubs_{nb_tub}_source_{i}"
            )
            source.attached_to = tub_name
            source.particle = "gamma"
            source.energy.mono = 140 * keV
            source.activity = activity_Bq_mL[nb_tub - 1] * s.cubic_volume
            source.position.type = "cylinder"
            source.position.radius = tubs.rmax
            source.position.dz = tubs.dz
            source.direction.type = "iso"
            sources.append(source)

    return sources
