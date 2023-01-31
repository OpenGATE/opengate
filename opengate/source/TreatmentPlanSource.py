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
        print(f"{dSMXIso=}")
        print(f"{dSMYIso=}")
        # mapping factors between iso center plane and nozzle plane (due to steering magnets)
        corrX = (dSMXIso - dNozzleIso) / dSMXIso
        corrY = (dSMYIso - dNozzleIso) / dSMYIso
        print(f"{corrX=}")
        print(f"{corrY=}")

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
            print(f"{spot.xiec=}")
            print(f"{spot.yiec=}")
            pos = [
                (spot.xiec) * corrX,
                (spot.yiec) * corrY,
                dNozzleIso,
            ]
            print(f"{pos=}")
            source.position.translation = (self.rotation).apply(pos) + self.translation
            # ROTATION: by default the source points in direction z+.
            # Need to account for SM direction deviation and rotation thoward isocenter (180 deg)
            # hen rotate of gantry angle
            rotation = [0.0, 0.0, 0.0]
            if dNozzleIso != 0:
                beta = np.arctan(spot.yiec / dSMYIso)
                alpha = np.arctan(spot.xiec / dSMXIso)
                rotation[0] = np.pi + beta
                rotation[1] = -alpha

            # apply gantry angle
            source.position.rotation = (
                self.rotation * Rotation.from_euler("xyz", rotation)
            ).as_matrix()

            print(source.position.rotation)
            # add weight
            # source.weight = -1
            source.n = (
                spot.beamFraction * nSim
            )  # simulate a fraction of the beam particles for this spot

            # set optics parameters
            source.direction.partPhSp_x = [
                beamline.getSigmaX(energyMeVnuc),
                beamline.getThetaX(energyMeVnuc),
                beamline.getEpsilonX(energyMeVnuc),
                beamline.convX,
            ]
            source.direction.partPhSp_y = [
                beamline.getSigmaY(energyMeVnuc),
                beamline.getThetaY(energyMeVnuc),
                beamline.getEpsilonY(energyMeVnuc),
                beamline.convX,
            ]
