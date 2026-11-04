"""Standalone transport of the LV-specific particle-name kill actor."""
import argparse
import json
from pathlib import Path
import opengate as gate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--threads', type=int, required=True)
    parser.add_argument('--particle', default='gamma')
    parser.add_argument('--unselected', action='store_true')
    parser.add_argument('--world', action='store_true')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    sim = gate.Simulation()
    sim.output_dir = args.output_dir
    sim.number_of_threads = args.threads
    sim.random_seed = 20261104
    sim.world.size = [1000,1000,1000]
    sim.world.material = 'G4_Galactic'
    box = sim.add_volume('Box','box')
    box.size = [20,20,20]
    box.material = 'G4_Galactic'
    source = sim.add_source('GenericSource','source')
    source.particle = args.particle
    source.energy.mono = gate.g4_units.MeV
    source.position.type = 'point'
    source.position.translation = [0,0,-50]
    source.direction.type = 'momentum'
    source.direction.momentum = [0,0,1]
    source.number_of_primaries = [64,64]
    sim.run_timing_intervals = [[0,1],[1,2]]
    actor = sim.add_actor('KillAccordingParticleNameLVActor','kill_name_lv')
    actor.attached_to = 'world' if args.world else box.name
    actor.particles_name_to_kill = [] if args.unselected else [args.particle]
    sim.physics_manager.physics_list_name = 'G4EmStandardPhysics_option3'
    sim.run()
    expected = 0 if args.unselected or args.world else 128
    actual = actor.GetNumberOfKilledParticles()
    assert actual == expected, (actual, expected)
    assert actor.number_of_killed_particles == expected
    result = dict(threads=args.threads, particle=args.particle,
                  unselected=args.unselected, world=args.world,
                  killed=actual, expected=expected)
    (args.output_dir/'verification.json').write_text(json.dumps(result,indent=2))
    print('PASS particle-name MT transport:',result)


if __name__ == '__main__':
    main()
