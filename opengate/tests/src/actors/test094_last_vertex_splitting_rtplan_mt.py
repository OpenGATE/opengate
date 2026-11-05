"""Compare water dose with/without LV at four sigma, in mono and MT."""

from pathlib import Path
import tempfile

import itk
import numpy as np
import uproot
from opengate.tests import utility

from test094_last_vertex_splitting_rtplan_helpers import build_simulation, load_fixture


if __name__ == "__main__":
    repetitions = 8
    with tempfile.TemporaryDirectory(prefix="test094-rtplan-") as scratch:
        phsp = Path(scratch) / "fixture.root"
        # Each interval receives the same primary population in all configurations.
        with uproot.recreate(phsp) as output:
            output.mktree("phsp_actor", {
                key: np.tile(value, 32 * repetitions)
                for key, value in load_fixture()["phsp"].items()
            })

        for threads in (1, 4):
            means, variances = [], []
            for use_lv in (False, True):
                sim = build_simulation(use_lv, repetitions)
                sim.number_of_threads = threads
                sim.random_seed = 20261105 + int(use_lv)
                sim.output_dir = Path(scratch) / f"{threads}_{use_lv}"
                sim.check_volumes_overlap = False
                source = sim.get_source_user_info("phsp_source_global")
                source.phsp_file = str(phsp)
                source.batch_size = 1024
                source.number_of_primaries = [128] * (4 * repetitions)
                source.entry_start = (0 if threads == 1 else
                    source.generate_entry_start_list(512 * repetitions, threads, offset=0))
                sim.run(start_new_process=True)

                stats = sim.actor_manager.actors["stats"]
                replays = 0
                if use_lv:
                    lv = sim.actor_manager.actors["vertexSplittingActor"].user_output.last_vertex_output
                    replays = lv.number_of_replayed_events
                    assert replays > 0
                    assert replays == lv.number_of_actor_classified_replayed_events
                assert stats.counts.runs == 4 * repetitions * threads
                assert stats.counts.events == 512 * repetitions + replays

                dose = sim.actor_manager.actors["dose"].dose
                maps = np.asarray([
                    itk.array_from_image(dose.get_data(which=i))
                    for i in range(4 * repetitions)
                ])
                # Keep all correlated replays inside their original four-interval batch.
                batches = maps.reshape(repetitions, 4, *maps.shape[1:]).sum(axis=1)
                assert np.isfinite(batches).all() and np.any(batches > 0)
                means.append(batches.mean(axis=0))
                variances.append(batches.var(axis=0, ddof=1) / repetitions)

            difference = means[1] - means[0]
            sigma = np.sqrt(variances[0] + variances[1])
            scored = (means[0] > 0) | (means[1] > 0)
            # Empty voxels agree exactly; a nonzero difference with zero sigma fails.
            z = np.divide(np.abs(difference), sigma,
                          out=np.where(difference == 0, 0., np.inf), where=sigma > 0)
            assert np.any(scored)
            maximum = z[scored].max()
            print(f"{threads} thread(s): max |Z| = {maximum:.2f}, "
                  f"{np.count_nonzero(z[scored] > 4)}/{scored.sum()} voxels above 4 sigma")
            assert maximum <= 4, "Water dose with/without LV differs by more than 4 sigma"

    utility.test_ok(True)
