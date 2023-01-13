from .GenericSource import *
import opengate_core as g4


class PencilBeamSource(GenericSource):
    """
    Pencil Beam source
    """

    type_name = "PencilBeam"

    @staticmethod
    def set_default_user_info(user_info):
        GenericSource.set_default_user_info(user_info)
        # additional parameters: position
        # Box() resets the object to blank. All param set for position before this line are cancelled
        # user_info.position = Box()
        user_info.position.type = "disc"
        # user_info.position.size = [0, 0, 0]
        # user_info.position.translation = [0, 0, 0]
        # user_info.position.rotation = Rotation.identity().as_matrix()
        # user_info.position.confine = None
        # user_info.position.radius = None
        # user_info.position.sigma_x = None
        # additional parameters: direction
        # sigma, theta, epsilon, conv (0: divergent, 1: convergent)
        user_info.direction.partPhSp_x = [0, 0, 0, 0]
        user_info.direction.partPhSp_y = [0, 0, 0, 0]

    def __del__(self):
        pass

    def create_g4_source(self):
        return g4.GatePencilBeamSource()

    def __init__(self, user_info):
        super().__init__(user_info)
        self.__check_phSpace_params(self.user_info.direction.partPhSp_x)
        self.__check_phSpace_params(self.user_info.direction.partPhSp_y)

    def __check_phSpace_params(self, paramV):
        sigma = paramV[0]
        theta = paramV[1]
        epsilon = paramV[2]
        conv = paramV[3]
        pi = 3.14159265358979323846
        if epsilon == 0:
            raise ValueError(
                "Ellipse area is 0 !!! Check epsilon parameter in PencilBeamSource."
            )
        if pi * sigma * theta < epsilon:
            raise ValueError(
                f"pi*sigma*theta < epsilon. Provided values: sigma = {sigma}, theta = {theta}, epsilon = {epsilon}."
            )
        if conv not in [0, 1]:
            raise ValueError("convergence parameter can be only 0 or 1.")
