import numpy as np
from scipy.spatial.transform import Rotation
import opengate as gate


class TreatmentPlanSource:
    def __init__(self, name, sim):
        self.name = name
        # self.mother = None
        self.rotation = Rotation.identity()
        self.translation = [0, 0, 0]
        self.spots = None
        self.beamline_model = None
        self.n_sim = 0
        self.sim = sim  # simulation obj to which we want to add the tp source

    def __del__(self):
        pass

    def set_particles_to_simulate(self, n_sim):
        self.n_sim = n_sim

    def set_spots(self, spots):
        self.spots = spots

    def set_spots_from_rtplan(self, rt_plan_path):
        beamset = gate.beamset_info(rt_plan_path)
        gantry_angle = beamset.beam_angles[0]
        spots = gate.get_spots_from_beamset(beamset)
        self.spots = spots
        self.rotation = Rotation.from_euler("z", gantry_angle, degrees=True)

    def set_beamline_model(self, beamline):
        self.beamline_model = beamline

    def initialize_tpsource(self):
        # some alias
        spots_array = self.spots
        sim = self.sim
        nSim = self.n_sim
        beamline = self.beamline_model
        self.d_nozzle_to_iso = beamline.distance_nozzle_iso
        self.d_stearMag_to_iso_x = beamline.distance_stearmag_to_isocenter_x
        self.d_stearMag_to_iso_y = beamline.distance_stearmag_to_isocenter_y

        # mapping factors between iso center plane and nozzle plane (due to steering magnets)
        cal_proportion_factor = (
            lambda d_magnet_iso: 1
            if (d_magnet_iso == float("inf"))
            else (d_magnet_iso - self.d_nozzle_to_iso) / d_magnet_iso
        )
        self.proportion_factor_x = cal_proportion_factor(self.d_stearMag_to_iso_x)
        self.proportion_factor_y = cal_proportion_factor(self.d_stearMag_to_iso_y)
        tot_sim_particles = 0
        # initialize a pencil beam for each spot
        for i, spot in enumerate(spots_array):
            # simulate a fraction of the beam particles for this spot
            nspot = np.round(spot.beamFraction * nSim)
            if nspot == 0:
                continue
            tot_sim_particles += nspot
            source = sim.add_source("PencilBeamSource", f"{self.name}_spot_{i}")

            # set energy
            source.energy.type = "gauss"
            source.energy.mono = beamline.get_energy(nominal_energy=spot.energy)
            source.energy.sigma_gauss = beamline.get_sigma_energy(
                nominal_energy=spot.energy
            )

            source.particle = spot.particle_name
            source.position.type = "disc"  # pos = Beam, shape = circle + sigma

            # # set mother
            # if self.mother is not None:
            #     source.mother = self.mother

            # POSITION:
            source.position.translation = self._get_pbs_position(spot)

            # ROTATION:
            source.position.rotation = self._get_pbs_rotation(spot)

            # add weight
            # source.weight = -1
            source.n = nspot

            # set optics parameters
            source.direction.partPhSp_x = [
                beamline.get_sigma_x(spot.energy),
                beamline.get_theta_x(spot.energy),
                beamline.get_epsilon_x(spot.energy),
                beamline.conv_x,
            ]
            source.direction.partPhSp_y = [
                beamline.get_sigma_y(spot.energy),
                beamline.get_theta_y(spot.energy),
                beamline.get_epsilon_y(spot.energy),
                beamline.conv_y,
            ]

        self.actual_sim_particles = tot_sim_particles

    def _get_pbs_position(self, spot):
        # (x,y) referr to isocenter plane.
        # Need to be corrected to referr to nozzle plane
        pos = [
            (spot.xiec) * self.proportion_factor_x,
            (spot.yiec) * self.proportion_factor_y,
            self.d_nozzle_to_iso,
        ]
        # Gantry angle = 0 -> source comes from +y and is positioned along negative side of y-axis
        # https://opengate.readthedocs.io/en/latest/source_and_particle_management.html

        position = (self.rotation * Rotation.from_euler("x", np.pi / 2)).apply(
            pos
        ) + self.translation

        return position

    def _get_pbs_rotation(self, spot):
        # by default the source points in direction z+.
        # Need to account for SM direction deviation and rotation thoward isocenter (270 deg around x)
        # then rotate of gantry angle
        rotation = [0.0, 0.0, 0.0]
        beta = np.arctan(spot.yiec / self.d_stearMag_to_iso_y)
        alpha = np.arctan(spot.xiec / self.d_stearMag_to_iso_x)
        rotation[0] = -np.pi / 2 + beta
        rotation[2] = -alpha

        # apply gantry angle
        spot_rotation = (
            self.rotation * Rotation.from_euler("xyz", rotation)
        ).as_matrix()

        return spot_rotation
