
Volumes
=======

Volumes are the elements that describe solid objects. There is a default volume called 'World' automatically created. All volumes can be created with the :code:`add_volume` command. The parameters of the resulting volume
can be easily set as follows::

  vol = sim.add_volume('Box', 'mybox')
  print(vol) # to display the default parameter values
  vol.material = 'G4_AIR'
  vol.mother = 'World' # by default
  cm = gam.g4_units('cm')
  mm = gam.g4_units('mm')
  vol.size = [10 * cm, 5 * cm, 15 * mm]

  # print the list of available volumes types:
  print('Volume types :', sim.dump_volume_types())


The return of :code:`add_volume` is a :code:`UserInfo` object (that can be view as a dict). All volumes must have a material ('G4_AIR' by default) and a mother ('World' by default). Volumes must follow a hierarchy like volumes in Geant4. All volumes have a default list of parameters you can print (:code:`print(vol)`).

Common parameters
-----------------

Some parameters are specific to one volume type (for example :code:`size` for :code:`Box`, or :code:`radius` for :code:`Sphere`), but all volumes share some common parameters:

 - :code:`mother`: the name of the mother volume ('world' by default) in the hierarchy of volume. The volume will consider its coordinates system the one of his mother.
 - :code:`material`: the name of the material that compose the volume ('G4_WATER' for example).
 - :code:`translation`: the translation (list of 3 values), such that :code:`[0, 2*cm, 3*mm]`, to place the volume according to his coordinate system (the one from his mother)
 - :code:`rotation`: a rotation matrix. We advocate the use of :code:`scipy.spatial.transform` :code:`Rotation` object to manage rotation matrix.
 - :code:`repeat`: a list of dictionary of 'name' + 'translation' + 'rotation'. Each element of the list will create a repeated copy of the volume, positionned according to the translation and rotation (see :code:`test017`)
 - :code:`color`: a color as a list of 4 values :code:`[1, 0, 0, 0.5]` (Red, Green, Blue, Opacity) between 0 and 1. Only use when visualization is on.


See for example :code:`test007` and :code:`test017` test files for more details.

Materials
---------

todo
