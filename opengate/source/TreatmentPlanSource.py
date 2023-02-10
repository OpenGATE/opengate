import numpy as np
from scipy.spatial.transform import Rotation
import opengate as gate


class TreatmentPlanSource:
    def __init__(self, name, ntot, sim, beamline, spots, gantry_angle=0):
        self.name = name
        # self.mother = None
        if gantry_angle != 0:
            self.rotation = Rotation.from_euler("z", gantry_angle, degrees=True)
        else:
            self.rotation = Rotation.identity()
        self.translation = [0, 0, 0]
        self.spots = spots
        self.beamline_model = beamline
        self.ntot = ntot
        self.sim = sim  # simulation obj to which we want to add the tp source

    def __del__(self):
        pass

    @classmethod
    def from_dcm(cls, name, ntot, sim, beamline, *, rt_plan_path):
        beamset = gate.beamset_info(rt_plan_path)
        gantry_angle = beamset.beam_angles[0]
        spots = gate.get_spots_from_beamset(beamset)

        return cls(name, ntot, sim, beamline, spots, gantry_angle)

    # def set_spots(self, spots):
    #     self.spots = spots

    def initialize_tpsource(self):
        # if self.beamset is None and self.spots is None:
        #     raise Exception(
        #         "TPSource: provide either an rt plan dicom path or a spot array"
        #     )

        spots_array = self.spots

        # some alias
        sim = self.sim
        nSim = self.ntot
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

        # initialize a pencil beam for each spot
        for i, spot in enumerate(spots_array):
            source = sim.add_source("PencilBeam", f"{self.name}_spot_{i}")

            # set energy
            source.energy.mono = beamline.get_energy(nominal_energy=spot.energy)

            source.particle = spot.particle_name
            source.position.type = "disc"  # pos = Beam, shape = circle + sigma

            # # set mother
            # if self.mother is not None:
            #     source.mother = self.mother

            # POSITION:
            source.position.translation = self.get_pbs_position(spot)

            # ROTATION:
            source.position.rotation = self.get_pbs_rotation(spot)

            # add weight
            # source.weight = -1
            source.n = np.round(
                spot.beamFraction * nSim
            )  # simulate a fraction of the beam particles for this spot

            # set optics parameters
            source.direction.partPhSp_x = [
                beamline.get_sigma_x(spot.energy),
                beamline.get_theta_x(spot.energy),
                beamline.get_epsilon_x(spot.energy),
                beamline.convX,
            ]
            source.direction.partPhSp_y = [
                beamline.get_sigma_y(spot.energy),
                beamline.get_theta_y(spot.energy),
                beamline.get_epsilon_y(spot.energy),
                beamline.convX,
            ]

    def get_pbs_position(self, spot):
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

    def get_pbs_rotation(self, spot):
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
