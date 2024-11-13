Migrating from GATE 9
=====================

This page contains a series of examples of non-trivial GATE 9 macros converted into GATE 10.

Proton CT
---------

A proton beam with a spiral phantom placed in between two proton detectors.

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
          /gate/Spiral/rotation/setAxis   0 0 1
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
            translations = [
                [0, 0, 0],
                [-3.0188, 2.6242, 0],
                [1.1134, -7.9221, 0],
                [6.5357, 10.0640, 0],
                [-15.3802, -4.4102, 0],
                [18.1262, -8.4524, 0],
                [-9.7617, 21.9251, 0],
                [-8.1864, -26.7765, 0],
                [27.1375, 16.9574, 0],
                [-35.5568, 5.6316, 0],
                [25.7115, -30.6418, 0],
                [0.7679, 43.9933, 0],
                [-32.1183, -35.6710, 0],
                [51.6124, 6.3372, 0],
                [-46.4261, 31.3148, 0],
                [15.5291, -57.9555, 0],
                [28.0558, 57.5228, 0],
                [-62.5943, -26.5697, 0],
                [68.4761, -22.2492, 0],
                [-39.1429, 65.1447, 0],
                [-13.8919, -78.7846, 0],
                [65.2803, 52.8629, 0],
                [-87.9464, 3.0712, 0],
                [67.2845, -62.7438, 0],
                [-10.0347, 95.4741, 0]
            ]
            assert len(translations) == 25
            for i in range(1, len(translations) + 1):
                tx, ty, tz = translations[i - 1]
                add_spiral_insert(sim, spiral, f"SpiralInsert{i:02d}", translation=[tx * mm, ty * mm, tz * mm])

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