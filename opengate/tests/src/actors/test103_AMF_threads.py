#!/usr/bin/env python3
"""Worker reduction, stochastic transport checks, and independent AMF instances."""

import json

import itk
import numpy as np
import SimpleITK as sitk

import opengate as gate
from opengate.tests import utility
from test103_AMF_helpers import analytical_power_spectrum, labels, make_simulation


def array(output):
    """Copy an output interface's retained ITK image into a NumPy array."""
    return itk.array_from_image(output.get_data())


def run_case(
    output,
    threads,
    seed=123456789,
    *,
    forced=False,
    multiple=False,
    no_hit=False,
    in_process=False,
    event_count=64,
):
    """Run and check a synthetic serial or threaded AMF transport case.

    Optional cases exercise independent actor instances, empty scoring
    grids and in-process lifecycle guards. Return aggregate metrics."""
    sim, actor, dose = make_simulation(output, weight=3.7)
    sim.number_of_threads = threads
    sim.force_multithread_mode = forced
    sim.random_seed = seed
    sim.source_manager.get_source("beam").number_of_primaries = event_count
    actor.size = dose.size = [1, 1, 1]
    actor.spacing = dose.spacing = [10, 10, 10]
    dose.dose_uncertainty.active = True
    actor.write_to_disk = False
    if no_hit:
        actor.translation = [50, 0, 0]
    instances = [actor]
    if multiple:
        # One instance in the same volume and a third in a separate volume.
        for name, radius, volume in (
            ("same_volume", 0.15, "water"),
            ("other_volume", 0.5, "water2"),
        ):
            if volume == "water2":
                box = sim.add_volume("Box", volume)
                box.material = "G4_WATER"
                box.size = [10, 10, 10]
                box.translation = [20, 0, 0]
                source = sim.add_source("GenericSource", "helium")
                source.particle = "ion 2 4"
                source.energy.mono = 400
                source.position.translation = [20, 0, -4]
                source.direction.type = "momentum"
                source.direction.momentum = [0, 0, 1]
                source.number_of_primaries = 32
            item = sim.add_actor("AMFActor", name)
            item.attached_to = volume
            item.size = [1, 1, 1]
            item.spacing = [10, 10, 10]
            item.hit_type = "middle"
            item.DomainRadius = radius * gate.g4_units.um
            item.tsed_file_name = actor.tsed_file_name
            item.DoseAveragedLinealEnergy.active = True
            item.output_filename = name + ".mhd"
            item.microdosimetric_spectra_file_name = name + "_spectrum.mhd"
            item.write_to_disk = False
            instances.append(item)
    sim.run(start_new_process=not in_process)
    if in_process:
        for call, message in (
            (lambda: actor.SetNucleusRadius(1), "configuration"),
            (actor.InitializeCpp, "initialization"),
            (lambda: actor.BeginOfRunActionMasterThread(0), "run start"),
            (lambda: actor.EndOfRunActionMasterThread(0), "finalization"),
        ):
            try:
                call()
            except RuntimeError as error:
                assert message in str(error), str(error)
            else:
                raise AssertionError(f"Expected {message} rejection")
    events = event_count + 32 if multiple else event_count
    assert sim.get_actor("stats").counts.events == events, sim.get_actor("stats").counts
    if no_hit:
        assert array(dose.dose).sum() > 0
        for interface in actor.interfaces_to_user_output.values():
            assert np.all(array(interface) == 0)
        return dict(threads=threads, events=events, empty=True)
    np.testing.assert_allclose(
        array(actor.dose), array(dose.dose), rtol=1e-12, atol=1e-25
    )
    for item in instances:
        d = array(item.dose)
        assert d.sum() > 0
        spectrum = array(item.microdosimetric_spectra)
        assert spectrum.shape == (1, 1, 1, 400) and spectrum.dtype == np.float64
        assert np.all(np.isfinite(spectrum)) and np.all(spectrum >= 0)
        np.testing.assert_allclose(spectrum.sum(-1) * np.log(10) / 50, 1, rtol=1e-12)
        radius = item.DomainRadius / gate.g4_units.um
        lam, yd = analytical_power_spectrum(radius)
        np.testing.assert_allclose(array(item.DoseAveragedLinealEnergy), yd, rtol=2e-4)
        y = labels()
        expected = y**2 * np.exp(-lam * y)
        expected[np.exp(-lam * y) <= 1e-10] = 0
        expected *= (50 / np.log(10)) / expected.sum()
        np.testing.assert_allclose(spectrum[0, 0, 0], expected, rtol=1e-10, atol=1e-12)
        assert (
            item.user_output.dose.merged_data.get_data_item_object(0).number_of_samples
            == events
        )
        if multiple:
            for interface in item.interfaces_to_user_output.values():
                if interface.active and interface.write_to_disk:
                    image = sitk.ReadImage(str(interface.get_output_path()))
                    assert image.GetSize() == (1, 1, 1)
                    np.testing.assert_array_equal(
                        sitk.GetArrayFromImage(image), array(interface)
                    )
    if multiple:
        np.testing.assert_allclose(
            array(instances[1].dose), array(actor.dose), rtol=1e-12
        )
        assert instances[1].DomainRadius != actor.DomainRadius
    # DoseActor estimates relative standard error of the whole-volume dose.
    return dict(
        threads=threads,
        events=events,
        dose=float(array(actor.dose).sum()),
        sem=float(array(dose.dose_uncertainty).ravel()[0] * array(actor.dose).sum()),
        yd=float(array(actor.DoseAveragedLinealEnergy).ravel()[0]),
    )


def main():
    """Check two-worker scoring and independent instances in one small run."""
    paths = utility.get_default_test_paths(
        __file__, output_folder="test103_AMF_threads"
    )
    result = run_case(paths.output, 2, multiple=True, in_process=True, event_count=16)
    (paths.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    utility.test_ok(True)


if __name__ == "__main__":
    main()
