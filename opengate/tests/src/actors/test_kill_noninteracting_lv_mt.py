"""Small standalone transports for the LV-specific kill actor (no test datasets)."""
import argparse
import json
from pathlib import Path
import opengate as gate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--threads', type=int, required=True)
    parser.add_argument('--birth', choices=['outside', 'inside', 'world'], default='outside')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    sim = gate.Simulation()
    sim.output_dir = args.output_dir
    sim.number_of_threads = args.threads
    sim.random_seed = 20261104
    sim.world.size = [1000,1000,1000]
    sim.world.material = 'G4_Galactic'
    box = sim.add_volume('Box', 'box')
    box.size = [20,20,20]
    box.material = 'G4_Galactic'
    source = sim.add_source('GenericSource', 'source')
    source.particle = 'gamma'
    source.energy.mono = 1 * gate.g4_units.MeV
    source.position.type = 'point'
    source.position.translation = [0,0,-50] if args.birth != 'inside' else [0,0,0]
    source.direction.type = 'momentum'
    source.direction.momentum = [0,0,1]
    source.number_of_primaries = [64,64]
    sim.run_timing_intervals = [[0,1], [1,2]]
    actor = sim.add_actor('KillNonInteractingParticleForLVActor', 'kill_lv')
    actor.attached_to = 'world' if args.birth == 'world' else box.name
    stats = sim.add_actor('SimulationStatisticsActor', 'stats')
    sim.physics_manager.physics_list_name = 'G4EmStandardPhysics_option3'
    sim.run()
    expected = 128 if args.birth == 'outside' else 0
    counted = actor.number_of_killed_particles
    output_count = actor.user_output.kill_non_interacting_particles.number_of_killed_particles
    assert counted == expected, (counted, expected)
    assert output_count == expected, (output_count, expected)
    result = dict(threads=args.threads, birth=args.birth, killed=counted,
                  output_killed=output_count, expected=expected)
    (args.output_dir/'verification.json').write_text(json.dumps(result, indent=2))
    print('PASS standalone MT kill actor:', result)


if __name__ == '__main__':
    main()
