"""Self-contained moving-LINAC fixture for the short Last Vertex MT test."""

from pathlib import Path
import json

import numpy as np
import opengate as gate
from opengate.contrib.linacs import elektaversa as versa

FIXTURE = Path(__file__).with_name('test094_last_vertex_splitting_rtplan_fixture.json')


def load_fixture():
    return json.loads(FIXTURE.read_text())


def build_simulation(use_lv, repetitions):
    plan = {key: np.concatenate([value] * repetitions)
            for key, value in load_fixture()['plan'].items()}
    sim = gate.Simulation()
    sim.verbose_level = 'WARNING'
    sim.running_verbose_level = 0
    sim.world.size = [3000, 3000, 3000]
    sim.world.material = 'G4_AIR'

    linac = versa.add_linac(sim, 'linac_box', sad=1000)
    bias = versa.add_patient_dependent_linac_box(sim, linac.name)
    leaves = versa.add_mlc(sim, linac.name, bias.name)
    jaws = versa.add_jaws(sim, linac.name, bias.name)
    versa.add_linac_shielding(sim, linac.name, bias.name, lead_thickness=4)
    versa.set_time_intervals_from_rtplan(sim, plan)
    versa.set_linac_head_motion(sim, linac.name, jaws, leaves, plan, sad=1000)

    plane = sim.add_volume('Box', 'plan')
    plane.mother = linac.name
    plane.material = 'G4_AIR'
    plane.size = [linac.size[0], linac.size[1], 0.1 * gate.g4_units.nm]
    plane.translation = [0, 0, linac.size[2] / 2 - 300.1 + 0.5 * gate.g4_units.nm]
    source = versa.add_phase_space_source(sim, plane.name)
    source.position_key = 'PrePositionLocal'
    source.direction_key = 'PreDirectionLocal'
    source.weight_key = 'Weight'
    source.PDGCode_key = 'PDGCode'

    patient = sim.add_volume('Box', 'patient')
    patient.size = [640, 320, 440]
    patient.material = 'G4_WATER'
    dose = sim.add_actor('DoseActor', 'dose')
    dose.attached_to = patient.name
    dose.size = [16, 8, 11]
    dose.spacing = [40, 40, 40]
    dose.output_coordinate_system = 'local'
    dose.hit_type = 'random'
    dose.dose.active = True
    dose.write_to_disk = False
    dose.dose.keep_data_per_run = True

    kill = sim.add_actor('KillNonInteractingParticleForLVActor', 'kill_non_int_actor')
    kill.attached_to = bias.name
    if use_lv:
        lv = sim.add_actor('LastVertexInteractionSplittingActor', 'vertexSplittingActor')
        lv.attached_to = bias.name
        lv.splitting_factor = 50
        lv.batch_size = 500
        lv.nb_of_max_batch_per_event = 300
        lv.angular_acceptance.target_volumes = [patient.name]
        lv.angular_acceptance.policy = 'Rejection'
        lv.angular_acceptance.skip_policy = 'SkipEvents'
        lv.angular_acceptance.enable_intersection_check = True
        sim.add_source('LastVertexSource', 'source_vertex')
    sim.physics_manager.physics_list_name = 'G4EmStandardPhysics_option3'
    sim.physics_manager.set_production_cut('world', 'electron', 1000 * gate.g4_units.m)
    sim.physics_manager.set_production_cut('patient', 'electron', 0.05)
    sim.g4_commands_before_init.extend(['/process/em/UseGeneralProcess false',
                                       '/process/eLoss/CSDARange true'])
    sim.add_actor('SimulationStatisticsActor', 'stats')
    return sim
