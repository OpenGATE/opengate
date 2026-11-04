"""Source resolution and legacy output-path regressions; no transport/data IO."""
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

import numpy as np
import opengate as gate
import opengate_core as g4
from opengate.actors.biasingactors import LastVertexInteractionSplittingActor


class VRTSourceAPITest(unittest.TestCase):
    def test_source_replay_count_is_gathered(self):
        self.assertEqual(g4.GateLastVertexSource().GetTotalReplayedEvents(), 0)
        sim = gate.Simulation()
        source = sim.add_source("LastVertexSource", "source_vertex")
        first, second = MagicMock(), MagicMock()
        first.GetTotalReplayedEvents.return_value = 11
        second.GetTotalReplayedEvents.return_value = 22
        source.gather_outputs([first, second])
        self.assertEqual(source.total_replayed_events, 33)
        # Gathering again must replace the result, not double-count it.
        source.gather_outputs([first, second])
        self.assertEqual(source.total_replayed_events, 33)

    def test_actor_output_uses_generated_not_classified_replays(self):
        output = SimpleNamespace()
        sim = gate.Simulation()
        sim.add_source("GenericSource", "source_vertex")
        source = sim.add_source("LastVertexSource", "arbitrary_replay_name")
        source.total_replayed_events = 33
        actor = SimpleNamespace(
            simulation=sim,
            user_output=SimpleNamespace(last_vertex_output=output),
            GetNumberOfEvents=lambda: 12717,
            GetNumberOfReplayedEvents=lambda: 34,
            GetNumberOfKilledParticles=lambda: 0,
        )
        actor._get_replay_source = lambda: (
            LastVertexInteractionSplittingActor._get_replay_source(actor)
        )
        LastVertexInteractionSplittingActor.EndSimulationAction(actor)
        self.assertEqual(output.number_of_replayed_events, 33)
        self.assertEqual(output.number_of_actor_classified_replayed_events, 34)
        self.assertEqual(output.number_of_events - output.number_of_replayed_events, 12684)

    def test_replay_source_is_identified_by_type(self):
        sim = gate.Simulation()
        sim.add_source("GenericSource", "source_vertex")
        source = sim.add_source("LastVertexSource", "None")
        actor = SimpleNamespace(simulation=sim)
        self.assertIs(
            LastVertexInteractionSplittingActor._get_replay_source(actor), source
        )

    def test_missing_or_ambiguous_replay_sources_are_rejected(self):
        for count in (0, 2):
            with self.subTest(count=count):
                sim = gate.Simulation()
                for i in range(count):
                    sim.add_source("LastVertexSource", f"replay_{i}")
                actor = SimpleNamespace(simulation=sim)
                with self.assertRaisesRegex(Exception, "exactly one LastVertexSource"):
                    LastVertexInteractionSplittingActor._get_replay_source(actor)

    def test_replay_source_normalizes_before_multirun_validation(self):
        for runs in (1, 123):
            with self.subTest(runs=runs):
                sim = gate.Simulation()
                source = sim.add_source("LastVertexSource", "source_vertex")
                intervals = [[i, i + 1] for i in range(runs)]
                # No manually supplied placeholder count is needed.
                source.resolve_and_validate_config(intervals)
                source.resolve_and_validate_config(intervals)
                np.testing.assert_array_equal(source.number_of_primaries, np.ones(runs))
                self.assertEqual(source.activity, 0)


    def test_dose_uncertainty_correction_targets_dose_output(self):
        dose = MagicMock()
        dose.dose_uncertainty.active = True
        dose.dose_squared.active = True
        dose.dose_uncertainty.get_output_path.return_value = "dose-uncertainty.mhd"
        dose.dose.get_output_path.return_value = "dose.mhd"
        dose.dose_squared.get_output_path.return_value = "dose-squared.mhd"
        correction = MagicMock()
        actor = SimpleNamespace(
            simulation=SimpleNamespace(actor_manager=SimpleNamespace(actors={"dose": dose})),
            user_output=SimpleNamespace(last_vertex_output=SimpleNamespace(
                number_of_events=12, number_of_replayed_events=2)),
            UncertaintyCalculation=correction,
        )
        LastVertexInteractionSplittingActor.CorrectDoseUncertainty(actor)
        correction.assert_called_once_with(
            10, "dose-uncertainty.mhd", "dose.mhd", "dose-squared.mhd"
        )
        dose.edep_uncertainty.get_output_path.assert_not_called()



if __name__ == "__main__":
    unittest.main()
