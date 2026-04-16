#!/usr/bin/env python3
"""
Shared helpers for the test099_fields_* tests.
"""

import numpy as np

import opengate as gate
from opengate.geometry import fields

# Units
g4_m = gate.g4_units.m
g4_cm = gate.g4_units.cm
g4_mm = gate.g4_units.mm
g4_tesla = gate.g4_units.tesla
g4_MeV = gate.g4_units.MeV
g4_volt = gate.g4_units.volt
g4_eplus = gate.g4_units.eplus

# Proton mass
PROTON_MASS = 938.27208943 * g4_MeV


def cyclotron_radius(T, B, m, q):
    """
    Relativistic cyclotron radius:  r = p / (qBc).
    """
    E_tot = T + m
    p = np.sqrt(E_tot**2 - m**2)
    return p / (q * B * 0.299792458) / g4_m


def build_field_simulation(
    field_obj,
    kinetic_energy=10 * gate.g4_units.MeV,
    particle="proton",
    n_particles=1,
    phsp_output_filename="phsp.root",
    n_threads=1,
    seed=42,
    output_dir=".",
):
    """
    Build a standard simulation with:
      - vacuum world (1 m^3)
      - vacuum box (50 cm^3) with the given field attached
      - proton source at z = -1 m, shooting along +z
      - PhaseSpaceActor recording exiting particles
    Returns (simulation, phsp_actor).
    """
    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = n_threads
    sim.random_seed = seed
    sim.output_dir = output_dir

    world = sim.world
    world.size = [1 * g4_m, 1 * g4_m, 1 * g4_m]
    world.material = "G4_Galactic"

    box = sim.add_volume("BoxVolume", "field_box")
    box.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
    box.material = "G4_Galactic"
    box.add_field(field_obj)

    source = sim.add_source("GenericSource", "particle_source")
    source.particle = particle
    source.n = n_particles
    source.energy.type = "mono"
    source.energy.mono = kinetic_energy
    source.position.type = "point"
    source.position.translation = [0, 0, -100 * g4_cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = box.name
    phsp.attributes = ["PostKineticEnergy", "PostPosition"]
    phsp.output_filename = phsp_output_filename
    phsp.steps_to_store = "exiting"
    phsp.root_output.write_to_disk = True

    return sim, phsp
