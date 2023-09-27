import math

import opengate_core
from .generic import GenericSource


class IonPencilBeamSource(GenericSource):
    """
    Pencil Beam source
    """

    type_name = "IonPencilBeamSource"

    @staticmethod
    def set_default_user_info(user_info):
        GenericSource.set_default_user_info(user_info)
        user_info.position.type = "disc"
        # additional parameters: direction
        # sigma, theta, epsilon, conv (0: divergent, 1: convergent)
        user_info.direction.partPhSp_x = [0, 0, 0, 0]
        user_info.direction.partPhSp_y = [0, 0, 0, 0]

    def __del__(self):
        pass

    def create_g4_source(self):
        return opengate_core.GatePencilBeamSource()

    def __init__(self, user_info):
        super().__init__(user_info)
        self.__check_phSpace_params(self.user_info.direction.partPhSp_x)
        self.__check_phSpace_params(self.user_info.direction.partPhSp_y)

    def __check_phSpace_params(self, paramV):
        sigma = paramV[0]
        theta = paramV[1]
        epsilon = paramV[2]
        conv = paramV[3]
        pi = math.pi
        if epsilon == 0:
            raise ValueError(
                "Ellipse area is 0 !!! Check epsilon parameter in IonPencilBeamSource."
            )
        if pi * sigma * theta < epsilon:
            raise ValueError(
                f"pi*sigma*theta < epsilon. Provided values: sigma = {sigma}, theta = {theta}, epsilon = {epsilon}."
            )
        if conv not in [0, 1]:
            raise ValueError("convergence parameter can be only 0 or 1.")
