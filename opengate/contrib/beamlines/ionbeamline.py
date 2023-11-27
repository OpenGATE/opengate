# N.B: distances in mm, degrees in rad
# FIXME: make sure distances are correctly converted via g4units


class BeamlineModel:
    def __init__(self):
        self.name = None
        self.radiation_types = []
        self.rm = None  # range modulator
        self.rashi = None
        # Nozzle entrance to Isocenter distance
        self.distance_nozzle_iso = 0  # mm
        # SMX (X bending magnet) to Isocenter distance
        self.distance_stearmag_to_isocenter_x = float(
            "inf"
        )  # default infinity for parallel beams
        # SMY (Y bending magnet) to Isocenter distance
        self.distance_stearmag_to_isocenter_y = float("inf")
        # polinomial coefficients
        self.energy_mean_coeffs = [0]
        self.energy_spread_coeffs = [0]
        self.sigma_x_coeffs = [0]
        self.theta_x_coeffs = [0]
        self.epsilon_x_coeffs = [0]
        self.sigma_y_coeffs = [0]
        self.theta_y_coeffs = [0]
        self.epsilon_y_coeffs = [0]
        # convergence
        self.conv_x = 0
        self.conv_y = 0

    def _polynomial_map(self, base, coeff):
        # coeff are given with decreasing degree (coeff[0]->max degree)
        polyDegree = len(coeff)
        exp = list(range(polyDegree))
        exp.reverse()

        return sum([c * (base ** (i)) for c, i in zip(coeff, exp)])

    def get_energy(self, nominal_energy):
        return self._polynomial_map(nominal_energy, self.energy_mean_coeffs)

    def get_sigma_energy(self, nominal_energy):
        return self._polynomial_map(nominal_energy, self.energy_spread_coeffs)

    def get_sigma_x(self, energy):
        return self._polynomial_map(energy, self.sigma_x_coeffs)

    def get_theta_x(self, energy):
        return self._polynomial_map(energy, self.theta_x_coeffs)

    def get_epsilon_x(self, energy):
        return self._polynomial_map(energy, self.epsilon_x_coeffs)

    def get_sigma_y(self, energy):
        return self._polynomial_map(energy, self.sigma_y_coeffs)

    def get_theta_y(self, energy):
        return self._polynomial_map(energy, self.theta_y_coeffs)

    def get_epsilon_y(self, energy):
        return self._polynomial_map(energy, self.epsilon_y_coeffs)
