Convert From Gate 9 to Gate 10 - Example :
=========================================================================
This section walks you through Gate 9 and Gate 10 versions of a simulation file used to create optical transport dataset for training OptiGAN.

Defining World Geometry -
-------------------------

Gate 9 -

.. code-block::

    /gate/world/geometry/setXLength       10. cm
    /gate/world/geometry/setYLength       10. cm
    /gate/world/geometry/setZLength       15. cm
    /gate/world/setMaterial               Air

Gate 10 -

.. code-block:: python

    sim.world.size = [10 * cm, 10 * cm, 15 * cm]

The material of the world volume is set to 'Air' by default.

Gate 9 -

.. code-block::

    /gate/world/daughters/name                      OpticalSystem
    /gate/world/daughters/insert                    box
    /gate/OpticalSystem/geometry/setXLength         10. cm
    /gate/OpticalSystem/geometry/setYLength         10. cm
    /gate/OpticalSystem/geometry/setZLength         14.0 cm
    /gate/OpticalSystem/placement/setTranslation    0 0 0.0 cm
    /gate/OpticalSystem/setMaterial                 Air

Gate 10 -

.. code-block:: python

    optical_system = sim.add_volume("Box", "optical_system")
    optical_system.size = [10 * cm, 10 * cm, 14 * cm]
    optical_system.material = "G4_AIR"
    optical_system.translation = [0 * cm, 0 * cm, 0 * cm]

Gate 9 -

.. code-block::

    /gate/OpticalSystem/daughters/name              crystal
    /gate/OpticalSystem/daughters/insert            box
    /gate/crystal/geometry/setXLength               3.0 mm
    /gate/crystal/geometry/setYLength               3.0 mm
    /gate/crystal/geometry/setZLength               3.0 mm
    /gate/crystal/placement/setTranslation          0 0 10 mm
    /gate/crystal/setMaterial                       BGO

Gate 10 -

.. code-block:: python

    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = optical_system.name
    crystal.size = [3 * mm, 3 * mm, 20 * mm]
    crystal.translation = [0 * mm, 0 * mm, 10 * mm]
    crystal.material = "BGO"

Gate 9 -

.. code-block::

    /gate/OpticalSystem/daughters/name              grease
    /gate/OpticalSystem/daughters/insert            box
    /gate/grease/geometry/setXLength                3.0 mm
    /gate/grease/geometry/setYLength                3.0 mm
    /gate/grease/geometry/setZLength                0.015 mm
    /gate/grease/setMaterial                        Epoxy
    /gate/grease/placement/setTranslation           0 0 20.0075 mm

Gate 10 -

.. code-block:: python

    grease = sim.add_volume("Box", "grease")
    grease.mother = optical_system.name
    grease.size = [3 * mm, 3 * mm, 0.015 * mm]
    grease.material = "Epoxy"
    grease.translation = [0 * mm, 0 * mm, 20.0075 * mm]

Gate 9 -

.. code-block::

    /gate/OpticalSystem/daughters/name              pixel
    /gate/OpticalSystem/daughters/insert            box
    /gate/pixel/geometry/setXLength                 3 mm
    /gate/pixel/geometry/setYLength                 3 mm
    /gate/pixel/geometry/setZLength                 0.1 mm
    /gate/pixel/setMaterial                         SiO2
    /gate/pixel/placement/setTranslation            0 0 20.065 mm

Gate 10 -

.. code-block:: python

    pixel = sim.add_volume("Box", "pixel")
    pixel.mother = optical_system.name
    pixel.size = [3 * mm, 3 * mm, 0.1 * mm]
    pixel.material = "SiO2"
    pixel.translation = [0 * mm, 0 * mm, 20.065 * mm]

Defining Physics -
------------------

Gate 9 -

.. code-block::

    /gate/physics/addPhysicsList emstandard_opt4
    /gate/physics/addPhysicsList optical

    /gate/physics/addProcess Scintillation
    /gate/physics/addProcess Cerenkov e+
    /gate/physics/addProcess Cerenkov e-

    /gate/physics/Electron/SetCutInRegion   world 10 mm
    /gate/physics/Positron/SetCutInRegion   world 10 um
    /gate/physics/Electron/SetCutInRegion   crystal 10 um
    /gate/physics/Positron/SetCutInRegion   crystal 10 um

    /gate/physics/processList Enabled
    /gate/physics/processList Initialized

Gate 10 -

.. code-block:: python

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"

    # This also includes Scintillation and Cerenkov processes.
    sim.physics_manager.special_physics_constructors.G4OpticalPhysics = True

    sim.physics_manager.set_production_cut("world", "electron", 10 * mm)
    sim.physics_manager.set_production_cut("world", "positron", 10 * um)
    sim.physics_manager.set_production_cut("crystal", "electron", 10 * um)
    sim.physics_manager.set_production_cut("crystal", "positron", 10 * um)

    # In Gate 10, enery range limits should be set like this for scintillation.
    # Reason for this is unknown.
    sim.physics_manager.energy_range_min = 10 * eV
    sim.physics_manager.energy_range_max = 1 * MeV


Defining Optical Surfaces -
---------------------------

Gate 9 -

.. code-block::

    /gate/crystal/surfaces/name                        surface1
    /gate/crystal/surfaces/insert                      OpticalSystem
    /gate/crystal/surfaces/surface1/setSurface         Customized3_LUT

Gate 10 -

.. code-block:: python

    opt_surf_optical_system_to_crystal = sim.physics_manager.add_optical_surface(
        volume_from="optical_system",
        volume_to="crystal",
        g4_surface_name="Customized3_LUT",
    )

Gate 9 -

.. code-block::

    /gate/OpticalSystem/surfaces/name                  surface2
    /gate/OpticalSystem/surfaces/insert                crystal
    /gate/OpticalSystem/surfaces/surface2/setSurface   Customized3_LUT

Gate 10 -

.. code-block:: python

    opt_surf_crystal_to_optical_system = sim.physics_manager.add_optical_surface(
        "crystal", "optical_system", "Customized3_LUT"
    )

Gate 9 -

.. code-block::

    /gate/crystal/surfaces/name                  surface5
    /gate/crystal/surfaces/insert                grease
    /gate/crystal/surfaces/surface5/setSurface   Customized2_LUT

Gate 10 -

.. code-block:: python

    opt_surf_grease_to_crystal = sim.physics_manager.add_optical_surface("grease", "crystal", "Customized2_LUT")

Gate 9 -

.. code-block::

    /gate/grease/surfaces/name                   surface6
    /gate/grease/surfaces/insert                 crystal
    /gate/grease/surfaces/surface6/setSurface    Customized2_LUT

Gate 10 -

.. code-block:: python

    opt_surf_crystal_to_grease = sim.physics_manager.add_optical_surface("crystal", "grease", "Customized2_LUT")

Gate 9 -

.. code-block::

    /gate/grease/surfaces/name                     Detection1
    /gate/grease/surfaces/insert                   pixel
    /gate/grease/surfaces/Detection1/setSurface    Customized4_LUT

Gate 10 -

.. code-block:: python

    opt_surface_pixel_to_grease = sim.physics_manager.add_optical_surface("pixel", "grease", "Customized4_LUT")

Gate 9 -

.. code-block::

    /gate/pixel/surfaces/name                       Detection2
    /gate/pixel/surfaces/insert                     grease
    /gate/pixel/surfaces/Detection2/setSurface      Customized4_LUT

Gate 10 -

.. code-block:: python

    opt_surf_grease_to_pixel = sim.physics_manager.add_optical_surface("grease", "pixel", "Customized4_LUT")

Defining Electron Source -
--------------------------

Gate 9 -

.. code-block::

    /gate/source/addSource                   Mysource
    /gate/source/Mysource/gps/particle       e-
    /gate/source/Mysource/gps/energytype       Mono
    /gate/source/Mysource/gps/type             Volume
    /gate/source/Mysource/gps/shape            Sphere
    /gate/source/Mysource/gps/radius           0. mm
    /gate/source/Mysource/setActivity          1000 becquerel
    /gate/source/Mysource/gps/monoenergy       420 keV
    /gate/source/Mysource/gps/centre           0 0 19 mm

    /gate/source/Mysource/gps/ang/type iso
    /gate/source/Mysource/gps/ang/mintheta 163. deg
    /gate/source/Mysource/gps/ang/maxtheta 165. deg

Gate 10 -

.. code-block:: python

    source = sim.add_source("GenericSource", "my_source")
    source.particle = "e-"
    source.energy.type = "mono"
    source.energy.mono = 420 * keV
    source.position.type = "sphere"
    source.position.radius = 0 * mm
    source.activity = 1000 * Bq
    source.direction.type = "iso"
    source.direction.theta = [163 * deg, 165 * deg]
    source.direction.phi = [100 * deg, 110 * deg]
    source.position.translation = [0 * mm, 0 * mm, 19 * mm]

Defining Actor -
----------------

Gate 9 -

.. code-block::

    /gate/actor/addActor PhaseSpaceActor MyActor
    /gate/actor/MyActor/attachTo pixel

    /gate/actor/MyActor/enableTime true
    /gate/actor/MyActor/enableLocalTime true
    /gate/actor/MyActor/enableTimeFromBeginOfEvent true
    /gate/actor/MyActor/enableTProd true
    /gate/actor/MyActor/enableTOut true
    /gate/actor/MyActor/enableTrackLength true
    /gate/actor/MyActor/enableEmissionPoint true
    /gate/actor/MyActor/enableElectronicDEDX true
    /gate/actor/MyActor/save ./output/{NameOutputSimu}/MyActorPixel_In.root

Gate 10 -

.. code-block:: python

    phase = sim.add_actor("PhaseSpaceActor", "Phase")
    phase.attached_to = pixel.name
    phase.output_filename = "test075_optigan_create_dataset_first_phase_space_with_track_volume.root"
    phase.attributes = [
        "EventID",
        "ParticleName",
        "Position",
        "TrackID",
        "ParentID",
        "Direction",
        "KineticEnergy",
        "PreKineticEnergy",
        "PostKineticEnergy",
        "TotalEnergyDeposit",
        "LocalTime",
        "GlobalTime",
        "TimeFromBeginOfEvent",
        "StepLength",
        "TrackCreatorProcess",
        "TrackLength",
        "TrackVolumeName",
        "PDGCode",
    ]

