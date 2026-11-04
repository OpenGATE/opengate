"""Build/run the LV native state regression using an existing core build.

Run with the developer Python. Artifacts go to a fresh --output-dir; no core
binary is replaced. This exercises native callbacks, not Geant4 transport MT.
"""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sysconfig


def main():
    core = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path,
                        default=core / 'build/cmake.linux-x86_64-cpython-3.11')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    build = args.build_dir.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    entries = json.loads((build / 'compile_commands.json').read_text())
    entry = next(e for e in entries if e['file'].endswith(
        '/GateLastVertexInteractionSplittingActor.cpp'))
    command = shlex.split(entry['command'])
    command[command.index('-o') + 1] = str(output / 'test.o')
    command[command.index('-c') + 1] = str(core / 'tests/test_lastvertex_worker_state.cpp')
    commands = [command]
    link = shlex.split((build / 'CMakeFiles/opengate_core.dir/link.txt').read_text())
    link.remove('-shared')
    link[link.index('-o') + 1] = str(output / 'test_lastvertex_worker_state')
    link.extend([str(output / 'test.o'),
                 str(Path(sysconfig.get_config_var('LIBDIR')) /
                     sysconfig.get_config_var('LDLIBRARY'))])
    commands.extend([link, [str(output / 'test_lastvertex_worker_state')]])
    (output / 'commands.json').write_text(json.dumps(commands, indent=2))
    for command in commands:
        subprocess.run(command, cwd=build, check=True)


if __name__ == '__main__':
    main()
