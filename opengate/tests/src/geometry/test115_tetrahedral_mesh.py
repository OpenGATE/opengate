"""CI smoke test for the synthetic MRCP tetrahedral mesh."""

from pathlib import Path

import opengate as gate

from opengate.tests import utility


def test_tetrahedral_mesh():
    # Locate packaged mesh data independently of the current working directory.
    opengate_dir = Path(__file__).resolve().parents[3]
    data_dir = opengate_dir / "contrib" / "mrcp"
    for filename in (
        "simple.node",
        "simple.ele",
        "simple.material",
        "simple_colour.dat",
    ):
        assert (data_dir / filename).is_file(), f"Missing MRCP fixture: {filename}"

    sim = gate.Simulation()
    sim.number_of_threads = 1
    sim.visu = False
    sim.world.size = [2 * gate.g4_units.m] * 3
    sim.world.material = "G4_Galactic"

    phantom = sim.add_volume("TetrahedralMesh", "phantom_tetmesh")
    phantom.mother = "world"
    phantom.material = "G4_Galactic"
    phantom.node_file = str(data_dir / "simple.node")
    phantom.ele_file = str(data_dir / "simple.ele")
    phantom.material_file = str(data_dir / "simple.material")
    phantom.color_file = str(data_dir / "simple_colour.dat")
    phantom.default_material = "G4_Galactic"
    phantom.pv_name = "phantom_tetmesh_env"

    # The mesh has a region centered near x=-12 cm and another at the origin.
    # Fire along +x so primaries cross both regions rather than missing the mesh.
    source = sim.add_source("GenericSource", "mesh_source")
    source.particle = "gamma"
    source.number_of_primaries = 100
    source.energy.mono = 1 * gate.g4_units.MeV
    source.position.translation = [-18 * gate.g4_units.cm, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [1, 0, 0]

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    sim.run()

    assert stats.counts.events == 100
    assert stats.counts.tracks >= 100
    assert stats.counts.steps > 0


if __name__ == "__main__":
    test_tetrahedral_mesh()
    utility.test_ok(True)
