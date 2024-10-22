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

    # lung box
    lung_box = sim.add_volume("Box", "lung_box")
    lung_box.mother = waterbox.name
    lung_box.size = [30 * cm, 30 * cm, 3 * cm]
    lung_box.translation = [0 * cm, 0 * cm, -7 * cm]
    lung_box.material = "G4_LUNG_ICRP"
    lung_box.color = [0, 1, 1, 1]

    # bone box
    bone_box = sim.add_volume("Box", "bone_box")
    bone_box.mother = waterbox.name
    bone_box.size = [30 * cm, 30 * cm, 1 * cm]
    bone_box.translation = [0 * cm, 0 * cm, 0 * cm]
    bone_box.material = "G4_BONE_CORTICAL_ICRP"
    bone_box.color = [1, 0, 0, 1]

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
