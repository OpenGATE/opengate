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

### Repeated and parameterized volumes

### Boolean volumes
