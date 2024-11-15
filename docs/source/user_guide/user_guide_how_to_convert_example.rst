Convert From Gate 9 to Gate 10 - Example
========================================
This section walks you through Gate 9 and Gate 10 versions of a simulation file used to create optical transport dataset for training OptiGAN.

Defining World Geometry
-----------------------

Gate 9

.. code-block::

    /gate/world/geometry/setXLength       10. cm
    /gate/world/geometry/setYLength       10. cm
    /gate/world/geometry/setZLength       15. cm
    /gate/world/setMaterial               Air

Gate 10

.. code-block:: python

    sim.world.size = [10 * cm, 10 * cm, 15 * cm]

The material of the world volume is set to 'Air' by default.

Gate 9

.. code-block::

    /gate/world/daughters/name                      OpticalSystem
    /gate/world/daughters/insert                    box
    /gate/OpticalSystem/geometry/setXLength         10. cm
    /gate/OpticalSystem/geometry/setYLength         10. cm
    /gate/OpticalSystem/geometry/setZLength         14.0 cm
    /gate/OpticalSystem/placement/setTranslation    0 0 0.0 cm
    /gate/OpticalSystem/setMaterial                 Air

Gate 10

.. code-block:: python

    optical_system = sim.add_volume("Box", "optical_system")
    optical_system.size = [10 * cm, 10 * cm, 14 * cm]
    optical_system.material = "G4_AIR"
    optical_system.translation = [0 * cm, 0 * cm, 0 * cm]

Gate 9

.. code-block::

    /gate/OpticalSystem/daughters/name              crystal
    /gate/OpticalSystem/daughters/insert            box
    /gate/crystal/geometry/setXLength               3.0 mm
    /gate/crystal/geometry/setYLength               3.0 mm
    /gate/crystal/geometry/setZLength               3.0 mm
    /gate/crystal/placement/setTranslation          0 0 10 mm
    /gate/crystal/setMaterial                       BGO

Gate 10

.. code-block:: python

    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = optical_system.name
    crystal.size = [3 * mm, 3 * mm, 20 * mm]
    crystal.translation = [0 * mm, 0 * mm, 10 * mm]
    crystal.material = "BGO"

Gate 9

.. code-block::

    /gate/OpticalSystem/daughters/name              grease
    /gate/OpticalSystem/daughters/insert            box
    /gate/grease/geometry/setXLength                3.0 mm
    /gate/grease/geometry/setYLength                3.0 mm
    /gate/grease/geometry/setZLength                0.015 mm
    /gate/grease/setMaterial                        Epoxy
    /gate/grease/placement/setTranslation           0 0 20.0075 mm

Gate 10

.. code-block:: python

    grease = sim.add_volume("Box", "grease")
    grease.mother = optical_system.name
    grease.size = [3 * mm, 3 * mm, 0.015 * mm]
    grease.material = "Epoxy"
    grease.translation = [0 * mm, 0 * mm, 20.0075 * mm]

Gate 9

.. code-block::

    /gate/OpticalSystem/daughters/name              pixel
    /gate/OpticalSystem/daughters/insert            box
    /gate/pixel/geometry/setXLength                 3 mm
    /gate/pixel/geometry/setYLength                 3 mm
    /gate/pixel/geometry/setZLength                 0.1 mm
    /gate/pixel/setMaterial                         SiO2
    /gate/pixel/placement/setTranslation            0 0 20.065 mm

Gate 10

.. code-block:: python

    pixel = sim.add_volume("Box", "pixel")
    pixel.mother = optical_system.name
    pixel.size = [3 * mm, 3 * mm, 0.1 * mm]
    pixel.material = "SiO2"
    pixel.translation = [0 * mm, 0 * mm, 20.065 * mm]

Defining Physics
----------------

Gate 9

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

Gate 10

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


Defining Optical Surfaces
-------------------------

Gate 9

.. code-block::

    /gate/crystal/surfaces/name                        surface1
    /gate/crystal/surfaces/insert                      OpticalSystem
    /gate/crystal/surfaces/surface1/setSurface         Customized3_LUT

Gate 10

.. code-block:: python

    opt_surf_optical_system_to_crystal = sim.physics_manager.add_optical_surface(
        volume_from="optical_system",
        volume_to="crystal",
        g4_surface_name="Customized3_LUT",
    )

Gate 9

.. code-block::

    /gate/OpticalSystem/surfaces/name                  surface2
    /gate/OpticalSystem/surfaces/insert                crystal
    /gate/OpticalSystem/surfaces/surface2/setSurface   Customized3_LUT

Gate 10

.. code-block:: python

    opt_surf_crystal_to_optical_system = sim.physics_manager.add_optical_surface(
        "crystal", "optical_system", "Customized3_LUT"
    )

Gate 9

.. code-block::

    /gate/crystal/surfaces/name                  surface5
    /gate/crystal/surfaces/insert                grease
    /gate/crystal/surfaces/surface5/setSurface   Customized2_LUT

Gate 10

.. code-block:: python

    opt_surf_grease_to_crystal = sim.physics_manager.add_optical_surface("grease", "crystal", "Customized2_LUT")

Gate 9

.. code-block::

    /gate/grease/surfaces/name                   surface6
    /gate/grease/surfaces/insert                 crystal
    /gate/grease/surfaces/surface6/setSurface    Customized2_LUT

Gate 10

.. code-block:: python

    opt_surf_crystal_to_grease = sim.physics_manager.add_optical_surface("crystal", "grease", "Customized2_LUT")

Gate 9

.. code-block::

    /gate/grease/surfaces/name                     Detection1
    /gate/grease/surfaces/insert                   pixel
    /gate/grease/surfaces/Detection1/setSurface    Customized4_LUT

Gate 10

.. code-block:: python

    opt_surface_pixel_to_grease = sim.physics_manager.add_optical_surface("pixel", "grease", "Customized4_LUT")

Gate 9

.. code-block::

    /gate/pixel/surfaces/name                       Detection2
    /gate/pixel/surfaces/insert                     grease
    /gate/pixel/surfaces/Detection2/setSurface      Customized4_LUT

Gate 10

.. code-block:: python

    opt_surf_grease_to_pixel = sim.physics_manager.add_optical_surface("grease", "pixel", "Customized4_LUT")

Defining Electron Source
------------------------

Gate 9

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

Gate 10

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

Defining Actor
--------------

Gate 9

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

Gate 10

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

Proton CT
---------

This is another example of a proton beam with a spiral phantom placed in between two proton detectors. The spiral phantom was used in the article `Filtered backprojection proton CT reconstruction along most likely paths by Rit et al <https://doi.org/10.1118/1.4789589>`_. The data generated by this simulation can be processed by the `PCT software <https://github.com/SimonRit/PCT>`_.

.. image:: ../figures/proton_ct.png

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - GATE 9
     - GATE 10
   * - Initialization
         .. code-block::

          /gate/run/initialize

          /gate/random/setEngineName MersenneTwister
          /gate/random/setEngineSeed auto

          /gate/application/setTimeSlice              1 s
          /gate/application/setTimeStart              0 s
          /gate/application/setTimeStop               360 s

          /gate/application/setTotalNumberOfPrimaries 720000
     - .. code-block:: python

        n = 360

        # Units
        nm = gate.g4_units.nm
        mm = gate.g4_units.mm
        cm = gate.g4_units.cm
        m = gate.g4_units.m
        sec = gate.g4_units.second
        MeV = gate.g4_units.MeV
        Bq = gate.g4_units.Bq

        # Simulation
        sim = gate.Simulation()

        sim.random_engine = "MersenneTwister"
        sim.random_seed = "auto"
        sim.run_timing_intervals = [[i * sec, (i + 1) * sec] for i in range(n)]
        sim.check_volumes_overlap = False
        sim.visu = True
        sim.visu_type = "qt"
        sim.g4_verbose = False
        sim.progress_bar = True
        sim.number_of_threads = 1

        # Misc
        yellow = [1, 1, 0, 1]
   * - Geometry
         .. code-block::

          /gate/geometry/setMaterialDatabase  data/GateMaterials.db
          /gate/world/setMaterial             Air
          /gate/world/geometry/setXLength     4 m
          /gate/world/geometry/setYLength     4 m
          /gate/world/geometry/setZLength     4 m
     - .. code-block:: python

          sim.volume_manager.add_material_database(path_to_gate_materials)
          sim.world.material = "Air"
          sim.world.size = [4 * m, 4 * m, 4 * m]
   * - Phantom
         .. code-block::

          /gate/world/daughters/name              Spiral
          /gate/world/daughters/insert            cylinder
          /gate/Spiral/geometry/setRmin           0 cm
          /gate/Spiral/geometry/setRmax           10 cm
          /gate/Spiral/geometry/setHeight         40 cm
          /gate/Spiral/setMaterial                Water
          /gate/Spiral/vis/setColor               yellow
          /gate/Spiral/vis/setVisible             1

          # Insert at radius 0.00 mm and angle 0.00 degree
          /gate/Spiral/daughters/name             SpiralInsert01
          /gate/Spiral/daughters/insert           cylinder
          /gate/SpiralInsert01/geometry/setRmin         0 mm
          /gate/SpiralInsert01/geometry/setRmax         1 mm
          /gate/SpiralInsert01/geometry/setHeight       40 cm
          /gate/SpiralInsert01/setMaterial              Aluminium
          /gate/SpiralInsert01/placement/setTranslation 0.0000 0.0000 0 mm
          /gate/SpiralInsert01/vis/setColor             yellow
          /gate/SpiralInsert01/vis/setVisible           1

          # ...
          # 24 additional inserts, omitted for brevity
          # ...

          /gate/Spiral/moves/insert       rotation
          /gate/Spiral/rotation/setSpeed  1 deg/s
          /gate/Spiral/rotation/setAxis   0 0 0
     - .. code-block:: python

        def add_spiral_insert(sim, mother, name, rmin=0 * mm, rmax=1 * mm, dz=40 * cm, material="Aluminium", translation=[0 * mm, 0 * mm, 0 * mm], color=yellow):
          spiral_insert = sim.add_volume("Tubs", name=name)
          spiral_insert.mother = mother.name
          spiral_insert.rmin = rmin
          spiral_insert.rmax = rmax
          spiral_insert.dz = dz
          spiral_insert.material = material
          spiral_insert.translation = translation
          spiral_insert.color = color

        def add_spiral(sim):
          # Mother of all
          spiral = sim.add_volume("Tubs", name="Spiral")
          spiral.rmin = 0 * cm
          spiral.rmax = 10 * cm
          spiral.dz = 40 * cm
          spiral.material = "Water"
          spiral.color = yellow

          # Spiral inserts
          sradius = 4
          radius = list(range(0, 100 - sradius // 2, sradius))
          sangle = 139
          angles = [math.radians(a) for a in range(0, sangle * len(radius), sangle)]
          posx = [radius[i] * math.cos(angles[i]) for i in range(len(radius))]
          posy = [radius[i] * math.sin(angles[i]) for i in range(len(radius))]

          for i in range(len(radius)):
               add_spiral_insert(sim, spiral, f"SpiralInsert{i:02d}", translation=[posx[i] * mm, posy[i] * mm, 0])

          # Spiral rotation
          sim.run_timing_intervals = gate.runtiming.range_timing(0, 1 * sec, n)
          tr, rot = gate.geometry.utility.volume_orbiting_transform("z", 0, 360, n, spiral.translation, spiral.rotation)
          spiral.add_dynamic_parametrisation(translation=tr, rotation=rot)

        add_spiral(sim)
   * - Beam
         .. code-block::

          /gate/source/addSource mybeam gps
          /gate/source/mybeam/gps/particle       proton
          /gate/source/mybeam/gps/ene/mono       200 MeV
          /gate/source/mybeam/gps/ene/type       Mono
          /gate/source/mybeam/gps/pos/halfx      8 mm
          /gate/source/mybeam/gps/pos/halfy      1 mm
          /gate/source/mybeam/gps/pos/centre     1060 0 0 mm
          /gate/source/mybeam/gps/pos/rot1       0 1 0
          /gate/source/mybeam/gps/pos/rot2       0 0 1
          /gate/source/mybeam/gps/pos/type       Plane
          /gate/source/mybeam/gps/pos/shape      Rectangle
          /gate/source/mybeam/gps/direction      -1 0 0
          /gate/source/mybeam/gps/ang/type       focused
          /gate/source/mybeam/gps/ang/rot1       0 1 0
          /gate/source/mybeam/gps/ang/rot2       0 0 1
          /gate/source/mybeam/gps/ang/focuspoint 1000 0 0 mm

     - .. code-block:: python

        source = sim.add_source("GenericSource", "mybeam")
        source.particle = "proton"
        source.energy.mono = 200 * MeV
        source.energy.type = "mono"
        source.position.type = "box"
        source.position.size = [1 * nm, 16 * mm, 1 * nm]
        source.position.translation = [-1060 * mm, 0 * mm, 0 * mm]
        source.direction.type = "focused"
        source.direction.focus_point = [-1000 * mm, 0 * mm, 0 * mm]
        source.n = 720000 / sim.number_of_threads
   * - Physics list
         .. code-block::

          /control/execute mac/physicslist_EM_std.mac
          /control/execute mac/physicslist_HAD_std.mac
     - .. code-block:: python

        sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"

   * - Phase spaces
         .. code-block::

          /gate/world/daughters/name                          PlanePhaseSpaceIn
          /gate/world/daughters/insert                        box
          /gate/PlanePhaseSpaceIn/geometry/setXLength         1 nm
          /gate/PlanePhaseSpaceIn/geometry/setYLength         400 mm
          /gate/PlanePhaseSpaceIn/geometry/setZLength         400 mm
          /gate/PlanePhaseSpaceIn/setMaterial                 Air
          /gate/PlanePhaseSpaceIn/vis/setVisible              1
          /gate/PlanePhaseSpaceIn/vis/setColor                yellow

          /gate/actor/addActor PhaseSpaceActor                PhaseSpaceIn
          /gate/actor/PhaseSpaceIn/save                       output/PhaseSpaceIn.root
          /gate/actor/PhaseSpaceIn/attachTo                   PlanePhaseSpaceIn
          /gate/actor/PhaseSpaceIn/enableEkine                true
          /gate/actor/PhaseSpaceIn/enableXPosition            false
          /gate/actor/PhaseSpaceIn/enableYPosition            true
          /gate/actor/PhaseSpaceIn/enableZPosition            true
          /gate/actor/PhaseSpaceIn/enableXDirection           true
          /gate/actor/PhaseSpaceIn/enableYDirection           true
          /gate/actor/PhaseSpaceIn/enableZDirection           true
          /gate/actor/PhaseSpaceIn/enableProductionVolume     false
          /gate/actor/PhaseSpaceIn/enableProductionProcess    false
          /gate/actor/PhaseSpaceIn/enableParticleName         false
          /gate/actor/PhaseSpaceIn/enableWeight               false
          /gate/actor/PhaseSpaceIn/enableTime                 true
          /gate/actor/PhaseSpaceIn/storeSecondaries           true
          /gate/actor/PhaseSpaceIn/useVolumeFrame             false
          /gate/actor/PhaseSpaceIn/storeOutgoingParticles     false               particleFilter
          /gate/actor/PhaseSpaceIn/particleFilter/addParticle proton
          0 0 mm

          /gate/world/daughters/name                           PlanePhaseSpaceOut
          /gate/world/daughters/insert                         box
          /gate/PlanePhaseSpaceOut/geometry/setXLength         1 nm
          /gate/PlanePhaseSpaceOut/geometry/setYLength         400 mm
          /gate/PlanePhaseSpaceOut/geometry/setZLength         400 mm
          /gate/PlanePhaseSpaceOut/setMaterial                 Air
          /gate/PlanePhaseSpaceOut/vis/setVisible              1
          /gate/PlanePhaseSpaceOut/vis/setColor                yellow

          /gate/actor/addActor PhaseSpaceActor                 PhaseSpaceOut
          /gate/actor/PhaseSpaceOut/save                       output/PhaseSpaceOut.root
          /gate/actor/PhaseSpaceOut/attachTo                   PlanePhaseSpaceOut
          /gate/actor/PhaseSpaceOut/enableEkine                true
          /gate/actor/PhaseSpaceOut/enableXPosition            false
          /gate/actor/PhaseSpaceOut/enableYPosition            true
          /gate/actor/PhaseSpaceOut/enableZPosition            true
          /gate/actor/PhaseSpaceOut/enableXDirection           true
          /gate/actor/PhaseSpaceOut/enableYDirection           true
          /gate/actor/PhaseSpaceOut/enableZDirection           true
          /gate/actor/PhaseSpaceOut/enableProductionVolume     false
          /gate/actor/PhaseSpaceOut/enableProductionProcess    false
          /gate/actor/PhaseSpaceOut/enableParticleName         false
          /gate/actor/PhaseSpaceOut/enableWeight               false
          /gate/actor/PhaseSpaceOut/enableTime                 true
          /gate/actor/PhaseSpaceOut/storeSecondaries           true
          /gate/actor/PhaseSpaceOut/useVolumeFrame             false
          /gate/actor/PhaseSpaceOut/storeOutgoingParticles     false
          /gate/actor/PhaseSpaceOut/particleFilter/addParticle proton

     - .. code-block:: python

          def add_detector(sim, name, translation):
              plane = sim.add_volume("Box", "PlanePhaseSpace" + name)
              plane.size = [1 * nm, 400 * mm, 400 * mm]
              plane.translation = translation
              plane.material = "Air"
              plane.color = yellow

              phase_space = sim.add_actor("PhaseSpaceActor", "PhaseSpace" + name)
              phase_space.attached_to = plane.name
              phase_space.attributes = [
                  "RunID",
                  "EventID",
                  "TrackID",
                  "TrackCreatorProcess",
                  "KineticEnergy",
                  "Position",
                  "Direction",
                  "GlobalTime"
              ]
              filter = sim.add_filter("ParticleFilter", "Filter" + name)
              filter.particle = "proton"
              phase_space.filters.append(filter)

          add_detector(sim, "In", [-110 * mm, 0 * mm, 0 * mm])
          add_detector(sim, "Out", [110 * mm, 0 * mm, 0 * mm])
   * - Particles stats
         .. code-block::

          /gate/actor/addActor  SimulationStatisticActor stat
          /gate/actor/stat/save output/protonct.txt
     - .. code-block:: python

        stat = sim.add_actor("SimulationStatisticsActor", "stat")
        stat.output_filename = "output/protonct.txt"
   * - Main
         .. code-block::

          /gate/application/start
     - .. code-block:: python

        sim.run()