## Volumes

Volumes are the elements that describe solid objects. There is a default volume called `world` (lowercase) automatically created. All volumes can be created with the `add_volume` command. The parameters of the resulting volume can be easily set as follows:

```python
vol = sim.add_volume('Box', 'mybox')
print(vol)  # to display the default parameter values
vol.material = 'G4_AIR'
vol.mother = 'world'  # by default
cm = gate.g4_units('cm')
mm = gate.g4_units('mm')
vol.size = [10 * cm, 5 * cm, 15 * mm]

# print the list of available volumes types:
print('Volume types :', sim.dump_volume_types())
```

The return of `add_volume` is a `UserInfo` object (that can be view as a dict). All volumes must have a material (`G4_AIR` by default) and a mother (`world` by default). Volumes must follow a hierarchy like volumes in Geant4. All volumes have a default list of parameters you can print with `print(vol)`.

Here is a list of available volumes: Box, Sphere, Trap, Image, Tubs, Polyhedra, Cons, Trd, Boolean, RepeatParametrised (this list may not be uptodate). You can find the way Geant4 parametrize the volumes [here](http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html#constructed-solid-geometry-csg-solids).

### Common parameters

Some parameters are specific to one volume type (for example `size` for `Box`, or `radius` for `Sphere`), but all volumes share some common parameters:

- `mother`: the name of the mother volume (`world` by default) in the hierarchy of volume. The volume will consider its coordinates system the one of his mother.
- `material`: the name of the material that compose the volume (`G4_WATER` for example).
- `translation`: the translation (list of 3 values), such as `[0, 2*cm, 3*mm]`, to place the volume according to his coordinate system (the one from his mother). In Geant4, the coordinate system is always according to the center of the shape.
- `rotation`: a 3x3 rotation matrix. We advocate the use of `scipy.spatial.transform` `Rotation` object to manage rotation matrix.
- `repeat`: a list of dictionary of 'name' + 'translation' + 'rotation'. Each element of the list will create a repeated copy of the volume, positionned according to the translation and rotation (see `test017`)
- `color`: a color as a list of 4 values `[1, 0, 0, 0.5]` (Red, Green, Blue, Opacity) between 0 and 1. Only use when visualization is on.

See for example `test007` and `test017` test files for more details.

### Materials

The Geant4 default materials are available. The list is available [here](https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Appendix/materialNames.html).

Additional materials can be created by the user, with a simple text file, like in the previous GATE versions. The text file can be loaded with:

    sim.add_material_database("GateMaterials.db")

After this command, all materials names defined in the "GateMaterials.db" are known and can be used for any volume. The format of the ".db" text file can be seen in the file `tests/data/GateMaterials`.

Alternatively, materials can be created dynamically with the following:

    gate.new_material("mylar", 1.38 * gcm3, ["H", "C", "O"], [0.04196, 0.625016, 0.333024])

This function creates a material named "mylar", with the given mass density and the composition (H C and O here) described as a vector of percentages. Note that the weights are normalized. The created material can then be used for any volume.


### Images (voxelized volumes)

A 3D image can be inserted in the scene with the following command:

```python
patient = sim.add_volume("Image", "patient")
patient.image = "data/myimage.mhd"
patient.mother = "world"
patient.material = "G4_AIR"  # material used by default
patient.voxel_materials = [
  [-2000, -900, "G4_AIR"],
  [-900, -100, "Lung"],
  [-100, 0, "G4_ADIPOSE_TISSUE_ICRP"],
  [0, 300, "G4_TISSUE_SOFT_ICRP"],
  [300, 800, "G4_B-100_BONE"],
  [800, 6000, "G4_BONE_COMPACT_ICRU"],
]
```

The user info named `patient. image` on the second line must be the path to the image filename, that must be readable by itk. In general, we advocate the use of mhd/raw file format, but other file format can be used. The image must be 3D, with any pixel type (float, int, char, etc).

User must describe how the voxels's values will be translated into materials. This is done with the `patient.voxel_materials` parameter that is a simple array of intervals defined by 3 values. The 3 values define an interval to assign a given material, 1) the starting value (included) 2) the ending value (not included) and 3) the material name. For example in the previous code, every voxel value between -900 and -100 will be assigned to the material "Lung". If there are voxel value outside all the intervals, the default material will be used as defined by `patient.material`. See for example the test `t009`.

There is a specific function that can help to automatically create such an array of intervals for conventional Hounsfield Unit of CT images:

```python
gcm3 = gate.g4_units("g/cm3")
f1 = "Schneider2000MaterialsTable.txt"
f2 = "Schneider2000DensitiesTable.txt"
tol = 0.05 * gcm3
patient.voxel_materials, materials = gate.HounsfieldUnit_to_material(tol, f1, f2)
patient.dump_label_image = "labels.mhd"
```

In that case, the `HounsfieldUnit_to_material` function will create the array of intervals. It also creates a list of materials. The input parameters for this function are 1) the density tolerance (in g/cm3), 2) a list of reference material and 3) a list of reference densities. Example of such files can be found in `opengate/tests/data` folder. The option `dump_label_image` is a help and can be used to write the corresponding labeled image (every voxel value is replaced by the material label). See for example the test `t009`.

The coordinate system of such image is like for other Geant4's volumes: by default, the center of the image is positioned at the origin. The embedded origin in the image (like in DICOM or mhd) is *not* considered here. This is the user responsibility to compute the needed translation/rotation.


### Repeated and parameterized volumes



### Boolean volumes
