# Gammex 467 phantom

import opengate as gate

import math

cm = gate.g4_units.cm
gcm3 = gate.g4_units.g_cm3

yellow = [1.0, 1.0, 0.0, 1.0]
red = [1.0, 0.0, 0.0, 1.0]


def add_insert(
    sim, mother, name, translation, material, rmin=0.0 * cm, rmax=1.4 * cm, dz=5.0 * cm
):
    insert = sim.add_volume("Tubs", f"{mother.name}_{name}")
    insert.mother = mother.name
    insert.rmin = rmin
    insert.rmax = rmax
    insert.dz = dz
    insert.translation = translation
    insert.material = material
    insert.color = red


def add_inserts(sim, mother, starting_angle, distance, materials, basename):
    ninserts = len(materials)
    dangle = math.radians(360.0 / ninserts)
    angle = math.radians(starting_angle)
    idx = 1
    while idx <= ninserts:
        add_insert(
            sim,
            mother,
            f"{basename}_{idx}",
            [
                math.cos(angle) * distance * cm,
                math.sin(angle) * distance * cm,
                0.0 * cm,
            ],
            materials[idx - 1],
        )
        angle += dangle
        idx += 1


def add_gammex467_phantom(sim, name="gammex467"):
    """
    Add a Gammex 467 phantom to the simulation.
    """

    phantom = sim.add_volume("Tubs", name)
    phantom.rmin = 0.0 * cm
    phantom.rmax = 16.5 * cm
    phantom.dz = 5.0 * cm
    phantom.material = "G4_WATER"
    phantom.color = yellow

    materials = ["H", "C", "N", "O", "Mg", "Si", "P", "Cl", "Ca"]
    sim.volume_manager.material_database.add_material_weights(
        "LN300",
        materials,
        [0.0846, 0.5938, 0.0196, 0.1814, 0.1119, 0.0078, 0.00, 0.0010, 0.00],
        0.3 * gcm3,
    )
    sim.volume_manager.material_database.add_material_weights(
        "LN450",
        materials,
        [0.0847, 0.5957, 0.0197, 0.1811, 0.1121, 0.0058, 0.00, 0.0010, 0.00],
        0.45 * gcm3,
    )
    sim.volume_manager.material_database.add_material_weights(
        "AP6",
        materials,
        [0.0906, 0.7230, 0.0225, 0.1627, 0.00, 0.00, 0.00, 0.0013, 0.00],
        0.94 * gcm3,
    )
    sim.volume_manager.material_database.add_material_weights(
        "BR12",
        materials,
        [0.0859, 0.7011, 0.0233, 0.1790, 0.00, 0.00, 0.00, 0.0013, 0.0095],
        0.98 * gcm3,
    )
    sim.volume_manager.material_database.add_material_weights(
        "Water_Solid",
        materials,
        [0.0800, 0.6730, 0.0239, 0.1987, 0.00, 0.00, 0.00, 0.0014, 0.0231],
        1.02 * gcm3,
    )
    sim.volume_manager.material_database.add_material_weights(
        "BRN-SR2",
        materials,
        [0.1083, 0.7254, 0.0169, 0.1486, 0.00, 0.00, 0.00, 0.0008, 0.00],
        1.05 * gcm3,
    )
    sim.volume_manager.material_database.add_material_weights(
        "LV1",
        materials,
        [0.0806, 0.6701, 0.0247, 0.2001, 0.00, 0.00, 0.00, 0.0014, 0.0231],
        1.1 * gcm3,
    )
    sim.volume_manager.material_database.add_material_weights(
        "IB3",
        materials,
        [0.0667, 0.5564, 0.0196, 0.2352, 0.00, 0.00, 0.0323, 0.0011, 0.0886],
        1.14 * gcm3,
    )
    sim.volume_manager.material_database.add_material_weights(
        "B200",
        materials,
        [0.0668, 0.5348, 0.0212, 0.2561, 0.00, 0.00, 0.00, 0.0011, 0.1201],
        1.15 * gcm3,
    )
    sim.volume_manager.material_database.add_material_weights(
        "CB2_30",
        materials,
        [0.0668, 0.5348, 0.0212, 0.2561, 0.00, 0.00, 0.00, 0.0011, 0.1201],
        1.34 * gcm3,
    )
    sim.volume_manager.material_database.add_material_weights(
        "CB2_50",
        materials,
        [0.0477, 0.4163, 0.0152, 0.3200, 0.00, 0.00, 0.00, 0.0008, 0.2002],
        1.56 * gcm3,
    )
    sim.volume_manager.material_database.add_material_weights(
        "SB3",
        materials,
        [0.0341, 0.3141, 0.0184, 0.3650, 0.00, 0.00, 0.00, 0.0004, 0.2681],
        1.82 * gcm3,
    )

    add_inserts(
        sim,
        phantom,
        67.5,
        10.82390837,
        [
            "LN450",
            "LN300",
            "B200",
            "AP6",
            "LV1",
            "IB3",
            "Water_Solid",
            "CB2_30",
        ],
        "insert_out",
    )

    add_inserts(
        sim,
        phantom,
        90.0,
        5.0,
        ["BR12", "CB2_50", "LN300", "Water_Solid", "BRN-SR2", "LV1", "AP6", "SB3"],
        "insert_in",
    )

    return phantom
