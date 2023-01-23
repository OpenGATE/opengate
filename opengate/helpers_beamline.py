# N.B: distances in mm, degrees in rad


class Rashi:
    pass


class RangeMod:
    pass


class BeamlineModel:
    def __init__(self):
        self.Name = None
        self.RadiationTypes = []
        self.Rm = None
        self.Rashi = None
        # Nozzle entrance to Isocenter distance
        self.NozzleToIsoDist = 0  # mm
        # SMX (X bending magnet) to Isocenter distance
        self.SMXToIso = 1
        # SMY (Y bending magnet) to Isocenter distance
        self.SMYToIso = 1
        # polinomial coefficients
        self.energyMeanCoeffs = []
        self.energySpreadCoeffs = []
        self.sigmaXCoeffs = []
        self.thetaXCoeffs = []
        self.epsilonXCoeffs = []
        self.sigmaYCoeffs = []
        self.thetaYCoeffs = []
        self.epsilonYCoeffs = []
        # convergence
        self.convX = 0
        self.convY = 0

    def _polynomial_map(self, base, coeff):
        # coeff are given with decreasing degree (coeff[0]->max degree)
        polyDegree = len(coeff)
        exp = list(range(polyDegree))
        exp.reverse()

        return sum([c * (base ** (i)) for c, i in zip(coeff, exp)])

    def getEnergy(self, energy):
        return self._polynomial_map(energy, self.energyMeanCoeffs)

    def getSigmaEnergy(self, energy):
        return self._polynomial_map(energy, self.energySpreadCoeffs)

    def getSigmaX(self, energy):
        return self._polynomial_map(energy, self.sigmaXCoeffs)

    def getThetaX(self, energy):
        return self._polynomial_map(energy, self.thetaXCoeffs)

    def getEpsilonX(self, energy):
        return self._polynomial_map(energy, self.epsilonXCoeffs)

    def getSigmaY(self, energy):
        return self._polynomial_map(energy, self.sigmaYCoeffs)

    def getThetaY(self, energy):
        return self._polynomial_map(energy, self.thetaYCoeffs)

    def getEpsilonY(self, energy):
        return self._polynomial_map(energy, self.epsilonYCoeffs)
