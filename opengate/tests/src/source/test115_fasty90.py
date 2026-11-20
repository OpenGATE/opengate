#!/usr/bin/env python3
"""Simulation regression for native fastY90 emission and activity scheduling."""

import numpy as np
import opengate as gate
import opengate_core as g4
from scipy.spatial.transform import Rotation
import uproot

from opengate.tests import utility


def make_simulation(output, threads=1):
    sim = gate.Simulation()
    sim.output_dir = output
    sim.random_seed = 29173
    sim.number_of_threads = threads
    sim.world.size = [200 * gate.g4_units.mm] * 3
    # Vacuum isolates primary generation from transport and secondary emission.
    sim.world.material = "G4_Galactic"
    source = sim.add_source("FastY90Source", "y90")
    source.min_brem_energy = 59 * gate.g4_units.keV
    source.positron_probability = 0.02
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = sim.world
    phsp.steps_to_store = "first"
    phsp.attributes = [
        "TrackID",
        "PDGCode",
        "EventPosition",
        "EventDirection",
        "EventKineticEnergy",
        "GlobalTime",
        "Weight",
    ]
    phsp.output_filename = "primaries.root"
    return sim, source, stats, phsp


def read_primaries(actor):
    data = uproot.open(actor.get_output_path())["phsp"].arrays(library="np")
    return {key: value[data["TrackID"] == 1] for key, value in data.items()}


def check_fixed_count(output, threads, tables):
    sim, source, stats, phsp = make_simulation(output, threads)
    source.number_of_primaries = 20003
    holder = sim.add_volume("Box", "holder")
    holder.material = "G4_Galactic"
    holder.size = [60 * gate.g4_units.mm] * 3
    holder.translation = [10, 20, 30]
    holder.rotation = Rotation.from_euler("z", 90, degrees=True).as_matrix()
    source.attached_to = holder
    source.position.translation = [3, 4, 5]
    source.weight = 2
    sim.run(start_new_process=True)
    data = read_primaries(phsp)
    assert stats.counts.events == 20003
    assert len(data["PDGCode"]) == 20003
    is_pos = data["PDGCode"] == -11
    assert np.all(np.isin(data["PDGCode"], [-11, 22]))
    brem_yield = tables["mEnergyTable"][5:].sum()
    fraction = 0.02 / (0.02 + brem_yield)
    assert abs(is_pos.mean() - fraction) < 6 * np.sqrt(
        fraction * (1 - fraction) / len(is_pos)
    )
    position = np.column_stack([data[f"EventPosition_{axis}"] for axis in "XYZ"])
    direction = np.column_stack([data[f"EventDirection_{axis}"] for axis in "XYZ"])
    center = (
        np.asarray(holder.translation) + holder.rotation @ source.position.translation
    )
    np.testing.assert_allclose(
        position[is_pos], np.broadcast_to(center, position[is_pos].shape), atol=1e-6
    )
    displacement = position[~is_pos] - center
    radius = np.linalg.norm(displacement, axis=1)
    assert np.all((radius > 0) & (radius < 12))
    energy = data["EventKineticEnergy"]
    assert np.all((energy[~is_pos] >= 0.05) & (energy[~is_pos] < 2))
    assert np.all((energy[is_pos] >= 0) & (energy[is_pos] <= 0.737))
    np.testing.assert_allclose(np.linalg.norm(direction, axis=1), 1, atol=1e-6)
    np.testing.assert_allclose(data["Weight"], 2)
    # Check the direction relation after geometry transforms. The expected
    # cosine integrates each uniform one-degree bin of the legacy angle table.
    angles = np.arange(181) * np.pi / 180
    cos_by_bin = np.diff(np.sin(angles)) / (np.pi / 180)
    angle_weights = tables["mAngleTable"]
    mean_cos = angle_weights @ cos_by_bin / angle_weights.sum(axis=1)
    rows = np.minimum((energy[~is_pos] / 0.02).astype(int), 99)
    observed_cos = np.sum(displacement * direction[~is_pos], axis=1) / radius
    assert abs(np.mean(observed_cos - mean_cos[rows])) < 0.03


def check_activity(output, tables, threads=1):
    sim, source, stats, phsp = make_simulation(output, threads=threads)
    source.activity = 1e6 * gate.g4_units.Bq
    source.half_life = 1 * gate.g4_units.s
    sim.run(start_new_process=True)
    total_yield = tables["mEnergyTable"][5:].sum() + 0.02
    expected = 1e6 * total_yield * 0.5 / np.log(2)
    assert abs(stats.counts.events - expected) < 6 * np.sqrt(expected)
    data = read_primaries(phsp)
    times = data["GlobalTime"] / gate.g4_units.s
    assert np.all((times >= 0) & (times < 1))
    # Half-life scheduling must also preserve the shape of the time distribution.
    fraction_first_half = (1 - 2**-0.5) / 0.5
    assert abs(np.mean(times < 0.5) - fraction_first_half) < 0.03


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test115")
    tables = g4.GateFastY90Kernel.GetTables()
    check_fixed_count(paths.output / "single", 1, tables)
    check_activity(paths.output / "activity", tables)
    utility.test_ok(True)
