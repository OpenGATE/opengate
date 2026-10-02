#!/usr/bin/env python3
"""Small kernel matrix and mixed-field run using explicitly synthetic fits.

This checks integration at paper benchmark points, not physical agreement with
TOPAS-nBio/PHITS. Production fitting coefficients and numerical references are
required before making such a comparison.
"""

import json

import itk
import numpy as np
import opengate as gate
from opengate_core import opengate_core as g4

from opengate.tests import utility
from test103_AMF_helpers import analytical_power_spectrum, labels, make_simulation, write_coefficients


def check(actor, reference, radius=.3, excluded=False):
    """Check synthetic spectrum normalization, moments and eligible dose bounds.

    Return aggregate metrics; excluded charges must produce zero AMF dose
    while the independent all-particle dose remains positive."""
    dose = itk.array_from_image(actor.dose.get_data())
    all_dose = itk.array_from_image(reference.dose.get_data())
    spectrum = itk.array_from_image(actor.microdosimetric_spectra.get_data())
    yd = itk.array_from_image(actor.DoseAveragedLinealEnergy.get_data())
    assert all_dose.sum() > 0 and np.isfinite(spectrum).all()
    assert np.all(spectrum >= 0) and np.all(dose <= all_dose * (1 + 1e-12) + 1e-25)
    if excluded:
        assert np.all(dose == 0) and np.all(spectrum == 0)
        return dict(status="outside actor scope: Z=26", all_particle_dose=float(all_dose.sum()))
    assert dose.sum() > 0
    scored = dose > 0
    integral = spectrum[scored].sum(-1) * np.log(10) / 50
    np.testing.assert_allclose(integral, 1, rtol=1e-12)
    np.testing.assert_allclose(yd[scored], analytical_power_spectrum(radius)[1], rtol=2e-4)
    # Hartzell eq.4: derive the dose mean from the independently parsed q=yd(y).
    derived = (spectrum[scored] * labels()).sum(-1) / spectrum[scored].sum(-1)
    np.testing.assert_allclose(yd[scored], derived, rtol=1e-12)
    dose_weighted = (spectrum * dose[..., None]).sum(axis=(0, 1, 2))
    integrated_dose = dose_weighted.sum() * np.log(10) / 50
    np.testing.assert_allclose(integrated_dose, dose.sum(), rtol=1e-12)
    return dict(status="synthetic equation/integration pass", dose=float(dose.sum()),
                integrated_dose=float(integrated_dose), normalization=float(integral.mean()),
                yd=float(np.average(yd[scored], weights=dose[scored])),
                reference_yd=analytical_power_spectrum(radius)[1])


def main():
    """Check synthetic integration at literature beam points and in a mixed field."""
    paths = utility.get_default_test_paths(__file__, output_folder="test103_AMF_literature")
    rows = []
    paths.output.mkdir(parents=True, exist_ok=True)
    table = write_coefficients(paths.output / "synthetic_matrix.dat")
    calc = g4._AMFCalculator(400, .6, .3, 4.5, .0615, 2, 9)
    calc.load(str(table))
    # Check paper beam points through the numerical kernel, avoiding 24 separate
    # Geant4 startups. The synthetic power-only model has a known dose mean.
    for charge, mass in ((1, 1), (2, 4), (3, 7), (6, 12), (8, 16), (10, 20), (18, 40)):
        for energy in (1, 10, 100):
            spectrum, yd, ys = calc.calculate(charge, mass, energy, 10, 1)
            np.testing.assert_allclose(spectrum.sum()*np.log(10)/50, 1, rtol=1e-12)
            np.testing.assert_allclose(yd, analytical_power_spectrum()[1], rtol=2e-4)
            assert 0 < ys <= yd
            rows.append(dict(charge=charge, mass=mass, energy_mev_u=energy, yd=yd))

    # Broad energy distributions and carbon fragmentation in a mixed field.
    # This is not a reproduction of the published carbon-SOBP geometry.
    sim, actor, reference = make_simulation(paths.output / "mixed")
    sim.number_of_threads = 1
    sim.world.size = [500, 500, 500]
    sim.volume_manager.get_volume("water").size = [100, 100, 100]
    actor.size = reference.size = [1, 1, 10]
    actor.spacing = reference.spacing = [100, 100, 10]
    actor.write_to_disk = False
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"
    sim.physics_manager.set_max_step_size("water", 2)
    sim.physics_manager.user_limits_particles = "all"
    beam = sim.source_manager.get_source("beam")
    beam.position.translation = [0, 0, -45]
    beam.particle = "ion 6 12"
    beam.energy.type = "gauss"
    beam.energy.mono = 1500
    beam.energy.sigma_gauss = 150
    beam.number_of_primaries = 32
    for name, particle, energy, weight in (("protons", "proton", 150, .5),
                                           ("helium", "ion 2 4", 600, 2)):
        source = sim.add_source("GenericSource", name)
        source.particle = particle
        source.position.translation = [0, 0, -45]
        source.direction.type = "momentum"
        source.direction.momentum = [0, 0, 1]
        source.energy.type = "gauss"
        source.energy.mono = energy
        source.energy.sigma_gauss = energy * .1
        source.number_of_primaries = 16
        source.weight = weight
    stats = sim.get_actor("stats")
    stats.track_types_flag = True
    sim.run()
    assert stats.counts.events == 64
    result = check(actor, reference)
    result.update(case="mixed carbon/proton/helium, broad energies and nuclear fragments",
                  threads=1, physics="QGSP_BIC_EMZ", track_types=dict(stats.counts.track_types),
                  external_SOBP_comparison="unavailable: production coefficients, exact setup and reference tables absent")
    assert len(result["track_types"]) > 3, "The mixed-field case must produce secondary species"
    rows.append(result)
    (paths.output / "matrix.json").write_text(json.dumps(rows, indent=2) + "\n")
    utility.test_ok(True)


if __name__ == "__main__":
    main()
