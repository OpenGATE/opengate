import math
from scipy.spatial.transform import Rotation

import opengate as gate


def protonct(output,
             projections=720,
             protons_per_projection=1000,
             seed=None,
             visu=False,
             verbose=False):

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
    sim.random_seed = "auto" if seed is None else seed
    sim.check_volumes_overlap = False
    sim.visu = visu
    sim.visu_type = "vrml"
    sim.g4_verbose = False
    sim.progress_bar = verbose
    sim.number_of_threads = 1

    sim.run_timing_intervals = [[j * sec, (j + 1) * sec]
                                for j in range(projections)]

    # Misc
    yellow = [1, 1, 0, 0.5]
    blue = [0, 0, 1, 0.5]

    # Geometry
    sim.volume_manager.add_material_database(gate.utility.get_contrib_path() /
                                             "GateMaterials.db")
    sim.world.material = "Vacuum"
    sim.world.size = [4 * m, 4 * m, 4 * m]
    sim.world.color = [0, 0, 0, 0]

    # Phantom

    def add_spiral(sim):
        # Mother of all
        spiral = sim.add_volume("Tubs", name="Spiral")
        spiral.rmin = 0 * cm
        spiral.rmax = 10 * cm
        spiral.dz = 40 * cm
        spiral.material = "Water"
        spiral.color = blue
        spiral.rotation = Rotation.from_euler("yz", [90, 90],
                                              degrees=True).as_matrix()

        # Spiral rotation
        tr, rot = gate.geometry.utility.volume_orbiting_transform(
            "y", 0, 360, projections, spiral.translation, spiral.rotation)
        spiral.add_dynamic_parametrisation(translation=tr, rotation=rot)

        # Spiral inserts
        sradius = 4
        radius = list(range(0, 100 - sradius // 2, sradius))
        sangle = 139
        angles = [
            math.radians(a) for a in range(0, sangle * len(radius), sangle)
        ]
        posx = [radius[i] * math.cos(angles[i]) for i in range(len(radius))]
        posy = [radius[i] * math.sin(angles[i]) for i in range(len(radius))]

        def add_spiral_insert(
            sim,
            mother,
            name,
            rmin=0 * mm,
            rmax=1 * mm,
            dz=40 * cm,
            material="Aluminium",
            translation=None,
            color=None,
        ):

            if translation is None:
                translation = [0 * mm, 0 * mm, 0 * mm]

            if color is None:
                color = yellow

            spiral_insert = sim.add_volume("Tubs", name=name)
            spiral_insert.mother = mother.name
            spiral_insert.rmin = rmin
            spiral_insert.rmax = rmax
            spiral_insert.dz = dz
            spiral_insert.material = material
            spiral_insert.translation = translation
            spiral_insert.color = color

        for i in range(len(radius)):
            add_spiral_insert(
                sim,
                spiral,
                f"SpiralInsert{i:02d}",
                translation=[posx[i] * mm, posy[i] * mm, 0],
            )

    add_spiral(sim)

    # Beam
    source = sim.add_source("GenericSource", "mybeam")
    source.particle = "proton"
    source.energy.mono = 200 * MeV
    source.energy.type = "mono"
    source.position.type = "box"
    source.position.size = [16 * mm, 1 * nm, 1 * nm]
    source.position.translation = [0, 0, -1060 * mm]
    source.direction.type = "focused"
    source.direction.focus_point = [0, 0, -1000 * mm]

    if sim.visu:
        # For visualisation speed, the number of particle is decreased
        source.activity = 10 * Bq
    else:
        source.activity = protons_per_projection * Bq

    # Physics list
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"

    # Phase spaces

    def add_detector(sim, name, translation):
        plane = sim.add_volume("Box", "PlanePhaseSpace" + name)
        plane.size = [400 * mm, 400 * mm, 1 * nm]
        plane.translation = translation
        plane.material = "Vacuum"
        plane.color = yellow

        phase_space = sim.add_actor("PhaseSpaceActor", "PhaseSpace" + name)
        phase_space.attached_to = plane.name
        phase_space.attributes = [
            "RunID",
            "EventID",
            "TrackID",
            "KineticEnergy",
            "LocalTime",
            "Position",
            "Direction",
        ]
        phase_space.output_filename = f"{output}/PhaseSpace{name}.root"

        ps_filter = sim.add_filter("ParticleFilter", "Filter" + name)
        ps_filter.particle = "proton"
        phase_space.filters.append(ps_filter)

    add_detector(sim, "In", [0, 0, -110 * mm])
    add_detector(sim, "Out", [0, 0, 110 * mm])

    # Particle stats
    stat = sim.add_actor("SimulationStatisticsActor", "stat")
    stat.output_filename = f"{output}/protonct.txt"

    sim.run()
