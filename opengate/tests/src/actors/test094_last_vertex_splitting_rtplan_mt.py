"""Compare LV water dose in mono and MT at four sigma."""

from pathlib import Path
import tempfile

import itk
import numpy as np
import uproot
from opengate.tests import utility

from test094_last_vertex_splitting_rtplan_helpers import build_simulation, load_fixture


if __name__ == "__main__":
    repetitions = 8
    is_ok = True
    with tempfile.TemporaryDirectory(prefix="test094-rtplan-") as scratch:
        phsp = Path(scratch) / "fixture.root"
        # Each interval receives the same primary population in all configurations.
        with uproot.recreate(phsp) as output:
            output.mktree("phsp_actor", {
                key: np.tile(value, 32 * repetitions)
                for key, value in load_fixture()["phsp"].items()
            })

        means, variances = [], []
        for threads in (1, 4):
            sim = build_simulation(repetitions)
            sim.number_of_threads = threads
            sim.random_seed = 20261105 + int(threads == 4)
            sim.output_dir = Path(scratch) / str(threads)
            sim.check_volumes_overlap = False
            source = sim.get_source_user_info("phsp_source_global")
            source.phsp_file = str(phsp)
            source.batch_size = 1024
            source.number_of_primaries = [128] * (4 * repetitions)
            source.entry_start = (0 if threads == 1 else
                source.generate_entry_start_list(512 * repetitions, threads, offset=0))
            sim.run(start_new_process=True)

            stats = sim.actor_manager.actors["stats"]
            lv = sim.actor_manager.actors["vertexSplittingActor"].user_output.last_vertex_output
            replays = lv.number_of_replayed_events
            is_ok = (replays > 0
                     and replays == lv.number_of_actor_classified_replayed_events
                     and stats.counts.runs == 4 * repetitions * threads
                     and stats.counts.events == 512 * repetitions + replays
                     and is_ok)

            dose = sim.actor_manager.actors["dose"].dose
            maps = np.asarray([
                itk.array_from_image(dose.get_data(which=i))
                for i in range(4 * repetitions)
            ])
            # Keep all correlated replays inside their original four-interval batch.
            batches = maps.reshape(repetitions, 4, *maps.shape[1:]).sum(axis=1)
            is_ok = bool(np.isfinite(batches).all() and np.any(batches > 0) and is_ok)
            means.append(batches.mean(axis=0))
            variances.append(batches.var(axis=0, ddof=1) / repetitions)

        difference = means[1] - means[0]
        sigma = np.sqrt(variances[0] + variances[1])
        scored = (means[0] > 0) | (means[1] > 0)
        # Empty voxels agree exactly; a nonzero difference with zero sigma fails.
        z = np.divide(np.abs(difference), sigma,
                      out=np.where(difference == 0, 0., np.inf), where=sigma > 0)
        maximum = z[scored].max() if np.any(scored) else np.inf
        print(f"LV mono vs 4 threads: max |Z| = {maximum:.2f}, "
              f"{np.count_nonzero(z[scored] > 4)}/{scored.sum()} voxels above 4 sigma")
        is_ok = bool(is_ok and np.isfinite(z[scored]).all() and maximum <= 4)

    utility.test_ok(is_ok)
