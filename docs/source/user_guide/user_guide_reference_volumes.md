# Volumes

This section describes the different volumes available in GATE 10 and their parameters.

## Common parameters

Some of the parameters are common to **all** volumes, while others are specific to a certain type of volume. Given a volume `vol`, use `print(vol)` to display the volume's parameters and their default values.

Common parameters are:

- `mother`: the name of the mother volume (`world` by default) in the hierarchy of volumes. Volumes are always positioned with respect to the reference frame of the mother volume and therefore moves with the mother volume.
- `material`: the name of the material that composes the volume, e.g. `G4_WATER`. See section [Materials](#materials)
- `translation`: list of 3 numerical values, e.g. `[0, 2*cm, 3*mm]`. It defines the translation of the volume with respect to the reference frame of the mother volume. Note: the origin of the reference frame is always at the center of the shape in Geant4.
- `rotation`: a 3x3 rotation matrix. Rotation of the volume with respect to the mother volume. We advocate the use of `scipy.spatial.transform.Rotation` to manage the rotation matrix.
- `color`: a list of 4 values (Red, Green, Blue, Opacity) between 0 and 1, e.g. `[1, 0, 0, 0.5]`. Only used when visualization is on.

## Image volume

### Description

An image volumes is essentially a box filled with a voxelized volumetric (3D) image. The box containing the image behaves pretty much like a `BoxVolume` and its size is automatically adjusted to match the size of the input image. The image should be provided in a format readable by the *itk* package and the path to the image file is set via the parameter `image`. In general, we advocate the use of the mhd/raw file format, but other itk-compatible file formats can be used as well. The image must be 3D, with any pixel type (float, int, char, etc.).

From the simulation point of view, a voxel is like a small box through which particles need to be transported. Therefore, in order for Gate/Geant4 to make use of the image, the image values need to be mapped to materials to be associated with the corresponding voxel. To this end, you need to provide a lookup table via the parameter `voxel_materials`, which is a list of 3-item-lists, each defining a value range (half-closed interval) and the material name to be used. Take the following example:


```python
import opengate as gate
sim = gate.Simulation()
patient = sim.add_volume("Image", name="patient")
patient.image = "data/myimage.mhd"
patient.mother = "world"
patient.material = "G4_AIR"  # material used by default
patient.voxel_materials = [
  # range format [)
  [-2000, -900, "G4_AIR"],
  [-900, -100, "Lung"],
  [-100, 0, "G4_ADIPOSE_TISSUE_ICRP"],
  [0, 300, "G4_TISSUE_SOFT_ICRP"],
  [300, 800, "G4_B-100_BONE"],
  [800, 6000, "G4_BONE_COMPACT_ICRU"],
]
patient.dump_label_image = "labels.mhd"
```

In the example above, the material "Lung" will be assigned to every voxel with a value between -900 and -100 (not including -100). Voxels whose value does not fall into any of the intervals are considered to contain the volume's default material, i.e. `patient.material = "G4_AIR"` in the example above. If a path is provided as `dump_label_image` parameter of the image volume, an image will be written to the provided path containing material labels. Label 0 stands for voxels to which the default material was assigned, and labels greater than 1 represent all other materials, in ascending order of the lower interval bounds provided in `voxel_materials`. In the example above, voxels with label 3 correspond to "G4_ADIPOSE_TISSUE_ICRP", voxels with label 4 correspond to "G4_TISSUE_SOFT_ICRP", and so forth. See test `test009` as an example simulation using an Image volume.

The frame of reference of an Image is linked to the bounding box and treated like other Geant4 volumes, i.e. by default, the center of the image box is positioned at the origin of the mother volume's frame of reference. Important: Currently, the origin provided by the input image (e.g. in the DICOM or mhd file) is ignored. If you want to place the Image volume according to the origin and rotation provided by the input image, you need to extract that information and set it via the `translation` and `rotation` parameters of the image volume. A future version of Gate 10 might provide an option to do this automatically. If you are motivated, you can implement that feature and contribute it to the opengate package.

There is a helper function `HounsfieldUnit_to_material` to create an interval-material list that can be used as input to the `voxel_materials` parameter, specifically for CT images expressed in Hounsfield Units:

```python
import opengate as gate
sim = gate.Simulation()
gcm3 = gate.g4_units.g_cm3
f1 = "PATH_TO_OPENGATE/tests/data/Schneider2000MaterialsTable.txt"
f2 = "PATH_TO_OPENGATE/tests/data/Schneider2000DensitiesTable.txt"
tol = 0.05 * gcm3
voxel_materials, materials = gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)
```

The function `HounsfieldUnit_to_material` returns two objects:
1) A list of intervals and material names which can be used as parameter `voxel_materials`
2) A list of materials for other use

The input parameters of the function `HounsfieldUnit_to_material` are
1) An existing simulation (here `sim`)
2) The density tolerance (in g/cm3)
3) The path to a file containing a list of reference *materials*
4) The path to a file containing a list of reference *densities*

Examples of such files can be found in the `opengate/tests/data` folder. See test `test009` as example.

### Reference
```{eval-rst}
.. autoclass:: opengate.geometry.volumes.ImageVolume
```

## Tesselated (STL) volumes

### Description

It is possible to create a tesselated volume shape based on an Standard Triangle Language (STL) data file. Such a file contains a mesh of triangles for one object. It is a typical output format of Computer Aided Design (CAD) software.
To create such a volume add a volume of type "Tesselated". Please keep in mind, that no material information is provided, it has to be specified by the user. A Tesselated volume inherits the the same basic options as other solids described above such as translation or rotation. A basic example how to import an STL file into a geometry "MyTesselatedVolume" and assign the material G4_WATER to it can be found below. In order to verify the correct generation of the solid, one could look at the volume.


```python
import opengate as gate
sim = gate.Simulation()
tes = sim.add_volume("Tesselated", name="MyTesselatedVolume")
tes.material = "G4_WATER"
tes.mother = "world"  # by default
tes.file_name = "myTesselatedVolume.stl"
#to read the volume of the generated solid
print("volume: ",sim.volume_manager.get_volume(
        "MyTesselatedVolume"
    ).solid_info.cubic_volume)
#an alternative way read the volume of the generated solid
print("same volume: ",tes.solid_info.cubic_volume)
```
See test test067_stl_volume for example.

### Reference
```{eval-rst}
.. autoclass:: opengate.geometry.volumes.TesselatedVolume
```

## Repeated volumes

### Description

The first method, described in this section, is controlled via the `translation` and `rotation` parameters. To instruct Geant4 to repeat a volume in multiple locations, it is sufficient to provide a list of translation vectors to the volume parameter `translation`. Gate will make sure that a G4PhysicalVolume is created for each entry. Consequently, the length of the list of translations determines the number of copies. If only a single rotation matrix is provided as volume parameter `rotation`, this will be used for all copies. If each copies requires a separate individual rotation, e.g. when repeating volume around a circle, then the volume parameter `rotation` should receive a list of rotation matrices. Obviously, the number of rotations and translation should match.

Each volume copy corresponds to a G4PhysicalVolume in Geant4 with its own unique name. Gate automatically generates this name. It can be obtained from a given copy index (counting starts at 0) via the method
```{eval-rst}
:py:meth:`opengate.geometry.volumes.RepeatableVolume.get_repetition_name_from_index`
```
. Or vice versa, the copy index can be obtained from the copy name via `get_repetition_index_from_name()`.

Gate comes with utility functions to generate translation and rotation parameters for common types of volume repetitions - see below.


```python
import opengate as gate
from scipy.spatial.transform import Rotation

cm = gate.g4_units.cm
crystal = sim.add_volume("Box", "crystal")
crystal.size = [1 * cm, 1 * cm, 1 * cm]
crystal.material = "LYSO"
m = Rotation.identity().as_matrix()
crystal.translation = [[1 * cm, 0 * cm, 0],
                       [0.2 * cm, 2 * cm, 0],
                       [-0.2 * cm, 4 * cm, 0]]
print(f"The crystal is repeated in {crystal.number_of_repetitions} locations. ")
print(f"Specified by the following translation vectors: ")
for i, t in enumrate(crystal.translation):
    print(f"Repetition {crystal.get_repetition_name_from_index(i)}: {t}. ")
```

In this example, the volume named `crystal`, with the shape of a box, a size of 1x1x1 cm<sup>3</sup>, and made of LYSO, is repeated in 3 positions. In this example, only the translation is modified, the rotation is set to the same default identity matrix.

There are utility functions that help you to generate lists of translations and rotations. For example:

```python
import opengate as gate
mm = gate.g4_units.mm
crystal = sim.add_volume("Box", "crystal")
translations_grid = gate.geometry.utility.get_grid_repetition(size=[1, 4, 5], spacing=[0, 32.85 * mm, 32.85 * mm])
crystal.translation = translations_grid
# or
detector = sim.add_volume("Box", "detector")
translations_circle, rotations_circle = gate.geometry.utility.get_circular_repetition(number_of_repetitions=18, first_translation=[391.5 * mm, 0, 0], axis=[0, 0, 1])
detector.translation = translations_circle
detector.rotation = rotations_circle
```

To get help about the utility functions, do:

```python
import opengate as gate
help(gate.geometry.utility.get_grid_repetition)
help(gate.geometry.utility.get_circular_repetition)
```

You can also have a look at the `philipsvereos.py` and `siemensbiograph.py` examples in the `opengate/contrib/pet/` folder.

You are obviously free to generate your own list of translations and rotations to suit your needs and they do not need to be regularly spaced and/or follow any spatial pattern such as a grid or ring. Just remember that Geant4 does not allow volumes to overlap and make sure that repetitions to not geometrically interfere (overlap) with each other.

Volume repetitions controlled via the `translation` and `rotation` parameter are a convenient and generic way to construct a "not too large" number of repeated objects. In case of "many" repetitions, the Geant4 tracking engine can become slow. In that case, it is better to use parameterised volumes described in the next section. It is not easy to quantify "not too many" repetitions. Based on our experience, a few hundred is still acceptable, but you might want to check in your case. Note that, if the volume contains sub-volumes (via their `mother` parameter, everything will be repeated, albeit in an optimized and efficient way.


## Repeat Parametrised Volumes

In some situations, the repeater concept explained in the previous section is not sufficient and can be inefficient when the number of repetitions is large. A specific example is a collimator for SPECT imaging containing a large number of holes. `RepeatParametrisedVolume` is an alternative repeated volume type which suits this use case. See this example:

```python
import opengate as gate
mm = gate.g4_units.mm
crystal = sim.add_volume("Box", "crystal")
param_vol = sim.add_volume("RepeatParametrised", f"my_param")
param_vol.repeated_volume_name = "crystal"
param_vol.translation = None
param_vol.rotation = None
size = [183, 235, 1]
tr = [2.94449 * mm, 1.7 * mm, 0]
param_vol.linear_repeat = size
param_vol.translation = tr
param_vol.start = [-(x - 1) * y / 2.0 for x, y in zip(size, tr)]
param_vol.offset_nb = 1
param_vol.offset = [0, 0, 0]
```

Note that the RepeatParametrisedVolume is still partly work in progress. The user guide on this will soon be updated and extended.

```python
param = sim.add_volume("RepeatParametrised", f"my_param")
param.repeated_volume_name = "crystal"
param.translation = None
param.rotation = None
size = [183, 235, 1]
tr = [2.94449 * mm, 1.7 * mm, 0]
param.linear_repeat = size
param.translation = tr
param.start = [-(x - 1) * y / 2.0 for x, y in zip(size, tr)]
param.offset_nb = 1
param.offset = [0, 0, 0]
```


## Boolean volumes

### Description

Geant4 provides a mechanism to combine volumetric shapes (Solids in Geant4) into new ones via boolean operations, i.e. `union`, `intersection`, and `subtraction`. In GATE, the details of this mechanism are taken care of under the hood and the user can directly combine compatible volumes. For example:

```python
import opengate as gate
from scipy.spatial.transform import Rotation

sim = gate.Simulation()
cm = gate.g4_units.cm
b = gate.geometry.volumes.BoxVolume(name="box")
b.size = [10 * cm, 10 * cm, 10 * cm]
s = gate.geometry.volumes.SphereVolume(name="sph")
s.rmax = 5 * cm
t = gate.geometry.volumes.TubsVolume(name="t")
t.rmin = 0
t.rmax = 2 * cm
t.dz = 15 * cm

combined_b_s = gate.geometry.volumes.unite_volumes(b, s, translation=[0, 1 * cm, 5 * cm])
final_vol = gate.geometry.volumes.subtract(combined_b_s, t, rotation=Rotation.from_euler("x", 3, degrees=True).as_matrix())

final_vol.translation = [5 * cm, 5 * cm, 5 * cm]
final_vol.mother = "world"
final_vol.material = "G4_WATER"
sim.add_volume(final_vol)
```

The keyword arguments `translation` and `rotation` specify how the second shape is translated and rotated, respectively, with respect to the first shape prior to the boolean operation. The absolute placement in space in the simulation is irrelevant for this. On the other hand, the line `final_vol.translation = [5 * cm, 5 * cm, 5 * cm]` simply refers to the [common parameter](#Common parameters) which specifies the placement of the final volume in space with respect to its mother, in this case the world volume.

Only the finally resulting volume `final_vol` is actually added to the simulation while the others are only created as intermediate steps of the contruction.

Note that not all volumes are compatible with boolean operations. For example, image volumes cannot be combined. You will receive an error message when trying to apply booelan operations to incompatible volumes.

Boolean operations are a great tool to build complex shapes. The phantoms in `opengate.contrib.phantoms` are good examples. Also have a look at `test016`. Be aware, however, that the Geant4 user guide warns that very extensive use of boolean operations can slow down particle tracking speed.

### Reference
```{eval-rst}
.. autoclass:: opengate.geometry.volumes.BooleanVolume
.. autofunction:: opengate.geometry.volumes.unite_volumes
```

