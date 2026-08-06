#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
from pathlib import Path

import opengate as gate
import opengate_core as g4
from opengate.geometry.volumes import GDMLVolume
from opengate.tests import utility

GDML_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<gdml
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:noNamespaceSchemaLocation="http://cern.ch/geant4/GDML/schema/gdml.xsd">

  <define>
    <position
      name="gdml_test_inner_position"
      unit="mm"
      x="0"
      y="0"
      z="0"/>
  </define>

  <materials>
    <material name="GDMLTestVacuum" state="gas" Z="1">
      <D value="1.0e-25" unit="g/cm3"/>
      <atom value="1.00794" unit="g/mole"/>
    </material>

    <material name="GDMLTestAluminium" state="solid" Z="13">
      <D value="2.7" unit="g/cm3"/>
      <atom value="26.9815" unit="g/mole"/>
    </material>
  </materials>

  <solids>
    <box
      name="gdml_test_world_box"
      lunit="mm"
      x="1000"
      y="1000"
      z="1000"/>

    <box
      name="gdml_test_inner_box"
      lunit="mm"
      x="100"
      y="100"
      z="100"/>
  </solids>

  <structure>
    <volume name="gdml_test_inner_logical">
      <materialref ref="GDMLTestAluminium"/>
      <solidref ref="gdml_test_inner_box"/>
    </volume>

    <volume name="gdml_test_world_logical">
      <materialref ref="GDMLTestVacuum"/>
      <solidref ref="gdml_test_world_box"/>

      <physvol name="gdml_test_inner_physical">
        <volumeref ref="gdml_test_inner_logical"/>
        <positionref ref="gdml_test_inner_position"/>
      </physvol>
    </volume>
  </structure>

  <setup name="Default" version="1.0">
    <world ref="gdml_test_world_logical"/>
  </setup>

</gdml>
"""


def create_simulation(gdml_path, output_path):
    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 123456789
    sim.output_dir = output_path

    m = gate.g4_units.m
    sim.world.size = [3 * m, 3 * m, 3 * m]
    sim.world.material = "G4_AIR"

    imported = sim.add_volume("GDML", "ImportedGDMLGeometry")
    imported.file_name = gdml_path
    imported.setup_name = "Default"
    imported.validate = False
    imported.strip_names = False
    imported.parser_overlap_check = False
    imported.mother = "world"

    source = sim.add_source("GenericSource", "GammaSource")
    source.particle = "gamma"
    source.n = 100
    source.energy.mono = 1 * gate.g4_units.MeV
    source.position.type = "point"
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [1, 0, 0]

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    # Attach a sensitive actor to the imported GDML root.
    # OpenGATE must propagate it to the logical-volume children
    # created internally by G4GDMLParser.
    kill_actor = sim.add_actor("KillActor", "KillImportedGeometry")
    kill_actor.attached_to = imported

    return sim, imported, stats, kill_actor


def main():
    assert hasattr(g4, "G4GDMLParser")

    with tempfile.TemporaryDirectory(prefix="opengate_gdml_test_") as directory:
        output_path = Path(directory)
        gdml_path = output_path / "minimal.gdml"
        gdml_path.write_text(GDML_CONTENT)

        assert gdml_path.is_file()

        sim, imported, stats, kill_actor = create_simulation(
            gdml_path,
            output_path,
        )

        assert isinstance(imported, GDMLVolume)
        assert imported.mother == "world"
        assert imported.setup_name == "Default"
        assert Path(imported.file_name) == gdml_path

        sim.run()

        print(stats)

        assert stats.counts.runs == 1
        assert stats.counts.events == 100
        assert stats.counts.tracks >= 100
        assert stats.counts.steps >= stats.counts.tracks

        print(
            "Particles killed in imported GDML geometry:",
            kill_actor.number_of_killed_particles,
        )
        assert kill_actor.number_of_killed_particles >= stats.counts.events
        assert kill_actor.number_of_killed_particles == stats.counts.tracks

    utility.test_ok(True)


if __name__ == "__main__":
    main()
