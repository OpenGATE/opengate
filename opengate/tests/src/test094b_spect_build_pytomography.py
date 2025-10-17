#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.contrib.spect.pytomography_helpers import *
from opengate.tests import utility

if __name__ == "__main__":

    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test094_pytomography"
    )
    data_folder = paths.data

    # units
    mm = g4_units.mm
    cm = g4_units.cm
    sec = g4_units.s
    keV = g4_units.keV

    # Init SPECT simulation, no phantom, no source
    sc = SPECTConfig()
    sc.output_folder = paths.output_ref
    sc.detector_config.model = "intevo"
    sc.detector_config.collimator = "melp"
    sc.detector_config.number_of_heads = 2
    sc.detector_config.size = [128, 128]
    sc.detector_config.spacing = [4.8 * mm, 4.8 * mm]
    sc.detector_config.digitizer_function = intevo.add_digitizer
    sc.detector_config.digitizer_channels = intevo.get_default_energy_windows("lu177")
    sc.phantom_config.image = data_folder / "ct_5mm.mhd"
    sc.phantom_config.translation = [0, 0, -20 * cm]
    sc.source_config.radionuclide = "177lu"
    # spect position has changed since the initial creation of the reference data
    # so we adapt the radius with 11 cm shift
    sc.acquisition_config.radius = 420 * mm - 11.707759999999993 * cm
    sc.acquisition_config.duration = 30 * sec
    sc.acquisition_config.number_of_angles = 30

    # Create the simulation to retrieve some spect information
    # (no need to run the simulation)
    sim = gate.Simulation()
    sc.setup_simulation(sim, visu=False)
    metadata = pytomography_build_metadata_and_attenuation_map(
        sc, sim, 208 * keV, output_folder=paths.output, verbose=True
    )

    # write metadata as a JSON file
    fn = paths.output / "pytomography_gate.json"
    with open(fn, "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"Metadata written in {fn}")

    # check the generated file according to the reference one
    ref_json = paths.output_ref / "pytomography_gate.json"
    # compare the dict
    with open(ref_json, "r") as f:
        ref_metadata = json.load(f)

    # compare the dict
    added, removed, modified, same = utility.dict_compare(metadata, ref_metadata)
    is_ok = len(added) == 0 and len(removed) == 0 and len(modified) == 0
    utility.print_test(is_ok, f"Labels comparisons, added:    {added}")
    utility.print_test(is_ok, f"Labels comparisons, removed:  {removed}")
    utility.print_test(is_ok, f"Labels comparisons: modified: {modified}")

    utility.test_ok(is_ok)
