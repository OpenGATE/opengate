"""Small synthetic AMF cases; these coefficients are not physical reference data."""

from pathlib import Path

import numpy as np
import opengate as gate


def write_coefficients(path, rows=None):
    """Write a synthetic 576-row AMF table and return its Path.

    Default rows define a power-only distribution for analytical tests,
    not a physical fit. Supplied rows are written without modification."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows is None:
        # Only the power term remains: sed(x)=2**(-x).  A8=1000 eV.
        rows = np.tile([0, 0, 0, 0, 0, 0, 1, 2, 1000], (576, 1))
    np.savetxt(path, rows, fmt="%.17g")
    return path


def make_simulation(output, *, particle="proton", energy=100, weight=1):
    """Return a seeded water simulation, AMF actor and independent DoseActor.

    The compact fixture uses synthetic coefficients and eight primaries;
    energy is the total particle kinetic energy in MeV."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    sim = gate.Simulation()
    sim.output_dir = output
    sim.random_seed = 123456789
    sim.g4_verbose = False
    sim.visu = False
    sim.world.size = [100, 100, 100]
    box = sim.add_volume("Box", "water")
    box.size = [10, 10, 10]
    box.material = "G4_WATER"
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.global_production_cuts.all = 1000 * gate.g4_units.km
    source = sim.add_source("GenericSource", "beam")
    source.particle = particle
    source.energy.mono = energy * gate.g4_units.MeV
    source.position.translation = [0, 0, -4]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = 8
    source.weight = weight
    actor = sim.add_actor("AMFActor", "amf")
    actor.attached_to = "water"
    actor.tsed_file_name = str(write_coefficients(output / "synthetic_tsed.dat"))
    actor.size = [3, 1, 3]
    actor.spacing = [2, 6, 2]
    actor.hit_type = "middle"
    actor.DoseAveragedLinealEnergy.active = True
    actor.DoseAveragedLinealEnergySaturationCorrected.active = True
    actor.output_filename = "amf.mhd"
    actor.dose.write_to_disk = True
    actor.microdosimetric_spectra_file_name = "spectrum.mhd"
    # Identical spatial scoring with a separate standard dose implementation.
    dose = sim.add_actor("DoseActor", "dose")
    dose.attached_to = "water"
    dose.size = actor.size
    dose.spacing = actor.spacing
    dose.hit_type = actor.hit_type
    dose.dose.active = True
    dose.write_to_disk = False
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.write_to_disk = False
    return sim, actor, dose


def labels():
    """Return the 400 arithmetic lineal-energy bin midpoints in keV/um."""
    edges = np.logspace(-3, 5, 401)
    return (edges[1:] + edges[:-1]) / 2


def analytical_power_spectrum(radius=0.3):
    # The selected power-only distribution is exponential in y. Its continuum
    # dose mean is 2/lambda, independently of energy, charge and stopping power.
    """Return the exponential slope and continuum dose mean for radius in um."""
    lam = np.log(2) * (4 * radius / 3)
    return lam, 2 / lam
