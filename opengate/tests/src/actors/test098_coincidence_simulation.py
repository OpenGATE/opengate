import opengate as gate
import opengate.contrib.pet.philipsvereos as vereos


def create_simulation(paths, num_threads):

    root_filename = paths.output / "output_singles.root"

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s

    # options
    sim = gate.Simulation()
    sim.number_of_threads = num_threads
    sim.random_seed = 1234
    sim.output_dir = paths.output
    sim.verbose_level = gate.logger.NONE

    # world
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]
    world.material = "G4_AIR"

    # Pet
    pet = vereos.add_pet(sim, "pet")
    crystal = sim.volume_manager.get_volume("pet_crystal")

    # Point source
    source = sim.add_source("GenericSource", "source")
    source.particle = "back_to_back"
    source.activity = 1e6 * Bq / sim.number_of_threads
    source.position.type = "point"
    source.position.translation = [0 * cm, 0 * cm, 0 * cm]
    source.direction.type = "iso"

    # Hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", "hits")
    hc.attached_to = crystal.name
    hc.authorize_repeated_volumes = True
    hc.attributes = [
        "EventID",
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # Singles
    sc = sim.add_actor("DigitizerAdderActor", "singles")
    sc.attached_to = hc.attached_to
    sc.authorize_repeated_volumes = True
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.group_volume = crystal.name
    sc.output_filename = root_filename

    # Coincidence sorter
    cc = sim.add_actor("CoincidenceSorterActor", "coincidences")
    cc.input_digi_collection = sc.name
    cc.window = 1e-9 * sec
    cc.output_filename = root_filename

    run_duration = 0.001 * sec
    num_runs = 2
    sim.run_timing_intervals = [
        [2 * r * run_duration, (2 * r + 1) * run_duration] for r in range(num_runs)
    ]

    return (sim, cc, root_filename)
