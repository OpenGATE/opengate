#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantoms.nemaiec as gate_iec
import gatetools as gt
import itk
import json
import opengate.contrib.pet.philipsvereos as pet_vereos
from opengate.tests import utility
from box import Box


def create_pet_simulation(sim, param):
    # units
    mm = gate.g4_units.mm
    m = gate.g4_units.m
    cm3 = gate.g4_units.cm3
    Bq = gate.g4_units.Bq
    BqmL = Bq / cm3

    # main parameters
    sim.check_volumes_overlap = True
    sim.number_of_threads = 1
    # sim.random_seed = 123456
    param.ac = param.activity_Bqml * BqmL / sim.number_of_threads
    if sim.visu:
        param.ac = 1 * BqmL
        sim.number_of_threads = 1

    # world size
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]
    world.material = "G4_AIR"

    # phantom ?
    if param.use_gaga:
        param.phantom_type = None
    if param.phantom_type == "analytic":
        add_analytical_phantom(sim, param)
    if param.phantom_type == "vox":
        add_voxelized_phantom(sim, param)

    sim.physics_manager.set_production_cut(
        volume_name="world", particle_name="gamma", value=1 * m
    )
    sim.physics_manager.set_production_cut(
        volume_name="world", particle_name="positron", value=1 * m
    )
    sim.physics_manager.set_production_cut(
        volume_name="world", particle_name="electron", value=1 * m
    )

    if param.phantom_type == "analytic" or param.phantom_type == "vox":
        sim.physics_manager.set_production_cut(
            volume_name="iec", particle_name="gamma", value=0.1 * mm
        )
        sim.physics_manager.set_production_cut(
            volume_name="iec", particle_name="positron", value=0.1 * mm
        )
        sim.physics_manager.set_production_cut(
            volume_name="iec", particle_name="electron", value=0.1 * mm
        )

    # PET ?
    if param.use_pet:
        add_pet(sim, param)
        sim.physics_manager.set_production_cut(
            volume_name="pet", particle_name="gamma", value=1 * mm
        )
        sim.physics_manager.set_production_cut(
            volume_name="pet", particle_name="positron", value=1 * mm
        )
        sim.physics_manager.set_production_cut(
            volume_name="pet", particle_name="electron", value=1 * mm
        )

    # physic list
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = False
    # p.apply_cuts = True

    # source ? FIXME
    if param.use_gaga:
        add_gaga_source(sim, param)
    else:
        if param.source_type == "analytic":
            add_analytical_source(sim, param)
        else:
            add_voxelized_source(sim, param)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True


def add_analytical_phantom(sim, param):
    print("Phantom: IEC analytical")
    gate_iec.add_iec_phantom(sim)


def add_voxelized_phantom(sim, param):
    print("Phantom: IEC voxelized: ", param.iec_vox_mhd)
    iec = sim.add_volume("Image", "iec")
    gate_iec.create_material(sim)
    iec.image = param.iec_vox_mhd
    iec.material = "G4_AIR"
    labels = json.loads(open(param.iec_vox_json).read())
    # labels are not material, we assign the material belows
    # all spheres are water ; central hole is lung ; shell are plastic
    iec.voxel_materials = []
    for l in labels:
        mat = "IEC_PLASTIC"
        if "capillary" in l:
            mat = "G4_WATER"
        if "cylinder_hole" in l:
            mat = "G4_LUNG_ICRP"
        if "interior" in l:
            mat = "G4_WATER"
        if "sphere" in l:
            mat = "G4_WATER"
        if "world" in l:
            mat = "G4_AIR"
        if "shell" in l:
            mat = "IEC_PLASTIC"
        m = [labels[l], labels[l] + 1, mat]
        iec.voxel_materials.append(m)


def add_gaga_source(sim, p):
    if p.source_type == "analytic":
        return add_gaga_source_analytic_condition(sim, p)
    if p.source_type == "vox":
        return add_gaga_source_vox_condition(sim, p)


def add_pet(sim, param):
    # add the pet volume
    pet_vereos.add_pet(sim, "pet")

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    crystal = None
    # get crystal volume by looking for the word crystal in the name
    for k, v in sim.volume_manager.volumes.items():
        if "crystal" in k:
            crystal = v
    hc.mother = crystal.name
    hc.output = ""
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "TrackVolumeCopyNo",
        "PostStepUniqueVolumeID",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # singles collection
    sc = sim.add_actor("DigitizerAdderActor", "Singles")
    sc.mother = crystal.name
    sc.input_digi_collection = "Hits"
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.skip_attributes = ["PreStepUniqueVolumeID", "PreStepUniqueVolumeID"]
    sc.output = param.pet_output


def get_spheres_activity(sim, p):
    # compute spheres param
    spheres_diam = [10, 13, 17, 22, 28, 37]
    ac = p.ac
    spheres_activity_concentration = [ac, ac, ac, ac, ac, ac]

    # unit
    cm3 = gate.g4_units.cm3
    Bq = gate.g4_units.Bq
    BqmL = Bq / cm3

    spheres_centers, spheres_volumes = gate_iec.get_default_sphere_centers_and_volumes()
    spheres_activity_ratio = []
    spheres_activity = []
    for diam, ac, volume, center in zip(
        spheres_diam, spheres_activity_concentration, spheres_volumes, spheres_centers
    ):
        activity = ac * volume
        print(
            f"Sphere {diam}: {str(center):<30} {volume / cm3:7.3f} cm3 "
            f"{activity / Bq:7.0f} Bq  {ac / BqmL:7.1f} BqmL"
        )
        spheres_activity.append(activity)

    total_activity = sum(spheres_activity)
    print(f"Total activity {total_activity / Bq:.0f} Bq")
    for activity in spheres_activity:
        spheres_activity_ratio.append(activity / total_activity)
    print("Activity ratio ", spheres_activity_ratio, sum(spheres_activity_ratio))

    return spheres_activity, spheres_centers, spheres_activity_ratio, spheres_diam


def add_gaga_source_analytic_condition(sim, p):
    # compute spheres param
    (
        spheres_activity,
        spheres_centers,
        spheres_activity_ratio,
        spheres_diam,
    ) = get_spheres_activity(sim, p)
    spheres_radius = [x / 2.0 for x in spheres_diam]
    total_activity = sum(spheres_activity)

    def gen_cond(n):
        n_samples = gate_iec.get_n_samples_from_ratio(n, spheres_activity_ratio)
        # (it is very important to shuffle when several spheres to avoid time artifact)
        cond = gate_iec.generate_pos_spheres(
            spheres_centers, spheres_radius, n_samples, shuffle=True
        )
        return cond

    # GAN source
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    keV = gate.g4_units.keV
    gsource = sim.add_source("GANPairsSource", "gaga")
    gsource.particle = "gamma"
    # no phantom, we consider attached to the world at origin
    gsource.activity = total_activity
    gsource.pth_filename = p.gaga_pth
    gsource.position_keys = ["X1", "Y1", "Z1", "X2", "Y2", "Z2"]
    gsource.direction_keys = ["dX1", "dY1", "dZ1", "dX2", "dY2", "dZ2"]
    gsource.energy_key = ["E1", "E2"]
    gsource.time_key = ["t1", "t2"]
    # time is added to the simulation time
    gsource.relative_timing = True
    gsource.weight_key = None
    # particle are move backward with 10 cm
    gsource.backward_distance = 10 * cm
    # if the kinetic E is below this threshold, we set it to 0
    gsource.energy_min_threshold = 0.1 * keV
    gsource.skip_policy = "ZeroEnergy"
    gsource.batch_size = 1e5
    gsource.verbose_generator = True
    # set the generator and the condition generator
    gen = gate.sources.gansources.GANSourceConditionalPairsGenerator(
        gsource, 210 * mm, gen_cond
    )
    gsource.generator = gen
    gsource.gpu_mode = utility.get_gpu_mode_for_tests()


def add_gaga_source_vox_condition(sim, p):
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    keV = gate.g4_units.keV

    (
        spheres_activity,
        spheres_centers,
        spheres_activity_ratio,
        spheres_diam,
    ) = get_spheres_activity(sim, p)
    total_activity = sum(spheres_activity)

    # GAN source
    gsource = sim.add_source("GANPairsSource", "gaga")
    gsource.particle = "gamma"
    gsource.activity = total_activity
    gsource.pth_filename = p.gaga_pth
    gsource.position_keys = ["X1", "Y1", "Z1", "X2", "Y2", "Z2"]
    gsource.direction_keys = ["dX1", "dY1", "dZ1", "dX2", "dY2", "dZ2"]
    gsource.energy_key = ["E1", "E2"]
    gsource.time_key = ["t1", "t2"]
    # time is added to the simulation time
    gsource.relative_timing = True
    gsource.weight_key = None
    # particle are move backward with 10 cm
    gsource.backward_distance = 10 * cm
    # if the kinetic E is below this threshold, we set it to 0
    gsource.energy_min_threshold = 0.1 * keV
    gsource.skip_policy = "ZeroEnergy"
    gsource.batch_size = 1e5
    gsource.verbose_generator = True

    # set the generator and the condition generator
    voxelized_cond_generator = (
        gate.sources.gansources.VoxelizedSourceConditionGenerator(p.source_vox_mhd)
    )
    gen = gate.sources.gansources.GANSourceConditionalPairsGenerator(
        gsource, 210 * mm, voxelized_cond_generator.generate_condition
    )
    gsource.generator = gen


def add_analytical_source(sim, p):
    print("Source: IEC analytical")
    if p.phantom_type == "vox":
        return add_analytical_source_with_vox_phantom(sim, p)
    gate_iec.add_spheres_sources(
        sim,
        "iec",
        "source",
        [10, 13, 17, 22, 28, 37],
        [p.ac, p.ac, p.ac, p.ac, p.ac, p.ac],  # in BqmL
        verbose=True,
    )
    sources = sim.source_manager.user_info_sources
    for source in sources.values():
        source.particle = "e+"
        source.energy.type = p.radionuclide
        source.direction.type = "iso"


def add_analytical_source_with_vox_phantom(sim, p):
    mm = gate.g4_units.mm
    (
        spheres_activity,
        spheres_centers,
        spheres_activity_ratio,
        spheres_diam,
    ) = get_spheres_activity(sim, p)

    i = 0
    for s in spheres_diam:
        source = sim.add_source("GenericSource", f"source_{i}")
        source.particle = "e+"
        source.energy.type = p.radionuclide
        source.direction.type = "iso"
        source.activity = spheres_activity[i]
        source.position.type = "sphere"
        source.position.radius = s * mm / 2.0
        source.position.translation = spheres_centers[i]
        i += 1


def add_voxelized_source(sim, p):
    Bq = gate.g4_units.Bq
    mm3 = gate.g4_units.mm3
    cm3 = gate.g4_units.cm3
    # compute volume to convert Bqml in Bq
    img = itk.imread(p.source_vox_mhd)
    stats = Box(gt.imageStatistics(img, None, False, 10))
    info = gate.image.get_info_from_image(img)
    vol = stats.sum * info.spacing[0] * info.spacing[1] * info.spacing[2] * mm3
    print(f"Volume source {vol} mm3")
    ac = p.activity_Bqml * vol / cm3
    print(f"Activity {ac} Bq")
    ac = ac * Bq

    # source
    source = sim.add_source("VoxelsSource", "vox")
    source.mother = "iec"
    source.particle = "e+"
    source.energy.type = p.radionuclide
    source.activity = ac
    source.image = p.source_vox_mhd
    source.direction.type = "iso"
    if p.phantom_type == "vox":
        source.position.translation = gate.image.get_translation_between_images_center(
            p.iec_vox_mhd, p.source_vox_mhd
        )
