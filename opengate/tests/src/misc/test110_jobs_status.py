#!/usr/bin/env python3

from pathlib import Path
from click.testing import CliRunner
import opengate as gate
from opengate.bin.opengate_jobs_status import go as jobs_status_cli
from opengate.jobs import create_split_jobs, get_jobs_status
from opengate.tests import utility


def main():
    paths = utility.get_default_test_paths(__file__, None, output_folder="test110")

    sim = gate.Simulation()
    sim.output_dir = paths.output

    box = sim.add_volume("Box", "box")
    box.size = [10.0, 10.0, 10.0]

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.n = [100, 50]
    source.direction.type = "iso"
    source.energy.mono = 1.0 * gate.g4_units.MeV

    sim.run_timing_intervals = [[0.0, 1.0], [1.0, 2.0]]

    # Create split jobs
    split_root_folder = create_split_jobs(
        sim, number_of_jobs=2, split_path=paths.output, policy="split_time"
    )

    # 1. Test get_jobs_status on folder
    status = get_jobs_status(split_root_folder)

    assert status["number_of_jobs"] == 2
    assert status["summary_counts"]["ready"] == 2

    # 3. Test CLI command execution
    runner = CliRunner()
    result = runner.invoke(jobs_status_cli, [str(split_root_folder), "-v"])
    assert result.exit_code == 0
    assert "Manifest file" in result.output
    assert "job0001" in result.output
    assert "job0002" in result.output

    # Test passing manifest file directly
    manifest_file = split_root_folder / "jobs_manifest.json"
    result_manifest = runner.invoke(jobs_status_cli, [str(manifest_file)])
    assert result_manifest.exit_code == 0
    assert "Root directory" in result_manifest.output

    utility.test_ok(True)


if __name__ == "__main__":
    main()
