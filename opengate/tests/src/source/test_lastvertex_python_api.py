"""Replay source discovery is independent of its user-defined name."""
from types import SimpleNamespace
import unittest
import opengate as gate
from opengate.actors.biasingactors import LastVertexInteractionSplittingActor


class VRTSourceAPITest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
