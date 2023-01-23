import opengate as gate
import numpy as np
from scipy.spatial.transform import Rotation


class TreatmentPlanSource:
    def __init__(self, ntot, sim, beamline):
        # set beamline model and rt plan path
        self.G = 0
        self.beamset = None
        self.mother = None
        self.rotation = Rotation.identity()
        self.translation = [0, 0, 0]
        self.spots = []
        self.beamline_model = beamline
        self.ntot = ntot
        self.sim = sim  # simulation obj to which we want to add the tp source

    def __del__(self):
        pass

    def get_spots_from_rtp(self):
        beamset = self.beamset
        rad_type = beamset.bs_info["Radiation Type Opengate"]
        spots_array = []
        for beam in beamset.beams:
            mswtot = beam.mswtot
            for energy_layer in beam.layers:
                for spot in energy_layer.spots:
                    nPlannedSpot = spot.w
                    spot.beamFraction = (
                        nPlannedSpot / mswtot
                    )  # nr particles planned for the spot/tot particles planned for the beam
                    spot.ion = rad_type
                    spots_array.append(spot)
        return spots_array

    def initialize_tpsource(self):
        if self.beamset is None and self.spots is None:
            raise Exception(
                "TPSource: provide either an rt plan dicom path or a spot array"
            )

        # get spots
        if self.beamset:
            spots_array = self.get_spots_from_rtp()
        else:
            spots_array = self.spots

        # some alias
        sim = self.sim
        nSim = self.ntot
        beamline = self.beamline_model
        dNozzleIso = beamline.NozzleToIsoDist
        dSMXIso = beamline.SMXToIso
        dSMYIso = beamline.SMYToIso
        # mapping factors between iso center plane and nozzle plane (due to bending magnets)
        corrX = (dSMXIso - dNozzleIso) / dSMXIso
        corrY = (dSMYIso - dNozzleIso) / dSMYIso
        # units
        mm = gate.g4_units("mm")
        rad = gate.g4_units("rad")
        G = np.pi * (self.G / 360)

        # initialize a pencil beam for each spot
        for i, spot in enumerate(spots_array):
            # add pbs source to simulation
            source = sim.add_source("PencilBeam", f"spot_{i}")
            energyMeVnuc = spot.energy
            energyMeV = beamline.getEnergy(energyMeVnuc)
            source.energy.mono = energyMeV
            # source.energy.type = 'gauss'
            # source.sigma_gauss = beamline.getSigmaEnergy(energyMeVnuc) # not used by pbs
            if self.mother is not None:
                source.mother = self.mother
            source.particle = spot.ion  # carbon
            source.position.type = "disc"  # pos = Beam, shape = circle + sigma
            # set correct position and rotation of the source
            # TODO: fix source position according to gantry and patient positions and angles
            pos = [
                (spot.xiec * mm) * corrX,
                (spot.yiec * mm) * corrY,
                dNozzleIso * mm,
            ]
            # pos = Rotation.from_euler("x", 90, degrees=True).apply(pos)
            # beam by default is coming from the negative direction of the z axis (gantry_angle = 0)
            # need to account for SM direction deviation
            rotation = [0, 0, 0]
            if dNozzleIso != 0:
                beta = np.arctan(spot.yiec / dSMYIso)
                alpha = np.arctan(spot.xiec / dSMXIso)
                rotation[0] = np.pi + beta
                rotation[1] = -alpha
                # rotation[0] = -np.pi/2 + beta
                # rotation[2] = -alpha
            source.position.translation = (
                self.rotation  # * Rotation.from_euler("z", np.pi / 2)
            ).apply(pos) + self.translation
            print(source.position.translation)
            # rotate in -z direction, correct for SM deviation, apply gantry angle
            source.position.rotation = (
                self.rotation * Rotation.from_euler("xyz", rotation)
            ).as_matrix()
            print((Rotation.from_euler("xyz", rotation)).as_euler("xyz", degrees=True))

            # add weight
            # source.weight = -1
            source.n = (
                spot.beamFraction * nSim
            )  # simulate a fraction of the beam particles for this spot
            # here we need beam model
            source.direction.partPhSp_x = [
                beamline.getSigmaX(energyMeVnuc) * mm,
                beamline.getThetaX(energyMeVnuc) * rad,
                beamline.getEpsilonX(energyMeVnuc) * mm * rad,
                beamline.convX,
            ]
            source.direction.partPhSp_y = [
                beamline.getSigmaY(energyMeVnuc) * mm,
                beamline.getThetaY(energyMeVnuc) * rad,
                beamline.getEpsilonY(energyMeVnuc) * mm * rad,
                beamline.convX,
            ]
