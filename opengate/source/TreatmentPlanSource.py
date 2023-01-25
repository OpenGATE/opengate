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
        # mapping factors between iso center plane and nozzle plane (due to steering magnets)
        corrX = (dSMXIso - dNozzleIso) / dSMXIso
        corrY = (dSMYIso - dNozzleIso) / dSMYIso
        # units
        mm = gate.g4_units("mm")
        rad = gate.g4_units("rad")
        G = np.pi * (self.G / 360)

        # initialize a pencil beam for each spot
        for i, spot in enumerate(spots_array):
            source = sim.add_source("PencilBeam", f"spot_{i}")

            # set energy
            energyMeVnuc = spot.energy
            energyMeV = beamline.getEnergy(energyMeVnuc)
            source.energy.mono = energyMeV

            # set mother
            if self.mother is not None:
                source.mother = self.mother

            source.particle = spot.ion  # carbon
            source.position.type = "disc"  # pos = Beam, shape = circle + sigma

            # POSITION: (x,y) referr to isocenter plane.
            # Need to be corrected to referr to nozzle plane
            pos = [
                (spot.xiec * mm) * corrX,
                -(spot.yiec * mm) * corrY,
                dNozzleIso * mm,
            ]
            # rotate of 90 around x to account for different reference frame of coordinates
            # TPSource should use the same RF of the CT scanner, but beam spots are in the
            # beam's own RF. Then apply external rotation (Gantry angle)
            source.position.translation = (self.rotation).apply(pos) + self.translation
            # source.position.translation = pos
            print(source.position.translation)

            # ROTATION: by default the source points in direction z+.
            # Need to account for SM direction deviation and rotation thoward isocenter (180 deg)
            # Then correct for reference frame (as in position). Then rotate of gantry angle
            rotation = [0, 0, 0]
            if dNozzleIso != 0:
                beta = np.arctan(spot.yiec / dSMYIso)
                alpha = np.arctan(spot.xiec / dSMXIso)
                print(f"{alpha=}")
                print(f"{beta=}")
                rotation[0] = np.pi + beta
                rotation[1] = -alpha

            # apply gantry angle
            source.position.rotation = (
                self.rotation * Rotation.from_euler("xyz", rotation)
            ).as_matrix()
            print(
                (self.rotation * Rotation.from_euler("xyz", rotation)).as_euler(
                    "xyz", degrees=True
                )
            )

            # add weight
            # source.weight = -1
            source.n = (
                spot.beamFraction * nSim
            )  # simulate a fraction of the beam particles for this spot

            # set optics parameters
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
