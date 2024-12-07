#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate


def create_photon_attenuation_image(
    image_filename,
    labels_filename,
    energy,
    material_database=None,
    database="NIST",
    verbose=False,
):

    # create a temporary simulation
    sim = gate.Simulation()
    sim.verbose_level = gate.logger.NONE

    # add the voxelized image
    image_volume = sim.add_volume("Image", "image")
    image_volume.image = image_filename
    image_volume.material = "G4_AIR"

    # labels
    image_volume.read_label_to_material(labels_filename)

    # material
    if material_database is not None:
        sim.volume_manager.add_material_database(material_database)

    # mu map actor (process at the first begin of run only)
    mumap = sim.add_actor("AttenuationImageActor", "mumap")
    mumap.image_volume = image_volume
    mumap.energy = energy * gate.g4_units.MeV
    mumap.database = database
    mumap.write_to_disk = False
    verbose and print(f"Energy is {mumap.energy/gate.g4_units.keV} keV")
    verbose and print(f"Database is {mumap.database}")

    # go
    verbose and print("Starting computing mu ...")
    sim.run(start_new_process=True)

    # retrieve the created image
    im = mumap.attenuation_image.merged_data.image
    return im
