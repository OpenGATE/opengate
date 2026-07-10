import opengate as gate


def create_simulation(paths, num_threads):

    root_filename = paths.output / "output_singles.root"

    sim = gate.Simulation()

    sim.visu = False
    sim.random_seed = 1234
    sim.number_of_threads = num_threads

    # Units
    mm = gate.g4_units.mm
    sec = gate.g4_units.s
    ns = gate.g4_units.ns
    Bq = gate.g4_units.Bq
    gcm3 = gate.g4_units.g_cm3
    deg = gate.g4_units.deg

    # World
    world = sim.world
    world.size = [450 * mm, 450 * mm, 70 * mm]
    world.material = "G4_AIR"

    sim.volume_manager.material_database.add_material_weights(
        "LYSO",
        ["Lu", "Y", "Si", "O"],
        [0.31101534, 0.368765605, 0.083209699, 0.237009356],
        5.37 * gcm3,
    )

    # Ring volume
    pet = sim.add_volume("Tubs", "pet")
    pet.rmax = 200 * mm
    pet.rmin = 127 * mm
    pet.dz = 32 * mm
    pet.material = "G4_AIR"

    # Block
    block = sim.add_volume("Box", "block")
    block.mother = pet.name
    block.size = [60 * mm, 20 * mm, 20 * mm]
    translations_ring, rotations_ring = gate.geometry.utility.get_circular_repetition(
        40, [160 * mm, 0.0 * mm, 0], start_angle_deg=180, axis=[0, 0, 1]
    )
    block.translation = translations_ring
    block.rotation = rotations_ring
    block.material = "G4_AIR"

    # Crystal
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = block.name
    crystal.size = [60 * mm, 20 * mm, 20 * mm]
    crystal.material = "LYSO"

    source1 = sim.add_source("GenericSource", "b2b_1")
    source1.particle = "back_to_back"
    source1.activity = 5 * 1e6 * Bq / num_threads
    source1.position.type = "point"
    source1.position.translation = [100 * mm, 0, 0]
    source1.direction.theta = [90 * deg, 90 * deg]
    source1.direction.phi = [0, 360 * deg]

    source2 = sim.add_source("GenericSource", "b2b_2")
    source2.particle = "back_to_back"
    source2.activity = 5 * 1e6 * Bq / num_threads
    source1.position.translation = [-100 * mm, 0, 0]
    source2.position.type = "point"
    source2.direction.theta = [90 * deg, 90 * deg]
    source2.direction.phi = [0, 360 * deg]

    # Physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    # Hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.attached_to = crystal.name
    hc.authorize_repeated_volumes = True
    hc.root_output.write_to_disk = False
    hc.attributes = [
        "EventID",
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # Singles
    sc = sim.add_actor("DigitizerAdderActor", "Singles_before_deadtime")
    sc.attached_to = hc.attached_to
    sc.authorize_repeated_volumes = True
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWinnerPosition"
    sc.output_filename = root_filename

    # Dead time
    dt = sim.add_actor("DigitizerDeadTimeActor", "Singles_after_deadtime")
    dt.input_digi_collection = sc.name
    dt.group_volume = crystal.name
    dt.authorize_repeated_volumes = True
    dt.dead_time = 2000.0 * ns
    dt.clear_every = 1e4
    dt.output_filename = root_filename

    # Timing
    run_duration = 0.0005 * sec
    num_runs = 2
    sim.run_timing_intervals = [
        [2 * r * run_duration, (2 * r + 1) * run_duration] for r in range(num_runs)
    ]

    return (sim, dt, root_filename)
