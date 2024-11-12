Treatment Plan Pencil Beam source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In ion beam therapy, a target’s volume is irradiated by scanning a
pencil beam across the transverse plane using steering magnets, while
adjusting the beam energy to reach different depths within the target.
The Treatment Plan source simulates the delivery of a scanned ion pencil
beam treatment plan.

The treatment plan specifies, for each beam and each energy layer, the
positions (x,y) of the spots to be irradiated and their weight,
represented as either the number of particles or monitor units. Here,
the (x,y) coordinates indicate where the beam intersects the plane of
the room’s isocenter. The plan also includes the gantry angle for each
beam.

The Treatment Plan source reads the treatment plan file provided by the
user and generates a Pencil Beam source whose parameters are updated in
order to cover the spots described in the plan. To determine the
position and orientation of each pencil beam, essential beamline
geometrical parameters are required, such as the position of the
stearing magnets and the virtual source to isocenter distance. Moreover,
the beamline energy dependent optics parameters and the energy spread
should be characterized.

Note that the Treatment Plan source simulates only a single beam at a
time. If the treatment plan includes multiple beams, each must be
simulated individually. You can specify the beam to simulate by using
the “beam_nr” property of the source, with beam numbering starting at 1.

.. figure:: https://github.com/user-attachments/assets/6d7b68ec-6ecb-405e-8d6d-4a752ca8a189
   :alt: image

   image

To set up a Treatment Plan source, the user shall provide:

-  a **treatment plan file path**: DICOM format or Gate 9 text file
   format. Alternatively, the user can provide a dictionary with the
   spots data (see opengate.contrib.tps.ionbeamtherapy ->
   spots_info_from_txt).
-  a **beamline model**: including geometrical and energy dependent
   parametrs’ description. (see opengate.contrib.beamlines.ionbeamline
   -> BeamlineModel).
-  the **gantry rotation axis**. Default is ‘z’.
-  the **number of particles** to simulate.
-  the **ion type**.

Additional functionality:

-  ``flat_generation`` flag: if True, the same number of particles is
   generated for each spot and the spot weight is applied to the energy
   deposition instead. Default is False.
-  ``sorted_spot_generation`` flag: if True, the spots are irradiated
   one by one, following the order in the treatment plan. Otherwise the
   spots are selected by sampling from a probability density function.
   Default is False.

Here an example of how to set up a Treatment Plan source in the opengate
simulation:

.. code:: python

       # beamline model
       beamline = BeamlineModel()
       beamline.name = None
       beamline.radiation_types = "proton"

       # polinomial coefficients
       beamline.energy_mean_coeffs = [1, 0]
       beamline.energy_spread_coeffs = [0.4417036946562556]
       beamline.sigma_x_coeffs = [2.3335754]
       beamline.theta_x_coeffs = [2.3335754e-3]
       beamline.epsilon_x_coeffs = [0.00078728e-3]
       beamline.sigma_y_coeffs = [1.96433431]
       beamline.theta_y_coeffs = [0.00079118e-3]
       beamline.epsilon_y_coeffs = [0.00249161e-3]

       # tps
       n_sim = 80000  # particles to simulate per beam
       tps = sim.add_source("TreatmentPlanPBSource", "TPSource")
       tps.n = n_sim
       tps.beam_model = beamline
       tps.plan_path = ref_path / "TreatmentPlan2Spots.txt"
       tps.beam_nr = 1
       tps.gantry_rot_axis = "x"
       tps.sorted_spot_gneration = True
       tps.particle = "proton"

To see more examples on the Treatment Plan source usage, the user can
refer to test_059*.
