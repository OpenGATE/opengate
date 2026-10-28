#!/usr/bin/env python3

import opengate as gate


def _make_sim():
    sim = gate.Simulation()
    sim.number_of_threads = 1
    sim.world.size = [1.0, 1.0, 1.0]
    return sim


if __name__ == "__main__":
    sim = _make_sim()

    chem_box = sim.add_volume("BoxVolume", "chem_box")
    chem_box.size = [20.0, 40.0, 60.0]
    chem_box.translation = [1.0, 2.0, 3.0]

    chemistry_world = sim.chemistry_manager.create_chemistry_world(volume=chem_box)
    chemistry_world.pH = 7.2
    chemistry_world.add_component("H2O", 55.5)
    chemistry_world.add_component("O2", 2.5e-4)
    chemistry_world.add_scavenger_reaction(
        tracked_molecule="e_aq",
        scavenger="O2",
        products=["O2m"],
        rate_constant=1.74e10,
    )
    sim.chemistry_manager.confine_chemistry_to_volume = chem_box

    assert chemistry_world.source_volume_name == "chem_box"
    assert chemistry_world.translation == [1.0, 2.0, 3.0]
    assert chemistry_world.half_size == [10.0, 20.0, 30.0]
    assert chemistry_world.components_by_name["H2O"].concentration == 55.5
    assert chemistry_world.components_by_name["O2"].concentration == 2.5e-4
    assert chemistry_world.has_scavengers is True
    assert len(chemistry_world.scavenger_reactions) == 1
    assert chemistry_world.scavenger_reactions[0].tracked_molecule == "e_aq"
    assert sim.chemistry_manager.confine_chemistry_to_volume == "chem_box"

    d = sim.to_dictionary()

    sim2 = _make_sim()
    sim2.from_dictionary(d)
    chemistry_world_2 = sim2.chemistry_manager.chemistry_world

    assert chemistry_world_2 is not None
    assert chemistry_world_2.source_volume_name == "chem_box"
    assert chemistry_world_2.translation == [1.0, 2.0, 3.0]
    assert chemistry_world_2.half_size == [10.0, 20.0, 30.0]
    assert chemistry_world_2.pH == 7.2
    assert chemistry_world_2.components_by_name["H2O"].concentration == 55.5
    assert chemistry_world_2.components_by_name["O2"].concentration == 2.5e-4
    assert chemistry_world_2.has_scavengers is True
    assert len(chemistry_world_2.scavenger_reactions) == 1
    assert chemistry_world_2.scavenger_reactions[0].scavenger == "O2"
    assert sim2.chemistry_manager.confine_chemistry_to_volume == "chem_box"

    sim3 = _make_sim()
    chemistry_world_3 = sim3.chemistry_manager.create_chemistry_world(
        translation=[4.0, 5.0, 6.0],
        half_size=[7.0, 8.0, 9.0],
    )
    assert chemistry_world_3.source_volume_name is None
    assert chemistry_world_3.translation == [4.0, 5.0, 6.0]
    assert chemistry_world_3.half_size == [7.0, 8.0, 9.0]

    print("test103_chemistry_world: OK")
