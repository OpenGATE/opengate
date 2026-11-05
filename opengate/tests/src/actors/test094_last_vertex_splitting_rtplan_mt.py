"""Four real RTPlan intervals, full moving LINAC, water target and LV.

Run with the OpenGATE interpreter. Each transport uses a fresh subprocess;
Saved dose/squared arrays are fully read before scratch cleanup. The repeated
PHSP fixture is only suitable for mechanics, not statistical validation.
"""

import json
import hashlib
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from test094_last_vertex_splitting_rtplan_helpers import build_simulation, load_fixture
INTERVALS = load_fixture()['provenance']['intervals']
SEED = 20261105


def transport(output, threads):
    import numpy as np
    import itk
    from unittest.mock import patch

    from opengate.sources.phspsources import PhaseSpaceSource

    sim = build_simulation()
    sim.number_of_threads = threads
    sim.random_seed = SEED
    sim.output_dir = output
    sim.check_volumes_overlap = False
    source = sim.get_source_user_info('phsp_source_global')
    source.phsp_file = str(output.parent / 'fixture.root')
    source.batch_size = 1024
    source.number_of_primaries = np.full(4, 128, dtype=int)
    source.entry_start = (0 if threads == 1 else
                         source.generate_entry_start_list(512, threads, offset=0))
    # Read native counters while source instances are still alive.
    original_gather = PhaseSpaceSource.gather_outputs
    counts = {}
    per_run = []
    from opengate.actors.miscactors import SimulationStatisticsActor
    end_run = SimulationStatisticsActor.EndOfRunActionMasterThread

    def record_run(self, run_index):
        result = end_run(self, run_index)
        data = self.GetCountsCurrentRun()
        per_run.append(dict(run=int(run_index), events=int(data['events']),
                            originals=sum(int(s.GetRunGeneratedEvents())
                                          for s in source.g4_thread_sources),
                            cumulative_replays=sum(int(s.GetTotalReplayedEvents())
                                for s in sim.get_source_user_info('source_vertex').g4_thread_sources)))
        return result

    def gather_original(self, sources):
        counts['originals_per_worker'] = [int(s.GetTotalGeneratedEvents()) for s in sources]
        return original_gather(self, sources)

    started = time.perf_counter()
    with patch.object(PhaseSpaceSource, 'gather_outputs', gather_original), \
            patch.object(SimulationStatisticsActor, 'EndOfRunActionMasterThread', record_run):
        sim.run()
    counts['run_wall_seconds'] = time.perf_counter() - started
    stats = sim.actor_manager.actors['stats'].counts
    lv = sim.actor_manager.actors['vertexSplittingActor'].user_output.last_vertex_output
    counts.update(threads=threads, seed=SEED, intervals=INTERVALS, per_run=per_run,
                  events=int(stats.events), runs=int(stats.runs),
                  tracks=int(stats.tracks), steps=int(stats.steps),
                  replays=int(lv.number_of_replayed_events),
                  classified_replays=int(lv.number_of_actor_classified_replayed_events))
    arrays = {}
    for name in ('dose',):
        actor = sim.actor_manager.actors[name]
        for kind in ('dose', 'dose_squared'):
            image = getattr(actor, kind).get_data()
            arrays[f'{name}_{kind}'] = itk.array_from_image(image)
    np.savez(output / 'scores.npz', **arrays)
    (output / 'counts.json').write_text(json.dumps(counts, indent=2))


class ShortRunsTest(unittest.TestCase):
    def test_four_intervals_mono_and_multi(self):
        import numpy as np

        records = []
        scores = []
        with tempfile.TemporaryDirectory(prefix='vrt-short-runs-') as scratch:
            import uproot
            fixture_data = load_fixture()
            rows = {key: np.asarray(value) for key, value in fixture_data['phsp'].items()}
            selected_rows = np.asarray(fixture_data['provenance']['selected_phsp_rows'])
            with uproot.recreate(Path(scratch) / 'fixture.root') as fixture:
                fixture.mktree('phsp_actor', {key: np.tile(value, 32)
                                            for key, value in rows.items()})
            fixture_hash = hashlib.sha256((Path(scratch) / 'fixture.root').read_bytes()).hexdigest()
            for threads in (1, 4):
                output = Path(scratch) / str(threads)
                output.mkdir()
                process = subprocess.Popen(
                    [sys.executable, '-u', str(Path(__file__).resolve()),
                     '--worker', str(output), str(threads)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True)
                lines, event_times = [], {}

                def read_trace():
                    run = None
                    for line in process.stdout:
                        now = time.perf_counter()
                        lines.append(line)
                        match = re.search(r'GateDebugActor::BeginOfRunAction\s+(\d+)', line)
                        if match:
                            run = int(match[1])
                        if run is not None and 'GateDebugActor::BeginOfEventAction' in line:
                            event_times.setdefault(run, {})['first'] = event_times.get(run, {}).get('first', now)
                        if run is not None and 'GateDebugActor::EndOfEventAction' in line:
                            event_times.setdefault(run, {})['last'] = now

                reader = threading.Thread(target=read_trace)
                reader.start()
                try:
                    process.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise
                finally:
                    reader.join()
                    process.stdout.close()
                self.assertEqual(process.returncode, 0, ''.join(lines))
                record = json.loads((output / 'counts.json').read_text())
                self.assertEqual(sorted(event_times), list(range(4)), ''.join(lines))
                record['event_spans_seconds'] = [event_times[r]['last'] - event_times[r]['first'] for r in range(4)]
                record['transition_gaps_seconds'] = [event_times[r]['first'] - event_times[r-1]['last'] for r in range(1, 4)]
                # Pipe arrival times of flushed native traces are diagnostic,
                # not precise profiling. Never make CI depend on scheduler load.
                record['short_runs_condition_met'] = max(record['event_spans_seconds']) < min(record['transition_gaps_seconds'])
                records.append(record)
                with np.load(output / 'scores.npz') as data:
                    scores.append({key: data[key].copy() for key in data.files})
                self.assertEqual(sum(record['originals_per_worker']), 512)
                self.assertEqual(record['runs'], 4 * threads)
                self.assertEqual(record['replays'], record['classified_replays'])
                self.assertEqual(record['events'], 512 + record['replays'])
                self.assertGreater(record['replays'], 0, 'Fixture did not exercise LV replay')
                self.assertEqual([row['run'] for row in record['per_run']], list(range(4)))
                previous_replays = 0
                for row in record['per_run']:
                    self.assertEqual(row['originals'], 128)
                    self.assertEqual(row['events'], 128 + row['cumulative_replays'] - previous_replays)
                    previous_replays = row['cumulative_replays']
                self.assertEqual(previous_replays, record['replays'])
                for array in scores[-1].values():
                    self.assertTrue(np.isfinite(array).all())
                self.assertGreater(float(scores[-1]['dose_dose'].sum()), 0)
            comparison = {
                key: dict(identical=bool(np.array_equal(scores[0][key], scores[1][key])),
                          mono_sum=float(scores[0][key].sum()),
                          multi_sum=float(scores[1][key].sum()),
                          max_absolute_difference=float(np.max(np.abs(scores[0][key] - scores[1][key]))))
                for key in scores[0]}
            print(json.dumps({'runs': records, 'score_comparison': comparison,
                              'selected_phsp_rows': selected_rows.tolist(),
                              'fixture_sha256': fixture_hash,
                              'rtplan_sha256': fixture_data['provenance']['rtplan_sha256']}, indent=2))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--worker':
        transport(Path(sys.argv[2]), int(sys.argv[3]))
    else:
        from opengate.tests import utility

        result = unittest.main(exit=False)
        utility.test_ok(result.result.wasSuccessful())
