#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.contrib.carm.siemensciosalpha import Ciosalpha
from scipy.spatial.transform import Rotation
from opengate.tests import utility as utl
import matplotlib.pyplot as plt
import itk
import numpy as np
import json
import pathlib


if __name__ == "__main__":
    # paths
    paths = utl.get_default_test_paths(__file__, "gate_test075_siemens_cios_alpha", "test075")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.visu_type = "vrml"
    sim.number_of_threads = 1
    sim.random_seed = 12345678
    sim.check_volumes_overlap = True
    sim.output_dir = paths.gate_output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    deg = gate.g4_units.deg

    # world
    world = sim.world
    world.size = [5 * m, 5 * m, 5 * m]
    world.material = "G4_AIR"

    # xray tube spectrum parameters
    # tube potential [kV] (50, 60, 70, 80, 90, 100, 110, 120 to compare with experimental data)
    kvp = 80

    # add a carm
    carm = Ciosalpha(sim, kvp, source_only=False)
    carm.rotation = Rotation.from_euler("ZYX", [0, 90, 0], degrees=True).as_matrix()
    carm.translation = [0 * cm, 0 * cm, 0 * cm]
    carm.collimation = [25 * mm, 25 * mm]

    carm.source.n = 1e7
    if sim.visu:
        carm.source.n = 1000

    # CBCT detector plane
    detector_plane = sim.add_volume("Box", "CBCT_detector_plane")
    detector_plane.size = [10 * mm, 200 * mm, 200 * mm]
    detector_plane.translation = [-150 * mm, 0, 0]
    detector_plane.material = "G4_AIR"
    detector_plane.color = [1, 0, 0, 1]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option1"
    sim.physics_manager.set_production_cut("world", "all", 10 * mm)

    # actor
    detector_actor = sim.add_actor("FluenceActor", "detector_actor")
    detector_actor.attached_to = detector_plane
    detector_actor.output_filename = "fluence.mhd"
    detector_actor.spacing = [10 * mm, 2 * mm, 2 * mm]
    detector_actor.size = [10, 101, 101]
    detector_actor.output_coordinate_system = "local"

    # start simulation
    sim.run()

    def get_normalized_profile(img, axis="z", nb_points=200):
        """
        Get evenly spaced values from the profile and normalize them by the middle value.
        
        Parameters:
        -----------
        img : itk.Image
            The input image
        axis : str
            The axis along which to get the profile ('x', 'y', or 'z')
        nb_points : int
            Number of points to sample (default=200)
                
        Returns:
        --------
        tuple: (positions, normalized_values)
            The positions and normalized values
        """
        # Get data in numpy array
        data = itk.GetArrayViewFromImage(img)
        
        if axis == "z":
            y = np.nansum(data, 2)
            y = np.nansum(y, 1)
            x = np.arange(len(y)) * img.GetSpacing()[2]
        elif axis == "y":
            y = np.nansum(data, 2)
            y = np.nansum(y, 0)
            x = np.arange(len(y)) * img.GetSpacing()[1]
        else: # axis == "x"
            y = np.nansum(data, 1)
            y = np.nansum(y, 0)
            x = np.arange(len(y)) * img.GetSpacing()[0]
        
        # Get middle value for normalization
        mid_idx = len(x) // 2
        mid_val = y[mid_idx]
        
        # Interpolate to get evenly spaced points
        from scipy.interpolate import interp1d
        f = interp1d(x, y, kind='linear')
        
        # Create new x points evenly spaced
        x_new = np.linspace(x[0], x[-1], nb_points)
        y_new = f(x_new)
        
        # Normalize by middle value
        y_normalized = y_new / mid_val
        
        return x_new, y_normalized

    # Load experimental and simulation data
    # Simulation data
    img_mhd_out = itk.imread(paths.gate_output / detector_actor.output_filename)
    positions, weights = get_normalized_profile(img_mhd_out, axis="z", nb_points=200)
    positions = [pos -100 for pos in positions]

    # Experimental data
    current_dir = pathlib.Path(__file__).parent
    exp_file_path = current_dir.parent.parent / "contrib" / "carm" / "experimental_values.json"
    with open(exp_file_path, 'r') as f:
        exp_data = json.load(f)
    exp_positions = [pos*10.0 for pos in exp_data[str(kvp)]['distance']]
    exp_weights = list(reversed(exp_data[str(kvp)]['weight']))

    # Calculate differences
    differences = []
    within_uncertainty = []
    print(f"\nAnalysis for {kvp} kV:")
    print("Position (mm) | Simulation | Experimental | Difference (%)")
    print("-" * 75)
    
    # Interpolate simulation data to match experimental positions
    from scipy.interpolate import interp1d
    f = interp1d(positions, weights, kind='linear')
    sim_weights_interp = f(exp_positions)

    # excluding first/last 2 values
    exp_positions_trimmed = exp_positions[2:-2]
    sim_weights_interp_trimmed = sim_weights_interp[2:-2]
    exp_weights_trimmed = exp_weights[2:-2]
    
    for pos, sim_w, exp_w in zip(exp_positions_trimmed, sim_weights_interp_trimmed, exp_weights_trimmed):
        diff_percent = ((sim_w - exp_w) / exp_w) * 100
        differences.append(diff_percent)
        print(f"{pos:13.1f} | {sim_w:10.4f} | {exp_w:12.4f} | {diff_percent:11.2f}%")
    
    # results
    max_difference = max(abs(d) for d in differences)
    avg_abs_difference = sum(abs(d) for d in differences) / len(differences)
    print(f"\nMaximum difference: {max_difference:.2f}%")
    print(f"Average absolute difference: {avg_abs_difference:.2f}%")

    # Create plot with updated title
    fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    ax.plot(positions, weights, 'b-', label='Simulation')
    ax.plot(exp_positions, exp_weights, 'ro', label=f'Experimental ({kvp} kV)')
    ax.set_xlabel('Position (mm)')
    ax.set_ylabel('Weight (normalized to middle value)')
    ax.set_title(f'Anode Heel Effect Profile Comparison - Siemens Cios Alpha {kvp} kV')
    ax.grid(True)
    ax.legend()

    # Save plot
    fig.savefig(paths.gate_output / "anode_heel_effect_comparison.png")
    plt.show()

    is_ok = max_difference < 5.0 and avg_abs_difference < 2.0
    utl.test_ok(is_ok)