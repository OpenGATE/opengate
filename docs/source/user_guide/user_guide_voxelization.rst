.. _voxelization:

***************************************
Details: Volume and source voxelization
***************************************

Voxelization refers to converting Geant4 volumes, composed of analytical shapes such as boxes, spheres, and cylinders, into a 3D image represented as a matrix of voxels. Although particle tracking is generally slower in voxelized volumes (images), voxelization is valuable in several scenarios, such as computing the attenuation map of volumes for image reconstruction.

The example `test015_iec_phantom_voxelize_5` illustrates the different steps with complete voxelization of the NEMA IEC 6 spheres phantom.

From volumes to voxels
----------------------

To voxelize a specified volume, including all its sub-volumes, use the function call `voxelize_geometry`. This function requires as input a simulation object that contains the volumes to be voxelized. The second parameter, `extent`, defines the sub-portion of the scene to be voxelized. By default, it is set to `auto`, in which case GATE automatically determines the sub-portion to include all volumes within the simulation. Alternatively, `extent` can be specified as either a tuple of two 3-vectors indicating the diagonally opposite corners of a box-shaped sub-portion of the geometry to be extracted, or as a volume or list of volumes. In the latter scenario, the box is automatically adjusted to encompass the specified volume(s). The third parameter is `spacing`, which defines the resolution of the output image in millimeters. Additionally, an optional parameter `margin` can be set to add extra padding (in pixels) around the extracted box-shaped sub-portion specified by `extent`.

This algorithm creates an empty image corresponding to the defined `extent`, iterates over all the voxels within this image, and checks which volume is located at the center of each voxel within the simulation scene. For each distinct volume encountered, a label (an integer) is assigned to the voxel. The correspondence between each label and its associated volume along with its material is recorded.


.. code:: python

    # voxelize
    volume_labels, image = voxelize_geometry(sim, extent=my_phantom, spacing=(3*mm, 3*mm, 3*mm, margin=1)

    # write all output
    filenames = write_voxelized_geometry(sim, volume_labels, image, "voxelized_scene.mhd")


The output of `voxelize_geometry` is an image in ITK format and `volume_labels`, a dictionary structure that describes the correspondence between image voxel values (or labels), the volume name in the scene, and the corresponding material. The second helper function, named `write_voxelized_geometry`, will write all necessary files for subsequent reading and usage of the voxelized image as a volume in GATE (see the next section). There are four different written files:

- `volume_labels`: A JSON file containing label, volume names, and material correspondence.
- `image`: The voxelized image in MHD file format.
- `labels`: A list of labels with material correspondence (3 values
- `material_database`: A list of all materials used.

The `filenames` parameter will contain the automatically generated filenames for these four elements (alternatively, the user can set their own filenames).

From voxelization to ImageVolumes
---------------------------------

Once created, the image can be used in a simulation just like any other `ImageVolume` object. The previously written files are used to retrieve the correspondence between voxels and materials.

.. code:: python

    sim.volume_manager.add_material_database("voxelized_materials.db")
    vox = sim.add_volume("ImageVolume", "my_vox")
    vox.image = "voxelized_image.mhd"
    vox.read_label_to_material("voxelized_labels.json")

Here, the three files "voxelized_materials.db",  "voxelized_image.mhd" and "voxelized_labels.json" are the ones stored in the previous section.


From activity source to voxelized source
----------------------------------------

We also provide a convenient function for creating a voxelized source. This function requires the following inputs:
- An image
- A dictionary that describes the correspondence between labels and volumes (like in previous version)
- A dictionary that maps volumes to activity values

The function generates an image in which each voxel is assigned an activity value.

.. code:: python

    activities = {
        "volume1": 1,
        "volume2": 2,
    }
    img = itk.imread("voxelized_image.mhd")
    volume_labels = json.loads(open("voxelized_volumes_labels.json").read())
    img_source = voxelized_source(img, volume_labels, activities)
    itk.imwrite(img_source, "voxelized_source.mhd")


Complete example with the NEAM IEC volume + command line
--------------------------------------------------------


The example `test015_iec_phantom_voxelize_5` demonstrates the complete voxelization process of the NEMA IEC 6-sphere phantom. Additionally, a specific command line facilitates generating various versions of the IEC phantom, as shown below:


.. code:: bash

    voxelize_iec_phantom --spacing 1 -a 1 2 3 4 5 6.6 --bg 0.1 --cyl 0.5  --no_shell -o iec_1mm.mhd --output_source iec_1mm_activity.mha

This command will generate a voxelized version of the IEC phantom with a resolution of 1mm, saved in the `iec_1mm.mhd` file. Additionally, three other files related to volumes, labels, and material properties will be generated. In this example, a voxelized source of activity is also stored, with specified activities in the six spheres (1, 2, 3, 4, 5, and 6.6), background (0.1), and the central cylinder (0.5). The specified activities will then be normalized when used as a voxel source.
