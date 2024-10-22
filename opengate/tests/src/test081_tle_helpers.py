#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate


def add_waterbox(sim):
    # units
    cm = gate.g4_units.cm

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [30 * cm, 30 * cm, 20 * cm]
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]

    # low density box
    low_density_box = sim.add_volume("Box", "low_density_box")
    low_density_box.mother = waterbox.name
    low_density_box.size = [30 * cm, 30 * cm, 3 * cm]
    low_density_box.translation = [0 * cm, 0 * cm, -6 * cm]
    low_density_box.material = "G4_lPROPANE"  # density is around 0.43
    low_density_box.color = [0, 1, 1, 1]

    # high density box
    high_density_box = sim.add_volume("Box", "high_density_box")
    high_density_box.mother = waterbox.name
    high_density_box.size = [30 * cm, 30 * cm, 1 * cm]
    high_density_box.translation = [0 * cm, 0 * cm, 1 * cm]
    high_density_box.material = "G4_Pyrex_Glass"  # density is around 2.23
    high_density_box.color = [1, 0, 0, 1]

    return waterbox


def voxelize_waterbox(sim, output_folder):
    mm = gate.g4_units.mm
    a = sim.output_dir
    sim.output_dir = output_folder
    sim.voxelize_geometry(
        filename="waterbox_with_inserts_8mm", spacing=(8 * mm, 8 * mm, 8 * mm)
    )
    sim.voxelize_geometry(
        filename="waterbox_with_inserts_5mm", spacing=(5 * mm, 5 * mm, 5 * mm)
    )
    sim.voxelize_geometry(
        filename="waterbox_with_inserts_3mm", spacing=(3 * mm, 3 * mm, 3 * mm)
    )
    sim.voxelize_geometry(
        filename="waterbox_with_inserts_1mm", spacing=(1 * mm, 1 * mm, 1 * mm)
    )
    sim.output_dir = a
