## Geometry and volumes

Gate fundamentally relies on the geometry principle of Geant4, but provides the user with an easy-to-use interface to set up the geometry of a simulation. Nonetheless, a basic understanding of how Geant4 handles geometrical objects is useful and we refer the user to the Geant4 user guide. 

### Overview: Volumes

Volumes are the components that make up the simulation geometry. Following Geant4 logic, a volume contains information about its shape, its placement in space, its material, and possibly settings about physics modeling within that volume. In Gate, all these properties are stored and handled in a single volume object. Volumes are managed by the VolumeManager.

Volumes can be created in two ways:

1) With the `add_volume` command, providing the type of the volume as string argument. It is mandatory to provide a unique name as well. A volume is created according to the specified volume type and the volume object is returned.
Example:

```python
sim = opengate.Simulation()
myboxvol = sim.add_volume('Box', name='mybox')
```
Most users will opt for this way of creating volumes.

2) By calling the volume class. In this case, the volume is created, but not yet added to the simulation. It has to be added to the simulation explicitly.
Example:

```python
sim = opengate.Simulation()
myspherevol = opengate.geometry.volumes.SphereVolume(name='mysphere')
sim.add_volume(myspherevol)
```
This second way of creating volumes is useful in cases where the volume is needed but should not be part of the simulation. For example, if it serves as basis for a boolean operation, e.g. to be intersected with another volume.

Note that the `add_volume` command in the second example does not require the `name` because the volume already exists and already has a name. For the same reason, the `add_volume` command does not return anything, i.e. it returns `None`.

Note: Every simulation has a default volume called `world` (lowercase) which is automatically created.

The parameters of a volume can be set as follows:

```python
vol = sim.add_volume('Box', 'mybox')
vol.material = 'G4_AIR'
vol.mother = 'world'  # by default
cm = gate.g4_units.cm
mm = gate.g4_units.mm
vol.size = [10 * cm, 5 * cm, 15 * mm]
```

To get an overview of all the properties of a volume, simply print it:
```python
vol = sim.add_volume('Box', 'mybox')
print(vol)
```

In an interactive python console, e.g. ipython, you can also type `help(vol)` to get an explanation of the parameters.

To dump a list of all available volume types:

```
print('Volume types :', sim.volume_manager.dump_volume_types())
```

Remember that under the hood, volumes are handled and parametrized by Geant4. GATE just sets them up for you. Therefore, it might be worthwhile looking at the [Geant4 user guide](http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html#constructed-solid-geometry-csg-solids) as well.


### Volume hierarchy

All volumes have a parameter `mother` which contains the name of the volume to which they are attached. By default, this is the world volume indicated by the word `world`. Gate creates a hierarchy of volumes based on the mother parameter, according to Geant4's logic of hierarchically nested volumes. The volume hierarchy can be inspected with the command `dump_volume_tree` of the volume manager. Example:

```python
import opengate
sim = opengate.Simulation
b1 = sim.add_volume('Box', name='b1')
b1_a = sim.add_volume('Box', name='b1_a')
b1_b = sim.add_volume('Box', name='b1_b')
b1_a.mother = b1
b1_b.mother = b1
sim.volume_manager.dump_volume_tree()
```


### Common parameters

Some of the parameters are common to **all** volumes, while others are specific to a certain type of volume. Use `print(vol)` to display the volume's parameters and their default values.

Common parameters are:

- `mother`: the name of the mother volume (`world` by default) in the hierarchy of volume. Volumes are always positioned in the reference frame of the mother volume and therefore move with the mother volume.
- `material`: the name of the material that composes the volume, e.g. `G4_WATER`. See section [Materials](### Materials)
- `translation`: list of 3 numerical values, e.g. `[0, 2*cm, 3*mm]`. It defines the translation of the volume with respect to the reference frame of the mother volume. Note: the origin of the reference frame is always at the center of the shape in Geant4.
- `rotation`: a 3x3 rotation matrix. Rotation of the volume with respect to the mother volume. We advocate the use of `scipy.spatial.transform.Rotation` to manage the rotation matrix.
- `color`: a list of 4 values (Red, Green, Blue, Opacity), between 0 and 1, e.g. `[1, 0, 0, 0.5]`. Only used when visualization is on.

Take a look at `test007` as example for simple volumes.


### Materials

From the simulation point of view, a material is a set of parameters describing its chemical composition and physical properties such as its density. 

Geant4 defines a set of default materials which are also available in GATE. A prominent example is "G4_WATER". 
The full of Geant4 materials is available [here](https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Appendix/materialNames.html).

On top of that, Gate provides different mechanisms to define additional materials. One option is via a text file which can be loaded with

```python
sim.volume_manager.add_material_database("GateMaterials.db")
```

All material names defined in the "GateMaterials.db" can then be used for any volume. Please check the file in `tests/data/GateMaterials.db` for the required format of database file.

<!--
Alternatively, materials can be created within a simulation script with the following command:

```python
import opengate
gate.volume_manager.new_material("mylar", 1.38 * gcm3, ["H", "C", "O"], [0.04196, 0.625016, 0.333024])
```

This function creates a material named "mylar", with the given mass density and the composition (H C and O here) described as a vector of percentages. Note that the weights are normalized. The created material can then be used for any volume.
-->

### Image volumes

An image volumes is essentially a box filled with a voxelized volumetric (3D) image. The box containing the image behaves pretty much like a box volume. The image should be provided in a format readable by *itk* and the path to the image file is set via the parameter `image`. In general, we advocate the use of mhd/raw file format, but other file format can be used. The image must be 3D, with any pixel type (float, int, char, etc).
In order for Gate/Geant4 to make use of the image, the image values need to be mapped to materials to be associated with the corresponding voxel. Therefore, you need to provide a lookup table via the parameter `voxel_materials`, which is a list of 3-item-lists, each defining a value range and the material name to be used. Take the following example: 


```python
import opengate as gate
sim = gate.Simulation()
patient = sim.add_volume("Image", name="patient")
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

In the example above, the material "Lung" will be assigned to every voxel with a value between -900 and -100. The volume's default material, `patient.material = "G4_AIR"` in the example above, will be assigned to any voxel whose values does not fall into any of the provided intervals. See test `test009` as an example simulation using an Image volume.

There is a specific function that can help to automatically create such an array of intervals for conventional Hounsfield Unit of CT images:

```python
gcm3 = gate.g4_units.g_cm3
f1 = "Schneider2000MaterialsTable.txt"
f2 = "Schneider2000DensitiesTable.txt"
tol = 0.05 * gcm3
patient.voxel_materials, materials = gate.HounsfieldUnit_to_material(sim, tol, f1, f2)
patient.dump_label_image = "labels.mhd"
```

In that case, the `HounsfieldUnit_to_material` function will create the array of intervals. It also creates a list of materials. The input parameters for this function are 1) the density tolerance (in g/cm3), 2) a list of reference material and 3) a list of reference densities. Example of such files can be found in `opengate/tests/data` folder. The option `dump_label_image` is a help and can be used to write the corresponding labeled image (every voxel value is replaced by the material label). See for example the test `t009`.

The coordinate system of such image is like for other Geant4's volumes: by default, the center of the image is positioned at the origin. The embedded origin in the image (like in DICOM or mhd) is *not* considered here. This is the user responsibility to compute the needed translation/rotation.


### Repeated volumes

Sometimes, it can be convenient to duplicate a volume at different locations. This is for example the case in a PET simulation where the crystal, or some parts of the detector, are repeated. There are two ways to achieve this.

The first method described in this section is controlled via the `repeat` parameter, which must be a list of dictionaries. Each dictionary specifies one repetition of the volume and should have the following entries:
- 'name'
- 'translation'
- 'rotation'

```python
import opengate as gate
from scipy.spatial.transform import Rotation

cm = gate.g4_units.cm
crystal = sim.add_volume("Box", "crystal")
crystal.size = [1 * cm, 1 * cm, 1 * cm]
crystal.material = "LYSO"
m = Rotation.identity().as_matrix()
crystal.repeat = [
    {"name": "crystal1", "translation": [1 * cm, 0 * cm, 0], "rotation": m},
    {"name": "crystal2", "translation": [0.2 * cm, 2 * cm, 0], "rotation": m},
    {"name": "crystal3", "translation": [-0.2 * cm, 4 * cm, 0], "rotation": m},
    {"name": "crystal4", "translation": [0, 6 * cm, 0], "rotation": m},
]
```

In this example, the volume named `crystal` with the shape of a box, a size 1x1x1 cm3, and made if LYSO, is repeated in 4 positions. The list set in `crystal.repeat` describes for each of the 4 copies, the name of the copy, the translation and the rotation. In this example, only the translation is modified, the rotation is set to the same (identity) matrix. Of course, any rotation matrix can be given to each copy.
Note that the parameters `crystal.translation` and `crystal.rotation` of the repeated volume are ignored and only the translation and rotation provided in the repeat dictionaries are considered.

There are utility functions that help to generate lists of repeat dictionaries. For example:

```python
import opengate as gate
mm = gate.g4_units.mm
crystal = sim.add_volume("Box", "crystal")
crystal.repeat = gate.geometry.utility.repeat_array("crystal", [1, 4, 5], [0, 32.85 * mm, 32.85 * mm])
crystal.repeat = gate.geometry.utility.repeat_ring("crystal", 190, 18, [391.5 * mm, 0, 0], [0, 0, 1])
```

Here, the `repeat_array` function is a helper to generate a 3D grid repetition with the number of repetition along the x, y and z axis is given in the first array `[1, 4, 5]`. In this examples, there are a single repetition along x, 4 along y and 5 along z. The offsets are given in the second array: `[0, 32.85 * mm, 32.85 * mm]`, meaning that, e.g., the y repetitions will be separated by 32.85 mm. This helper function returns a list of dictionaries that can be used to set the parameter `crystal.repeat` of the previous example. The names of the repetitions will be generated from the word "crystal" by appending the copy number, i.e. "crystal_1", "crystal_2", etc.

The second helper function `repeat_ring` generates ring-link repetitions. The first parameter (190) is the starting angle, the second is the number of repetitions (18 here). The third is the initial translation of the first repetition. The fourth is the rotation axis (along the z-axis here). This function returns a list of dictionaries that can be used to set the `repeat` parameter of the `crystal` volume. It is for example useful for PET systems. You can look at the `pet_philips_vereos.py` example in the `opengate/contrib` folder.

You are obviously free to generated your own list of repeat dictionaries to suit your needs.

### Parametrised Volumes

Volume repetitions controlled via the `repeat` parameter are a convenient and generic way to construct a "not too large" number of repeated objects. In case of "many" repetitions, the Geant4 tracking engine can become slow. In that case, it is better to use parameterised volumes described in this section. It is not easy to quantify "not too many" repetitions. Based on our experience, a few hundred is ok, but you might want to check in your case. Note that, if the volume contains sub-volumes, everything will be repeated (in an optimized and efficient way).



In some situations, this repeater concept is not sufficient and can be inefficient when the number of repetitions is large. This is for example the case when describing a collimator for SPECT imaging. Thus, there is an alternative way to describe repetitions by using the so-called "parameterized" volume.

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


### Boolean volumes

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


### Examples of complex geometries: Linac, SPECT, PET, phantoms

Examples of complex nested geometries, partly relying on boolean and repeat operations, can be found in the subpackages `opengate.contrib.pet`,  `opengate.contrib.spect`, `opengate.contrib.linacs`, `opengate.contrib.phantoms`. Also have a look at some of the tests that use these geometries, e.g. `test015` (iec phantom), `test019` (linac Elekta), `test028` (SPECT GE NM670), `test037` (Philips Vereos PET).
