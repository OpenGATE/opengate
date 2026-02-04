# N.B: distances in mm, degrees in rad
# FIXME: make sure distances are correctly converted via g4units
from opengate import numerical as nm


class BaseBeamlineModel:
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

    def get_energy(self, nominal_energy):
        raise NotImplemented("This function must be overwritten by the child class")

    def get_sigma_energy(self, nominal_energy):
        raise NotImplemented("This function must be overwritten by the child class")

    def get_sigma_x(self, nominal_energy):
        raise NotImplemented("This function must be overwritten by the child class")

    def get_theta_x(self, nominal_energy):
        raise NotImplemented("This function must be overwritten by the child class")

    def get_epsilon_x(self, nominal_energy):
        raise NotImplemented("This function must be overwritten by the child class")

    def get_sigma_y(self, nominal_energy):
        raise NotImplemented("This function must be overwritten by the child class")

    def get_theta_y(self, nominal_energy):
        raise NotImplemented("This function must be overwritten by the child class")

    def get_epsilon_y(self, nominal_energy):
        raise NotImplemented("This function must be overwritten by the child class")

    def get_n_primaries_from_MU(self, nominal_energy):
        raise NotImplemented("This function must be overwritten by the child class")


class BeamlineModel(BaseBeamlineModel):
    """
    This class allows the definition of a beam model as polynomial coefficients,
    describing the beam properties as a function of energy.
    Polynomial coefficients should be provided in decreasing order
    """

    def __init__(self):
        super().__init__()
        # polinomial coefficients pencil beam
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
        # MU/N primaries conversion. Don't modify if the plan is already in N primaries
        self.MU_to_N_coeffs = [1]

    def get_energy(self, nominal_energy):
        return nm.polynomial_map(nominal_energy, self.energy_mean_coeffs)

    def get_sigma_energy(self, nominal_energy):
        return nm.polynomial_map(nominal_energy, self.energy_spread_coeffs)

    def get_sigma_x(self, energy):
        return nm.polynomial_map(energy, self.sigma_x_coeffs)

    def get_theta_x(self, nominal_energy):
        return nm.polynomial_map(nominal_energy, self.theta_x_coeffs)

    def get_epsilon_x(self, nominal_energy):
        return nm.polynomial_map(nominal_energy, self.epsilon_x_coeffs)

    def get_sigma_y(self, nominal_energy):
        return nm.polynomial_map(nominal_energy, self.sigma_y_coeffs)

    def get_theta_y(self, nominal_energy):
        return nm.polynomial_map(nominal_energy, self.theta_y_coeffs)

    def get_epsilon_y(self, nominal_energy):
        return nm.polynomial_map(nominal_energy, self.epsilon_y_coeffs)

    def get_n_primaries_from_MU(self, nominal_energy):
        return nm.polynomial_map(nominal_energy, self.MU_to_N_coeffs)


class BeamlineModelLUT(BaseBeamlineModel):
    """
    This class allows the definition of a beam model from LUT values.
    The user has to provide, for each beam parameter, a list of energies and corresponding
    parameter values, in the format [[e_list],[param_list]].
    In the treatment plan source, the parameter value for each planned energy
    will be calculated via piecewise linear interpolation of the values in the LUT.
    """

    def __init__(self):
        super().__init__()
        self.energy_mean_lut = [[], []]
        self.energy_sigma_lut = [[], []]
        self.sigma_x_lut = [[], []]
        self.theta_x_lut = [[], []]
        self.epsilon_x_lut = [[], []]
        self.sigma_y_lut = [[], []]
        self.theta_y_lut = [[], []]
        self.epsilon_y_lut = [[], []]
        self.MU_to_N_lut = [[], []]
        self.conv_x = 0
        self.conv_y = 0

    def get_energy(self, nominal_energy):
        return nm.piecewise_linear_interpolation(
            nominal_energy, self.energy_mean_lut[0], self.energy_mean_lut[1]
        )

    def get_sigma_energy(self, nominal_energy):
        return nm.piecewise_linear_interpolation(
            nominal_energy, self.energy_sigma_lut[0], self.energy_sigma_lut[1]
        )

    def get_sigma_x(self, nominal_energy):
        return nm.piecewise_linear_interpolation(
            nominal_energy, self.sigma_x_lut[0], self.sigma_x_lut[1]
        )

    def get_theta_x(self, nominal_energy):
        return nm.piecewise_linear_interpolation(
            nominal_energy, self.theta_x_lut[0], self.theta_x_lut[1]
        )

    def get_epsilon_x(self, nominal_energy):
        return nm.piecewise_linear_interpolation(
            nominal_energy, self.epsilon_x_lut[0], self.epsilon_x_lut[1]
        )

    def get_sigma_y(self, nominal_energy):
        return nm.piecewise_linear_interpolation(
            nominal_energy, self.sigma_y_lut[0], self.sigma_y_lut[1]
        )

    def get_theta_y(self, nominal_energy):
        return nm.piecewise_linear_interpolation(
            nominal_energy, self.theta_y_lut[0], self.theta_y_lut[1]
        )

    def get_epsilon_y(self, nominal_energy):
        return nm.piecewise_linear_interpolation(
            nominal_energy, self.epsilon_y_lut[0], self.epsilon_y_lut[1]
        )

    def get_n_primaries_from_MU(self, nominal_energy):
        return nm.piecewise_linear_interpolation(
            nominal_energy, self.MU_to_N_lut[0], self.MU_to_N_lut[1]
        )
