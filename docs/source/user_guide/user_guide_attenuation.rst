.. sectnum::

.. _attenuation:

Computing attenuation image
===========================

An attenuation map image can be generated from a voxelized volume and its associated materials using the `AttenuationImageActor`. The example below illustrates how to insert an image as a Geant4 volume and establish a correspondence between pixels and materials. Using this image, the actor creates an attenuation image that matches the dimensions of the `ImageVolume`, where each pixel is replaced by the linear attenuation coefficient of the respective material. This coefficient, referred to as mu, is derived from the NIST or EPDL database for a specified energy.

.. code:: python

        # image
        patient = sim.add_volume("Image", "patient")
        patient.image = paths.data / "patient-4mm.mhd"
        patient.material = "G4_AIR"  # material used by default
        patient.voxel_materials = [
            [-2000, -900, "G4_AIR"],
            [-900, -100, "Lung"],
            [-100, 0, "G4_ADIPOSE_TISSUE_ICRP"],
            [0, 300, "G4_TISSUE_SOFT_ICRP"],
            [300, 800, "G4_B-100_BONE"],
            [800, 6000, "G4_BONE_COMPACT_ICRU"],
        ]

        # mu map actor (process at the first begin of run only)
        mumap = sim.add_actor("AttenuationImageActor", "mumap")
        mumap.image_volume = patient  # FIXME volume for the moment, not the name
        mumap.output_filename = "mumap.mhd"
        mumap.energy = 140.511 * keV
        mumap.database = "NIST"  # EPDL
        mumap.attenuation_image.write_to_disk = True
        mumap.attenuation_image.active = True


Upon running the simulation, the "mumap.mhd" file is generated and written to disk.


There is a corresponding command line tools:

.. code:: bash

    opengate_photon_attenuation_image -i my_image.mhd -l labels.json --mdb materials.db -o mumap.mhd


The inputs of the command line are: 1) the image, 2) the label to material correspondance, 3) a database of material.
