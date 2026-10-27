#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
from opengate.tests import utility
import opengate as gate

# An actor configured with configure_like() must keep its own outputs (see #505)

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test116")

    cm = gate.g4_units.cm
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    sim = gate.Simulation()
    sim.random_seed = 123456
    sim.output_dir = paths.output
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"

    # two water slabs crossed by the beam
    for name, x in (("slab1", -10 * cm), ("slab2", 10 * cm)):
        slab = sim.add_volume("Box", name)
        slab.size = [2 * cm, 20 * cm, 20 * cm]
        slab.translation = [x, 0, 0]
        slab.material = "G4_WATER"

    source = sim.add_source("GenericSource", "beam")
    source.particle = "gamma"
    source.energy.mono = 1 * MeV
    source.position.translation = [-30 * cm, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [1, 0, 0]
    source.number_of_primaries = 1000

    # phase space actors: the second one is configured like the first one
    phsp1 = sim.add_actor("PhaseSpaceActor", "phsp1")
    phsp1.attached_to = "slab1"
    phsp1.attributes = ["KineticEnergy", "PrePosition"]
    phsp1.output_filename = "phsp1.root"

    phsp2 = sim.add_actor("PhaseSpaceActor", "phsp2")
    phsp2.configure_like(phsp1)
    phsp2.attached_to = "slab2"
    phsp2.output_filename = "phsp2.root"
    # the attributes are copied, not shared
    phsp2.attributes.append("ParticleName")

    # dose actors: the second one is configured like the first one
    dose1 = sim.add_actor("DoseActor", "dose1")
    dose1.attached_to = "slab1"
    dose1.size = [1, 1, 1]
    dose1.spacing = [2 * cm, 20 * cm, 20 * cm]
    dose1.edep.output_filename = "dose1.mhd"

    dose2 = sim.add_actor("DoseActor", "dose2")
    dose2.configure_like(dose1)
    dose2.attached_to = "slab2"
    dose2.edep.output_filename = "dose2.mhd"

    is_ok = True

    b = all(
        output.belongs_to == actor.name
        for actor in (phsp2, dose2)
        for output in actor.user_output.values()
    )
    utility.print_test(b, "Outputs of the configured actors belong to them")
    is_ok = is_ok and b

    b = list(phsp1.attributes) == ["KineticEnergy", "PrePosition"]
    utility.print_test(b, f"phsp1 attributes are not modified: {phsp1.attributes}")
    is_ok = is_ok and b

    sim.run()

    # both phase spaces are written, with the expected attributes
    for actor, attributes in (
        (phsp1, {"KineticEnergy", "PrePosition_X"}),
        (phsp2, {"KineticEnergy", "PrePosition_X", "ParticleName"}),
    ):
        path = paths.output / f"{actor.name}.root"
        b = path.exists()
        n = 0
        if b:
            tree = uproot.open(path)[actor.name]
            n = tree.num_entries
            b = n > 0 and attributes.issubset(set(tree.keys()))
        utility.print_test(b, f"{path.name} written with {n} entries")
        is_ok = is_ok and b

    # both dose images are written and not empty
    for actor in (dose1, dose2):
        path = actor.edep.get_output_path()
        b = path.exists()
        edep = 0
        if b:
            edep = actor.edep.image.GetPixel([0, 0, 0])
            b = edep > 0
        utility.print_test(b, f"{path.name} written, edep = {edep:.3f} MeV")
        is_ok = is_ok and b

    utility.test_ok(is_ok)
