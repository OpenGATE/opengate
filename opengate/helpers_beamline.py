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
        self.SMXToIso = float("inf")
        # SMY (Y bending magnet) to Isocenter distance
        self.SMYToIso = float("inf")
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

    def get_energy(self, nominal_energy):
        return self._polynomial_map(nominal_energy, self.energyMeanCoeffs)

    def get_sigma_energy(self, nominal_energy):
        return self._polynomial_map(nominal_energy, self.energySpreadCoeffs)

    def get_sigma_x(self, energy):
        return self._polynomial_map(energy, self.sigmaXCoeffs)

    def get_theta_x(self, energy):
        return self._polynomial_map(energy, self.thetaXCoeffs)

    def get_epsilon_x(self, energy):
        return self._polynomial_map(energy, self.epsilonXCoeffs)

    def get_sigma_y(self, energy):
        return self._polynomial_map(energy, self.sigmaYCoeffs)

    def get_theta_y(self, energy):
        return self._polynomial_map(energy, self.thetaYCoeffs)

    def get_epsilon_y(self, energy):
        return self._polynomial_map(energy, self.epsilonYCoeffs)
