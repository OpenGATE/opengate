SPECT imaging systems
=====================

**Important Notice**: Please be aware that the models provided within the OpenGate toolkit are based on approximate simulations. Users are strongly encouraged to independently verify these models against empirical data to ensure their applicability and accuracy for specific use cases.

GE Discovery 670 SPECT
----------------------

The GE Discovery NM670 SPECT system can be simulated using the following commands:


.. code-block:: python

    import opengate as gate
    import opengate.contrib.spect.ge_discovery_nm670 as discovery

    sim = gate.Simulation()
    spect, colli, crystal = discovery.add_spect_head(sim, "discovery1", collimator_type="lehr")
    discovery.add_digitizer(sim, crystal.name, "digit_tc99m")

    spect, colli, crystal = discovery.add_spect_head(sim, "discovery12", collimator_type="megp", rotation_deg=15 , crystal_size="5/8")
    discovery.add_digitizer(sim, crystal.name, "digit_lu177")


This configuration allows the simulation of two SPECT heads with different collimators (LEHR and MEGP) and digitizers optimized for Tc99m and Lu177, respectively. There are three collimator types: "lehr", "megp" and "hegp". There are two crystal size "3/8" and "5/8". Also the collimator can be rotated by few degrees, usually 15 deg like in reality.

Detail of the head description is `available here <https://github.com/OpenGATE/opengate/blob/master/opengate/contrib/spect/ge_discovery_nm670.py#L53>`_

**Note**: the digitizer is still a very simple one, validation are still in progress.


Siemens Symbia Intevo Bold SPECT
--------------------------------

The Siemens Symbia Intevo Bold SPECT system can be simulated with the following commands:


.. code-block:: python

    import opengate as gate
    import opengate.contrib.spect.siemens_intevo as intevo

    sim = gate.Simulation()
    spect, colli, crystal = intevo.add_spect_head(sim, "intevo1", collimator_type="lehr")
    crystal = sim.volume_manager.get_volume(f"{spect.name}_crystal")
    intevo.add_digitizer_tc99m(sim, crystal.name, "digit_tc99m")

    spect, colli, crystal = discovery.add_spect_head(sim, "intevo2", collimator_type="melp")
    crystal = sim.volume_manager.get_volume(f"{spect.name}_crystal")
    intevo.add_digitizer_lu177(sim, crystal.name, "digit_lu177")


There are three collimators: LEHR - Low Energy High Resolution for Tc99m with 1.11 mm holes; MELP - Medium Energy Low Penetration for In111 and Lu177 with 2.94 mm holes and HE - High Energy General Purpose for I131 with 4 mm holes.

Detail of the head description is `available here <https://github.com/OpenGATE/opengate/blob/master/opengate/contrib/spect/siemens_intevo.py#L19>`_


**Note**: the digitizer is still a very simple one, validation are still in progress.


Gate to PyTomography Reconstruction
-----------------------------------

OpenGate provides a dedicated interface to reconstruct simulated SPECT projection data using the **PyTomography** library. This is achieved via the `GateToPyTomographyAdapter`, which handles the coordinate transformations, unit conversions (mm to cm), and grid alignments.

The integration is demonstrated in the `test094` series of scripts, which simulates a NEMA IEC phantom with primary and scatter estimates.

Part 1: Quick Start
~~~~~~~~~~~~~~~~~~~

A complete simulation and reconstruction pipeline is typically split into four stages:

1. **Primary Simulation** (`test094a_spect_simu_prim.py`): Simulate the unscattered photons (with FFAA)
2. **Scatter Simulation** (`test094b_spect_simu_scatter.py`): Simulate the scattered photons (with FFAA)
3. **Sinogram Generation** (`test094c_build_sinogram.py`): Merge the primary and scatter data, and organize the raw detector projections into continuous, energy-separated sinograms using ``build_sinograms_from_files()``.
4. **Reconstruction** (`test094d_reconstruction.py`): Feed the sinograms into PyTomography.

Here is a minimal example of how to configure the adapter and run the reconstruction:

.. code-block:: python

    from opengate.contrib.spect.pytomography_helpers import GateToPyTomographyAdapter
    from opengate.image import get_image_physical_center
    import SimpleITK as sitk
    import numpy as np

    # 1. Initialize the adapter
    ad = GateToPyTomographyAdapter()

    # 2. Acquisition Parameters
    ad.acquisition.filenames = [f"sinogram_{c}.mhd" for c in range(6)]
    ad.acquisition.angles = np.linspace(0, 360, 120, endpoint=False)
    ad.acquisition.radii = np.ones(120) * 250.0 # in mm
    ad.acquisition.index_peak = 4

    # Calculate the physical center of the phantom to align the rotation axis
    ad.acquisition.isocenter = get_image_physical_center("iec_phantom.mhd")

    # 3. Target Reconstruction Grid (Output space)
    ad.reconstruction.template_filename = "iec_phantom.mhd"

    # 4. Corrections (Attenuation, PSF, Scatter)
    ad.mumap.filename = "iec_mu_208kev.mhd"

    # 3-Parameter PSF fit
    ad.psf.sigma_fit_params = np.array((0.01788, 0.5158, 0.0022))
    ad.psf.sigma_fit = "3_param"

    # TEW Scatter Correction
    ad.scatter_correction.mode = "TEW"
    ad.scatter_correction.index_upper = 5
    ad.scatter_correction.index_lower = 3
    ad.scatter_correction.w_peak_kev = 41.6
    ad.scatter_correction.w_lower_kev = 41.6
    ad.scatter_correction.w_upper_kev = 41.6

    # 5. Validate and Reconstruct
    ad.initialize_and_validate()
    img = ad.reconstruct_osem(iterations=4, subsets=6, device="auto", verbose=True)

    sitk.WriteImage(img, "reconstructed.mha")


Part 2: Under the Hood
~~~~~~~~~~~~~~~~~~~~~~

**Coordinate Systems & Unit Conversion**
Gate and SimpleITK operate in **millimeters**, while PyTomography natively computes in **centimeters**. Furthermore, the array axes (Z, Y, X) and rotation directions differ. The adapter automatically intercepts all data (spacings, radii, PSF distances) and transforms it to PyTomography's expected format, before rotating the final output array back to the standard Gate physical space.

**The "Working Grid" vs. "Final Grid"**
Running OSEM reconstruction on an anisotropic or mismatched voxel grid with PyTomography can introduce mathematical artifacts. The adapter decouples the physics from the output:
* **Working Grid:** During the OSEM iterations, the adapter forces PyTomography to reconstruct the object on an isotropic "physics grid" that matches the physical spacing of the detector pixels.
* **Final Grid:** Once reconstruction is complete, the adapter uses ``sitk.ResampleImageFilter`` (with B-Spline interpolation) to cast the result onto the final geometry defined by ``ad.reconstruction.template_filename``.

**Physical Isocenter Alignment**

PyTomography operates under the mathematical assumption that the scanner's axis of rotation (the isocenter) is located at the coordinate origin ``(0,0,0)`` of the image. Gate, however, allows for flexible configurations where the phantom and the gantry's rotation axis can be placed anywhere in the simulated world space.

To resolve this discrepancy, the data must be mathematically aligned. By providing the physical coordinates of the Gate rotation axis via ``ad.acquisition.isocenter``, the adapter dynamically shifts the origin of the PyTomography "Working Grid." This guarantees that the attenuation maps (mu-maps) and the emission projections are co-registered to the mechanical axis of rotation, without requiring the user to manually translate the raw image arrays.

* **Coordinate System Transformations (The Axis Swap)**
Gate and SimpleITK operate in **millimeters**, while PyTomography natively computes in **centimeters**. Furthermore, the array axes and directional conventions differ. The adapter manages these spatial conversions automatically during the data hand-off:

* **Memory Mapping (ITK to NumPy):** SimpleITK defines images using continuous spatial coordinates ordered as (X, Y, Z). When converted to a NumPy array, the data is mapped into C-contiguous memory (from slowest-varying to fastest-varying dimension), resulting in a shape of (Z, Y, X).
* **The Transposition:** PyTomography requires the input object tensors to be ordered by their spatial dimensions: (X, Y, Z). The adapter applies a standard transposition to convert the (Z, Y, X) arrays back into (X, Y, Z).
* **The Y-Axis Inversion:** GATE and PyTomography use opposite conventions for the orientation of the anterior-posterior axis relative to the gantry's center of rotation. The adapter inverts the data along the new Y-axis. This ensures the physical geometries align correctly during the forward and back-projection mathematical steps.

**Serialization**
The adapter state can be saved to JSON using ``ad.dump("recon_param.json")``. This is useful for debugging or cluster-based reconstruction, as it captures the exact geometries, scaling factors, and energy window widths passed to PyTomography. Warning : sigma_fit custom lambda function cannot be serialized.